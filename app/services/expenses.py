import uuid

from ..repositories import catalog as catalog_repo
from ..repositories import expenses as expenses_repo
from ..repositories import parcels as parcels_repo
from .dates import build_date_str


def create_expense(conn, parcel_id, form):
    date_str = build_date_str(form['day'], form['month'], form['year'])
    expense_type_id = form['expense_type_id']
    description = form['description']
    total_amount = float(form['amount'])

    share_parcel_ids = [int(pid) for pid in form.getlist('share_parcel_ids') if int(pid) != parcel_id]

    if not share_parcel_ids:
        expense_id = expenses_repo.insert(conn, parcel_id, date_str, expense_type_id, description, total_amount)
        return {parcel_id: expense_id}

    return _create_shared_expense(conn, parcel_id, share_parcel_ids, date_str, expense_type_id, description, total_amount)


def _create_shared_expense(conn, primary_parcel_id, other_parcel_ids, date_str, primary_expense_type_id, description, total_amount):
    """Reparteix l'import total entre totes les parcel·les implicades, proporcionalment a les
    seves hectarees, i crea una fila d'expenses a cadascuna, totes lligades pel mateix invoice_group."""
    all_parcel_ids = [primary_parcel_id] + other_parcel_ids
    hectares_by_parcel = {p['id']: (p['hectares'] or 0) for p in parcels_repo.list_all(conn)}
    total_hectares = sum(hectares_by_parcel.get(pid, 0) for pid in all_parcel_ids)

    expense_type_name = catalog_repo.get_expense_type(conn, primary_expense_type_id)['name']
    invoice_group = uuid.uuid4().hex

    expense_ids_by_parcel = {}
    remaining_amount = total_amount
    last_index = len(all_parcel_ids) - 1

    for index, pid in enumerate(all_parcel_ids):
        if index == last_index:
            # L'ultima parcel·la absorbeix l'arrodoniment perque la suma quadri amb el total exacte.
            amount = round(remaining_amount, 2)
        else:
            share = hectares_by_parcel.get(pid, 0) / total_hectares if total_hectares > 0 else 1 / len(all_parcel_ids)
            amount = round(total_amount * share, 2)
            remaining_amount -= amount

        expense_type_id = primary_expense_type_id if pid == primary_parcel_id else _matching_expense_type_id(conn, pid, expense_type_name)
        expense_ids_by_parcel[pid] = expenses_repo.insert(conn, pid, date_str, expense_type_id, description, amount, invoice_group)

    return expense_ids_by_parcel


def _matching_expense_type_id(conn, parcel_id, expense_type_name):
    """Troba el tipus de despesa amb el mateix nom a l'altra parcel·la (o el crea si no existeix)."""
    existing = catalog_repo.find_expense_type_by_name(conn, parcel_id, expense_type_name)
    if existing:
        return existing['id']
    return catalog_repo.insert_expense_type(conn, parcel_id, expense_type_name)


def update_expense(conn, parcel_id, item_id, form):
    date_str = build_date_str(form['day'], form['month'], form['year'])
    expense_type_id = form['expense_type_id']
    description = form['description']
    amount = float(form['amount'])

    expenses_repo.update(conn, parcel_id, item_id, date_str, expense_type_id, description, amount)


def get_expense(conn, parcel_id, item_id):
    return expenses_repo.get(conn, parcel_id, item_id)


def list_expenses(conn, parcel_id):
    return expenses_repo.list_by_parcel(conn, parcel_id)


def delete_expense(conn, parcel_id, item_id):
    expenses_repo.soft_delete(conn, parcel_id, item_id)


def delete_expense_group(conn, invoice_group):
    expenses_repo.soft_delete_by_group(conn, invoice_group)


def get_group_siblings(conn, invoice_group, exclude_parcel_id):
    if not invoice_group:
        return []
    return expenses_repo.list_by_group(conn, invoice_group, exclude_parcel_id)
