from flask import g, render_template

from ..database import get_connection
from ..services import data_sync as data_sync_service


def register(app):
    @app.route('/parcela/<int:parcel_id>/dades')
    def data_sync(parcel_id):
        sources = data_sync_service.sources(get_connection(), g.current_parcel)
        return render_template('data_sync.html', parcel=g.current_parcel, sources=sources)
