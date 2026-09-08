from ..repositories import expenses as expenses_repo
from .dates import build_date_str


def create_expense(conn, parcel_id, form):
    date_str = build_date_str(form['day'], form['month'], form['year'])
    expense_type_id = form['expense_type_id']
    description = form['description']
    amount = float(form['amount'])

    return expenses_repo.insert(conn, parcel_id, date_str, expense_type_id, description, amount)


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
