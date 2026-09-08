from ..repositories import parcels as parcels_repo
from ..repositories import labors as labors_repo
from ..repositories import production as production_repo
from ..repositories import expenses as expenses_repo
from .catalog import seed_defaults_for_parcel


def list_parcels_with_totals(conn):
    return parcels_repo.list_with_totals(conn)


def create_parcel(conn, name):
    parcel_id = parcels_repo.create(conn, name)
    seed_defaults_for_parcel(conn, parcel_id)
    return parcel_id


def get_summary(conn, parcel_id):
    labors_total = labors_repo.sum_by_parcel(conn, parcel_id)
    expenses_total = expenses_repo.sum_by_parcel(conn, parcel_id)
    income_total = production_repo.sum_by_parcel(conn, parcel_id)

    total_expenses = labors_total + expenses_total
    net_profit = income_total - total_expenses

    return {
        'income_total': income_total,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
    }
