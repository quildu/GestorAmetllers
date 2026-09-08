from ..repositories import production as production_repo
from .dates import build_date_str


def create_production(conn, parcel_id, form):
    date_str = build_date_str(form['day'], form['month'], form['year'])
    kilos = float(form['kilos'])
    price_per_kilo = float(form['price_per_kilo'])
    total_income = kilos * price_per_kilo

    return production_repo.insert(conn, parcel_id, date_str, kilos, price_per_kilo, total_income)


def update_production(conn, parcel_id, item_id, form):
    date_str = build_date_str(form['day'], form['month'], form['year'])
    kilos = float(form['kilos'])
    price_per_kilo = float(form['price_per_kilo'])
    total_income = kilos * price_per_kilo

    production_repo.update(conn, parcel_id, item_id, date_str, kilos, price_per_kilo, total_income)


def get_production(conn, parcel_id, item_id):
    return production_repo.get(conn, parcel_id, item_id)


def list_production(conn, parcel_id):
    return production_repo.list_by_parcel(conn, parcel_id)


def delete_production(conn, parcel_id, item_id):
    production_repo.soft_delete(conn, parcel_id, item_id)
