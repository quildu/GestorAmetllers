from ..repositories import expenses as expenses_repo
from ..repositories import labors as labors_repo
from ..repositories import production as production_repo

EXPORT_HEADERS = {
    'labors': ['ID', 'Data', 'WorkerID', 'TypeID', 'Hours', 'Price/H', 'Total', 'Notes'],
    'production': ['ID', 'Data', 'Kilos', 'Price/Kg', 'Total'],
    'expenses': ['ID', 'Data', 'TypeID', 'Description', 'Amount'],
}


def expenses_by_type(conn, parcel_id):
    return expenses_repo.sum_by_type(conn, parcel_id)


def get_export_data(conn, parcel_id, category):
    """Torna (header, files) per a `category`, o None si la categoria no existeix."""
    if category == 'labors':
        rows = labors_repo.list_all_by_parcel(conn, parcel_id)
    elif category == 'production':
        rows = production_repo.list_all_by_parcel(conn, parcel_id)
    elif category == 'expenses':
        rows = expenses_repo.list_all_by_parcel(conn, parcel_id)
    else:
        return None

    return EXPORT_HEADERS[category], rows
