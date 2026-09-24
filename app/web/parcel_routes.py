from flask import redirect, render_template, request, url_for

from ..auth import admin_required
from ..database import get_connection
from ..services import parcels as parcels_service


def register(app):
    @app.route('/')
    def list_parcels():
        conn = get_connection()
        parcels = parcels_service.list_parcels_with_totals(conn)
        return render_template('parcels.html', parcels=parcels)

    @app.route('/parcels/add', methods=['POST'])
    @admin_required
    def add_parcel():
        name = request.form.get('name', '').strip()
        hectares = request.form.get('hectares', '').strip()
        if name:
            conn = get_connection()
            parcels_service.create_parcel(conn, name, float(hectares) if hectares else 0)
        return redirect(url_for('list_parcels'))

    @app.route('/parcels/<int:parcel_id>/edit', methods=['POST'])
    @admin_required
    def update_parcel(parcel_id):
        name = request.form.get('name', '').strip()
        hectares = request.form.get('hectares', '').strip()
        if name:
            conn = get_connection()
            parcels_service.update_parcel(conn, parcel_id, name, float(hectares) if hectares else 0)
        return redirect(url_for('list_parcels'))

    @app.route('/parcela/<int:parcel_id>/')
    def index(parcel_id):
        conn = get_connection()
        summary = parcels_service.get_summary(conn, parcel_id)
        return render_template('index.html', **summary)
