from flask import abort, redirect, render_template, request, url_for

from ..database import get_connection
from ..services import catalog as catalog_service
from ..services import documents as documents_service
from ..services import labors as labors_service


def register(app):
    @app.route('/parcela/<int:parcel_id>/labor/add', methods=['GET', 'POST'])
    def add_labor(parcel_id):
        conn = get_connection()
        if request.method == 'POST':
            labor_id = labors_service.create_labor(conn, parcel_id, request.form)
            documents_service.save_documents(conn, parcel_id, 'labor', labor_id, request.files.getlist('documents'))
            return redirect(url_for('index'))

        workers = catalog_service.list_workers(conn, parcel_id)
        labor_types = catalog_service.list_labor_types(conn, parcel_id)
        return render_template('labor_form.html', workers=workers, labor_types=labor_types)

    @app.route('/parcela/<int:parcel_id>/labor/edit/<int:id>', methods=['GET', 'POST'])
    def edit_labor(parcel_id, id):
        conn = get_connection()
        if request.method == 'POST':
            labors_service.update_labor(conn, parcel_id, id, request.form)
            documents_service.save_documents(conn, parcel_id, 'labor', id, request.files.getlist('documents'))
            return redirect(url_for('history'))

        item = labors_service.get_labor(conn, parcel_id, id)
        if not item:
            abort(404)
        # Parse date
        y, m, d = item['date'].split('-')
        item_date = {'year': int(y), 'month': int(m), 'day': int(d)}

        workers = catalog_service.list_workers(conn, parcel_id)
        labor_types = catalog_service.list_labor_types(conn, parcel_id)
        documents = documents_service.get_documents(conn, 'labor', id)
        return render_template('labor_form.html', item=item, item_date=item_date, workers=workers, labor_types=labor_types, documents=documents)
