from flask import abort, redirect, render_template, request, url_for

from ..database import get_connection
from ..services import catalog as catalog_service
from ..services import documents as documents_service
from ..services import expenses as expenses_service


def register(app):
    @app.route('/parcela/<int:parcel_id>/expense/add', methods=['GET', 'POST'])
    def add_expense(parcel_id):
        conn = get_connection()
        if request.method == 'POST':
            expense_id = expenses_service.create_expense(conn, parcel_id, request.form)
            documents_service.save_documents(conn, parcel_id, 'expense', expense_id, request.files.getlist('documents'))
            return redirect(url_for('index'))

        expense_types = catalog_service.list_expense_types(conn, parcel_id)
        return render_template('expense_form.html', expense_types=expense_types)

    @app.route('/parcela/<int:parcel_id>/expense/edit/<int:id>', methods=['GET', 'POST'])
    def edit_expense(parcel_id, id):
        conn = get_connection()
        if request.method == 'POST':
            expenses_service.update_expense(conn, parcel_id, id, request.form)
            documents_service.save_documents(conn, parcel_id, 'expense', id, request.files.getlist('documents'))
            return redirect(url_for('history'))

        item = expenses_service.get_expense(conn, parcel_id, id)
        if not item:
            abort(404)
        y, m, d = item['date'].split('-')
        item_date = {'year': int(y), 'month': int(m), 'day': int(d)}
        expense_types = catalog_service.list_expense_types(conn, parcel_id)
        documents = documents_service.get_documents(conn, 'expense', id)
        return render_template('expense_form.html', item=item, item_date=item_date, expense_types=expense_types, documents=documents)
