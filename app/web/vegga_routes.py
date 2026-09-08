from flask import g, render_template, request

from ..database import get_connection
from ..services import vegga as vegga_service


def register(app):
    @app.route('/parcela/<int:parcel_id>/vegga')
    def vegga(parcel_id):
        conn = get_connection()
        unit_id = request.args.get('unit', type=int) or g.current_parcel['vegga_unit_id']

        if not unit_id:
            return render_template('vegga.html', unit_id=None, status=None, meters=[], filter_events=[],
                                   sectors=[], programs=[], analog_sensors=[], digital_sensors=[],
                                   sync_error=None, just_synced=False)

        force_refresh = request.args.get('refresh') == '1'
        needs_sync, sync_error = vegga_service.sync_if_stale(conn, unit_id, force=force_refresh)
        data = vegga_service.get_dashboard_data(conn, unit_id)

        return render_template('vegga.html', unit_id=unit_id, sync_error=sync_error, just_synced=needs_sync, **data)
