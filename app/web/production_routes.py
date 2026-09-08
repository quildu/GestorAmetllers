from flask import abort, redirect, render_template, request, url_for

from ..database import get_connection
from ..services import documents as documents_service
from ..services import production as production_service


def register(app):
    @app.route('/parcela/<int:parcel_id>/production/add', methods=['GET', 'POST'])
    def add_production(parcel_id):
        if request.method == 'POST':
            conn = get_connection()
            production_id = production_service.create_production(conn, parcel_id, request.form)
            documents_service.save_documents(conn, parcel_id, 'production', production_id, request.files.getlist('documents'))
            return redirect(url_for('index'))
        return render_template('production_form.html')

    @app.route('/parcela/<int:parcel_id>/production/edit/<int:id>', methods=['GET', 'POST'])
    def edit_production(parcel_id, id):
        conn = get_connection()
        if request.method == 'POST':
            production_service.update_production(conn, parcel_id, id, request.form)
            documents_service.save_documents(conn, parcel_id, 'production', id, request.files.getlist('documents'))
            return redirect(url_for('history'))

        item = production_service.get_production(conn, parcel_id, id)
        if not item:
            abort(404)
        y, m, d = item['date'].split('-')
        item_date = {'year': int(y), 'month': int(m), 'day': int(d)}
        documents = documents_service.get_documents(conn, 'production', id)
        return render_template('production_form.html', item=item, item_date=item_date, documents=documents)
