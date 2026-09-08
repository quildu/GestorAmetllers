from ..database import get_connection
from ..repositories import catalog as catalog_repo


def list_workers(conn, parcel_id):
    return catalog_repo.list_workers(conn, parcel_id)


def list_labor_types(conn, parcel_id):
    return catalog_repo.list_labor_types(conn, parcel_id)


def list_expense_types(conn, parcel_id):
    return catalog_repo.list_expense_types(conn, parcel_id)


def quick_add_worker(conn, parcel_id, name):
    return catalog_repo.insert_worker(conn, parcel_id, name)


def quick_add_labor_type(conn, parcel_id, name):
    return catalog_repo.insert_labor_type(conn, parcel_id, name)


def quick_add_expense_type(conn, parcel_id, name):
    return catalog_repo.insert_expense_type(conn, parcel_id, name)


def seed_defaults_for_parcel(conn, parcel_id):
    catalog_repo.seed_defaults_for_parcel(conn, parcel_id)


def seed_data():
    """Sembra els tipus per defecte de la parcel·la 1 (Servereta) si encara no en té."""
    conn = get_connection()
    if not catalog_repo.has_labor_types(conn, 1):
        catalog_repo.seed_default_labor_types(conn, 1)
    if not catalog_repo.has_expense_types(conn, 1):
        catalog_repo.seed_default_expense_types(conn, 1)
    conn.commit()
