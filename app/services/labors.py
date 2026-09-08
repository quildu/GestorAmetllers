from ..repositories import labors as labors_repo
from .dates import build_date_str


def create_labor(conn, parcel_id, form):
    date_str = build_date_str(form['day'], form['month'], form['year'])
    worker_id = form['worker_id']
    labor_type_id = form['labor_type_id']
    hours = float(form['hours'])
    price_per_hour = float(form['price_per_hour'])
    description = form.get('description', '')
    total_price = hours * price_per_hour

    return labors_repo.insert(conn, parcel_id, date_str, worker_id, labor_type_id, hours, price_per_hour, total_price, description)


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
