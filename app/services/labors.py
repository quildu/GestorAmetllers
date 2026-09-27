import uuid

from ..repositories import catalog as catalog_repo
from ..repositories import labors as labors_repo
from ..repositories import parcels as parcels_repo
from .dates import build_date_str


def _parse_labor_amounts(form):
    """Si nomes s'ha introduit el preu total (sense hores), retorna hores=0 i preu/hora=0
    perque la BD no permet NULL, pero el total_price real es preserva igualment."""
    if form.get('only_total') == 'on':
        return 0.0, 0.0, float(form['total_price'])
    total_hours = float(form['hours'])
    price_per_hour = float(form['price_per_hour'])
    return total_hours, price_per_hour, total_hours * price_per_hour


def create_labor(conn, parcel_id, form):
    date_str = build_date_str(form['day'], form['month'], form['year'])
    worker_id = form['worker_id']
    labor_type_id = form['labor_type_id']
    total_hours, price_per_hour, total_price = _parse_labor_amounts(form)
    description = form.get('description', '')

    share_parcel_ids = [int(pid) for pid in form.getlist('share_parcel_ids') if int(pid) != parcel_id]

    if not share_parcel_ids:
        labor_id = labors_repo.insert(conn, parcel_id, date_str, worker_id, labor_type_id, total_hours, price_per_hour, total_price, description)
        return {parcel_id: labor_id}

    return _create_shared_labor(conn, parcel_id, share_parcel_ids, date_str, worker_id, labor_type_id, total_hours, price_per_hour, total_price, description)


def _create_shared_labor(conn, primary_parcel_id, other_parcel_ids, date_str, primary_worker_id, primary_labor_type_id, total_hours, price_per_hour, total_price, description):
    """Reparteix les hores (o, si nomes hi ha preu total, el preu total) entre totes les
    parcel·les implicades, proporcionalment a les seves hectarees, i crea una fila de labors
    a cadascuna, totes lligades pel mateix invoice_group."""
    all_parcel_ids = [primary_parcel_id] + other_parcel_ids
    hectares_by_parcel = {p['id']: (p['hectares'] or 0) for p in parcels_repo.list_all(conn)}
    total_hectares = sum(hectares_by_parcel.get(pid, 0) for pid in all_parcel_ids)
    only_total = total_hours == 0 and price_per_hour == 0

    worker_name = catalog_repo.get_worker(conn, primary_worker_id)['name']
    labor_type_name = catalog_repo.get_labor_type(conn, primary_labor_type_id)['name']
    invoice_group = uuid.uuid4().hex

    labor_ids_by_parcel = {}
    remaining_hours = total_hours
    remaining_total_price = total_price
    last_index = len(all_parcel_ids) - 1

    for index, pid in enumerate(all_parcel_ids):
        share = hectares_by_parcel.get(pid, 0) / total_hectares if total_hectares > 0 else 1 / len(all_parcel_ids)

        if index == last_index:
            # L'ultima parcel·la absorbeix l'arrodoniment perque la suma quadri amb el total exacte.
            hours = round(remaining_hours, 2)
            parcel_total_price = round(remaining_total_price, 2)
        elif only_total:
            hours = 0.0
            parcel_total_price = round(total_price * share, 2)
            remaining_total_price -= parcel_total_price
        else:
            hours = round(total_hours * share, 2)
            remaining_hours -= hours
            parcel_total_price = round(hours * price_per_hour, 2)
            remaining_total_price -= parcel_total_price

        if pid == primary_parcel_id:
            worker_id = primary_worker_id
            labor_type_id = primary_labor_type_id
        else:
            worker_id = _matching_worker_id(conn, pid, worker_name)
            labor_type_id = _matching_labor_type_id(conn, pid, labor_type_name)

        labor_ids_by_parcel[pid] = labors_repo.insert(conn, pid, date_str, worker_id, labor_type_id, hours, price_per_hour, parcel_total_price, description, invoice_group)

    return labor_ids_by_parcel


def _matching_worker_id(conn, parcel_id, worker_name):
    """Troba el treballador amb el mateix nom a l'altra parcel·la (o el crea si no existeix)."""
    existing = catalog_repo.find_worker_by_name(conn, parcel_id, worker_name)
    if existing:
        return existing['id']
    return catalog_repo.insert_worker(conn, parcel_id, worker_name)


def _matching_labor_type_id(conn, parcel_id, labor_type_name):
    """Troba el tipus de feina amb el mateix nom a l'altra parcel·la (o el crea si no existeix)."""
    existing = catalog_repo.find_labor_type_by_name(conn, parcel_id, labor_type_name)
    if existing:
        return existing['id']
    return catalog_repo.insert_labor_type(conn, parcel_id, labor_type_name)


def update_labor(conn, parcel_id, item_id, form):
    date_str = build_date_str(form['day'], form['month'], form['year'])
    worker_id = form['worker_id']
    labor_type_id = form['labor_type_id']
    hours, price_per_hour, total_price = _parse_labor_amounts(form)
    description = form.get('description', '')

    share_parcel_ids = [int(pid) for pid in form.getlist('share_parcel_ids') if int(pid) != parcel_id]
    existing = labors_repo.get(conn, parcel_id, item_id)
    existing_group = existing['invoice_group'] if existing else None

    if not share_parcel_ids:
        if existing_group:
            for sibling in labors_repo.list_by_group(conn, existing_group, parcel_id):
                labors_repo.soft_delete(conn, sibling['parcel_id'], sibling['id'])
        labors_repo.update(conn, parcel_id, item_id, date_str, worker_id, labor_type_id, hours, price_per_hour, total_price, description)
        return

    _update_shared_labor(conn, parcel_id, item_id, existing_group, share_parcel_ids, date_str, worker_id, labor_type_id, hours, price_per_hour, total_price, description)


def _update_shared_labor(conn, primary_parcel_id, primary_item_id, existing_group, share_parcel_ids, date_str, worker_id, labor_type_id, total_hours, price_per_hour, total_price, description):
    """Recalcula el repartiment d'un treball existent segons les parcel·les seleccionades ara:
    actualitza les files que ja formaven part del grup, en crea de noves per a les parcel·les
    afegides i esborra (soft) les que ja no hi son."""
    all_parcel_ids = [primary_parcel_id] + share_parcel_ids
    hectares_by_parcel = {p['id']: (p['hectares'] or 0) for p in parcels_repo.list_all(conn)}
    total_hectares = sum(hectares_by_parcel.get(pid, 0) for pid in all_parcel_ids)
    only_total = total_hours == 0 and price_per_hour == 0

    worker_name = catalog_repo.get_worker(conn, worker_id)['name']
    labor_type_name = catalog_repo.get_labor_type(conn, labor_type_id)['name']
    invoice_group = existing_group or uuid.uuid4().hex

    existing_siblings = {s['parcel_id']: s for s in labors_repo.list_by_group(conn, existing_group, primary_parcel_id)} if existing_group else {}
    kept_parcel_ids = set()

    remaining_hours = total_hours
    remaining_total_price = total_price
    last_index = len(all_parcel_ids) - 1

    for index, pid in enumerate(all_parcel_ids):
        share = hectares_by_parcel.get(pid, 0) / total_hectares if total_hectares > 0 else 1 / len(all_parcel_ids)

        if index == last_index:
            hours = round(remaining_hours, 2)
            parcel_total_price = round(remaining_total_price, 2)
        elif only_total:
            hours = 0.0
            parcel_total_price = round(total_price * share, 2)
            remaining_total_price -= parcel_total_price
        else:
            hours = round(total_hours * share, 2)
            remaining_hours -= hours
            parcel_total_price = round(hours * price_per_hour, 2)
            remaining_total_price -= parcel_total_price

        if pid == primary_parcel_id:
            labors_repo.update(conn, primary_parcel_id, primary_item_id, date_str, worker_id, labor_type_id, hours, price_per_hour, parcel_total_price, description, invoice_group)
        elif pid in existing_siblings:
            sibling = existing_siblings[pid]
            labors_repo.update(conn, pid, sibling['id'], date_str, sibling['worker_id'], sibling['labor_type_id'], hours, price_per_hour, parcel_total_price, description, invoice_group)
            kept_parcel_ids.add(pid)
        else:
            w_id = _matching_worker_id(conn, pid, worker_name)
            lt_id = _matching_labor_type_id(conn, pid, labor_type_name)
            labors_repo.insert(conn, pid, date_str, w_id, lt_id, hours, price_per_hour, parcel_total_price, description, invoice_group)

    for pid, sibling in existing_siblings.items():
        if pid not in kept_parcel_ids:
            labors_repo.soft_delete(conn, pid, sibling['id'])


def get_labor(conn, parcel_id, item_id):
    """Si el treball es comparteix amb altres parcel·les, retorna les hores i el preu total
    sumats de tot el grup (no nomes la part d'aquesta parcel·la), perque en editar-lo el
    formulari parteixi del total real i no d'una part ja repartida (si no, cada edicio
    reduiria el total repartit)."""
    item = labors_repo.get(conn, parcel_id, item_id)
    if not item or not item['invoice_group']:
        return item

    siblings = labors_repo.list_by_group(conn, item['invoice_group'], parcel_id)
    if not siblings:
        return item

    item = dict(item)
    item['hours'] = round(item['hours'] + sum(s['hours'] for s in siblings), 2)
    item['total_price'] = round(item['total_price'] + sum(s['total_price'] for s in siblings), 2)
    return item


def list_labors(conn, parcel_id):
    return labors_repo.list_by_parcel(conn, parcel_id)


def delete_labor(conn, parcel_id, item_id):
    """Si el treball es comparteix amb altres parcel·les, s'esborren totes les parts
    perque son el mateix jornal real: no te sentit deixar-ne nomes una."""
    item = labors_repo.get(conn, parcel_id, item_id)
    if item and item['invoice_group']:
        labors_repo.soft_delete_by_group(conn, item['invoice_group'])
    else:
        labors_repo.soft_delete(conn, parcel_id, item_id)


def get_group_siblings(conn, invoice_group, exclude_parcel_id):
    if not invoice_group:
        return []
    return labors_repo.list_by_group(conn, invoice_group, exclude_parcel_id)
