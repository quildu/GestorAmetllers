from datetime import date

from flask import g, redirect, render_template, request, url_for

from ..auth import admin_required
from ..database import get_connection
from ..services import irrigation as irrigation_service
from ..services import sector_flow as sector_service


def register(app):
    @app.route('/parcela/<int:parcel_id>/reg')
    def irrigation(parcel_id):
        conn = get_connection()
        parcel = g.current_parcel
        sync_error = None
        if parcel['meteo_station']:
            sync_error = irrigation_service.sync_eto_if_stale(
                conn, parcel['meteo_station'], force=request.args.get('refresh') == '1')
        result = irrigation_service.compute(conn, parcel)
        real_week = None
        if parcel['vegga_unit_id']:
            real_week = sector_service.weekly_real_volume(sector_service.load_runs(conn, parcel, days=8))
        return render_template('irrigation.html', parcel=parcel, r=result, sync_error=sync_error,
                               real_week=real_week, today=date.today().isoformat())

    @app.route('/parcela/<int:parcel_id>/reg/eto', methods=['POST'])
    @admin_required
    def add_manual_eto(parcel_id):
        try:
            day = date.fromisoformat(request.form.get('date', ''))
            eto = float(request.form.get('eto', '').replace(',', '.'))
            rain_raw = request.form.get('rain', '').strip().replace(',', '.')
            rain = float(rain_raw) if rain_raw else 0.0
        except ValueError:
            return redirect(url_for('irrigation', error='manual'))
        if 0 <= eto < 20 and rain >= 0 and day <= date.today():
            conn = get_connection()
            irrigation_service.save_manual_eto(conn, g.current_parcel, day.isoformat(), eto, rain)
        return redirect(url_for('irrigation'))
