"""Ganxos globals de la petició: resolució de la parcel·la actual i control d'accés.

Suport multi-parcel·la: totes les rutes de dades porten <parcel_id> a la URL.
Aquests ganxos permeten que les plantilles facin url_for('index') sense haver
de passar parcel_id explicitament: Flask l'injecta automaticament a partir de la
parcel·la de la petició actual (g.parcel_id).
"""

from flask import abort, current_app, g, redirect, request, url_for
from flask_login import current_user

from ..database import get_connection
from ..repositories import parcels as parcels_repo


def register(app):
    # Ordre important: load_current_parcel s'ha d'executar abans que require_login
    # (avui una parcel·la inexistent dona 404 encara que l'usuari no estigui logat).
    @app.before_request
    def load_current_parcel():
        parcel_id = (request.view_args or {}).get('parcel_id')
        if parcel_id is None:
            return
        conn = get_connection()
        parcel = parcels_repo.get_active(conn, parcel_id)
        if not parcel:
            abort(404)
        g.parcel_id = parcel_id
        g.current_parcel = parcel

    @app.url_defaults
    def inject_parcel_id(endpoint, values):
        if 'parcel_id' in values:
            return
        parcel_id = g.get('parcel_id')
        if not parcel_id:
            return
        if current_app.url_map.is_endpoint_expecting(endpoint, 'parcel_id'):
            values['parcel_id'] = parcel_id

    @app.before_request
    def require_login():
        if request.endpoint in ('login', 'static') or request.endpoint is None:
            return
        if not current_user.is_authenticated:
            return redirect(url_for('login', next=request.path))
