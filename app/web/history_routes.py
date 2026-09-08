from flask import redirect, render_template, url_for

from ..database import get_connection
from ..services import documents as documents_service
from ..services import expenses as expenses_service
from ..services import labors as labors_service
from ..services import production as production_service


def register(app):
    @app.route('/parcela/<int:parcel_id>/history')
    def history(parcel_id):
        conn = get_connection()
        labors = labors_service.list_labors(conn, parcel_id)
        production = production_service.list_production(conn, parcel_id)
        expenses = expenses_service.list_expenses(conn, parcel_id)

        return render_template(
            'history.html', labors=labors, production=production, expenses=expenses,
            labor_docs=documents_service.get_documents_grouped_by_entity(conn, 'labor', parcel_id),
            production_docs=documents_service.get_documents_grouped_by_entity(conn, 'production', parcel_id),
            expense_docs=documents_service.get_documents_grouped_by_entity(conn, 'expense', parcel_id),
        )

    @app.route('/parcela/<int:parcel_id>/delete/<string:category>/<int:item_id>', methods=['POST'])
    def delete_item(parcel_id, category, item_id):
        conn = get_connection()
        if category == 'labor':
            labors_service.delete_labor(conn, parcel_id, item_id)
        elif category == 'production':
            production_service.delete_production(conn, parcel_id, item_id)
        elif category == 'expense':
            expenses_service.delete_expense(conn, parcel_id, item_id)
        return redirect(url_for('history'))
