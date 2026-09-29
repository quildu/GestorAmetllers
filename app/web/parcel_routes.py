from datetime import date

from flask import g, redirect, render_template, request, url_for

from ..auth import admin_required
from ..database import get_connection
from ..integrations.meteo.xema import is_valid_station_code
from ..services import irrigation as irrigation_service
from ..services import parcels as parcels_service
from ..services import sector_flow as sector_service

FLOAT_FIELDS = ('hectares', 'row_spacing', 'tree_spacing', 'canopy_cover_pct', 'emitter_flow', 'emitter_spacing')
INT_FIELDS = ('planting_year', 'vegga_unit_id')


def _to_float(raw):
    return float(raw.replace(',', '.')) if raw else None


def _parse_parcel_form(form):
    data, errors = {}, []

    data['name'] = form.get('name', '').strip()
    if not data['name']:
        errors.append("El nom és obligatori.")

    for field in FLOAT_FIELDS:
        try:
            value = _to_float(form.get(field, '').strip())
        except ValueError:
            errors.append(f"Valor numèric no vàlid: {field}")
            continue
        if value is not None and value < 0:
            errors.append(f"El valor no pot ser negatiu: {field}")
        data[field] = value
    data['hectares'] = data['hectares'] or 0

    for field in INT_FIELDS:
        raw = form.get(field, '').strip()
        try:
            data[field] = int(raw) if raw else None
        except ValueError:
            errors.append(f"Valor enter no vàlid: {field}")

    if data.get('planting_year') and not (1900 <= data['planting_year'] <= date.today().year):
        errors.append("L'any de plantació no és vàlid.")
    if data.get('canopy_cover_pct') and data['canopy_cover_pct'] > 100:
        errors.append("La cobertura ha de ser un percentatge entre 0 i 100.")

    data['crop'] = form.get('crop', '').strip() or None
    data['variety'] = form.get('variety', '').strip() or None
    data['hose_lines'] = 2 if form.get('hose_lines') == '2' else 1

    try:
        efficiency_pct = _to_float(form.get('irrigation_efficiency', '').strip()) or 90
    except ValueError:
        efficiency_pct = None
    if efficiency_pct is None or not (50 <= efficiency_pct <= 100):
        errors.append("L'eficiència del reg ha de ser entre 50 i 100 %.")
    else:
        data['irrigation_efficiency'] = efficiency_pct / 100

    station = form.get('meteo_station', '').strip().upper()
    if station and not is_valid_station_code(station):
        errors.append("El codi d'estació meteorològica no és vàlid.")
    data['meteo_station'] = station or None

    return data, errors


def _render_form(parcel, errors=None, efficiency_pct=None):
    if efficiency_pct is None:
        stored = parcel['irrigation_efficiency'] if parcel and parcel['irrigation_efficiency'] else 0.9
        efficiency_pct = round(stored * 100)
    return render_template(
        'parcel_form.html',
        parcel=parcel,
        efficiency_pct=efficiency_pct,
        errors=errors or [],
        crops=irrigation_service.crop_choices(),
        stations=irrigation_service.list_stations(),
        current_year=date.today().year,
    )


def register(app):
    @app.route('/')
    def list_parcels():
        conn = get_connection()
        parcels = parcels_service.list_parcels_with_totals(conn)
        return render_template('parcels.html', parcels=parcels, crop_label=irrigation_service.crop_label,
                               current_year=date.today().year)

    @app.route('/gestio/parceles')
    @admin_required
    def manage_parcels():
        conn = get_connection()
        parcels = parcels_service.list_parcels_with_totals(conn)
        return render_template('parcel_manage.html', parcels=parcels, crop_label=irrigation_service.crop_label,
                               current_year=date.today().year)

    @app.route('/gestio/parceles/nova', methods=['GET', 'POST'])
    @admin_required
    def add_parcel():
        if request.method == 'GET':
            return _render_form(None)
        data, errors = _parse_parcel_form(request.form)
        if errors:
            return _render_form(request.form, errors, request.form.get('irrigation_efficiency'))
        conn = get_connection()
        parcels_service.create_parcel(conn, data)
        return redirect(url_for('manage_parcels'))

    @app.route('/parcela/<int:parcel_id>/fitxa', methods=['GET', 'POST'])
    @admin_required
    def edit_parcel(parcel_id):
        conn = get_connection()
        if request.method == 'GET':
            return _render_form(parcels_service.get_parcel(conn, parcel_id))
        data, errors = _parse_parcel_form(request.form)
        if errors:
            return _render_form({**request.form.to_dict(), 'id': parcel_id}, errors,
                                request.form.get('irrigation_efficiency'))
        parcels_service.update_parcel(conn, parcel_id, data)
        return redirect(url_for('manage_parcels'))

    @app.route('/parcela/<int:parcel_id>/')
    def index(parcel_id):
        conn = get_connection()
        summary = parcels_service.get_summary(conn, parcel_id)
        alerts = sector_service.recent_alerts(conn, g.current_parcel, days=7)
        return render_template('index.html', irrigation_alerts=alerts, **summary)
