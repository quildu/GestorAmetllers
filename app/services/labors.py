import uuid

from ..repositories import catalog as catalog_repo
from ..repositories import labors as labors_repo
from ..repositories import parcels as parcels_repo
from .dates import build_date_str


def create_labor(conn, parcel_id, form):
    date_str = build_date_str(form['day'], form['month'], form['year'])
    worker_id = form['worker_id']
    labor_type_id = form['labor_type_id']
    total_hours = float(form['hours'])
    price_per_hour = float(form['price_per_hour'])
    description = form.get('description', '')

    share_parcel_ids = [int(pid) for pid in form.getlist('share_parcel_ids') if int(pid) != parcel_id]

    if not share_parcel_ids:
        total_price = total_hours * price_per_hour
        labor_id = labors_repo.insert(conn, parcel_id, date_str, worker_id, labor_type_id, total_hours, price_per_hour, total_price, description)
        return {parcel_id: labor_id}

    return _create_shared_labor(conn, parcel_id, share_parcel_ids, date_str, worker_id, labor_type_id, total_hours, price_per_hour, description)


def _create_shared_labor(conn, primary_parcel_id, other_parcel_ids, date_str, primary_worker_id, primary_labor_type_id, total_hours, price_per_hour, description):
    """Reparteix les hores totals entre totes les parcel·les implicades, proporcionalment a les
    seves hectarees, i crea una fila de labors a cadascuna, totes lligades pel mateix invoice_group."""
    all_parcel_ids = [primary_parcel_id] + other_parcel_ids
    hectares_by_parcel = {p['id']: (p['hectares'] or 0) for p in parcels_repo.list_all(conn)}
    total_hectares = sum(hectares_by_parcel.get(pid, 0) for pid in all_parcel_ids)

    worker_name = catalog_repo.get_worker(conn, primary_worker_id)['name']
    labor_type_name = catalog_repo.get_labor_type(conn, primary_labor_type_id)['name']
    invoice_group = uuid.uuid4().hex

    labor_ids_by_parcel = {}
    remaining_hours = total_hours
    last_index = len(all_parcel_ids) - 1

    for index, pid in enumerate(all_parcel_ids):
        if index == last_index:
            # L'ultima parcel·la absorbeix l'arrodoniment perque la suma quadri amb el total exacte.
            hours = round(remaining_hours, 2)
        else:
            share = hectares_by_parcel.get(pid, 0) / total_hectares if total_hectares > 0 else 1 / len(all_parcel_ids)
            hours = round(total_hours * share, 2)
            remaining_hours -= hours

        total_price = round(hours * price_per_hour, 2)

        if pid == primary_parcel_id:
            worker_id = primary_worker_id
            labor_type_id = primary_labor_type_id
        else:
            worker_id = _matching_worker_id(conn, pid, worker_name)
            labor_type_id = _matching_labor_type_id(conn, pid, labor_type_name)

        labor_ids_by_parcel[pid] = labors_repo.insert(conn, pid, date_str, worker_id, labor_type_id, hours, price_per_hour, total_price, description, invoice_group)

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
    hours = float(form['hours'])
    price_per_hour = float(form['price_per_hour'])
    description = form.get('description', '')
    total_price = hours * price_per_hour

    labors_repo.update(conn, parcel_id, item_id, date_str, worker_id, labor_type_id, hours, price_per_hour, total_price, description)


def get_labor(conn, parcel_id, item_id):
    return labors_repo.get(conn, parcel_id, item_id)


def list_labors(conn, parcel_id):
    return labors_repo.list_by_parcel(conn, parcel_id)


def delete_labor(conn, parcel_id, item_id):
    labors_repo.soft_delete(conn, parcel_id, item_id)


def delete_labor_group(conn, invoice_group):
    labors_repo.soft_delete_by_group(conn, invoice_group)


def get_group_siblings(conn, invoice_group, exclude_parcel_id):
    if not invoice_group:
        return []
    return labors_repo.list_by_group(conn, invoice_group, exclude_parcel_id)
