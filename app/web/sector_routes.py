from datetime import date, timedelta

from flask import g, redirect, render_template, request, url_for

from ..auth import admin_required
from ..database import get_connection
from ..repositories import sector_flow as sector_repo
from ..services import sector_flow as sector_service

HISTORY_DAYS = 400
RECENT_RUN_DAYS = 14
DEFAULT_SUGGEST_DAYS = 30


def _parse_date(raw, default):
    try:
        return date.fromisoformat(raw) if raw else default
    except ValueError:
        return default


def register(app):
    @app.route('/parcela/<int:parcel_id>/sectors')
    def sectors(parcel_id):
        conn = get_connection()
        parcel = g.current_parcel
        today = date.today()
        period_to = _parse_date(request.args.get('to'), today)
        period_from = _parse_date(request.args.get('from'), period_to - timedelta(days=DEFAULT_SUGGEST_DAYS))

        runs = sector_service.load_runs(conn, parcel, HISTORY_DAYS)
        recent_since = today - timedelta(days=RECENT_RUN_DAYS)
        latest, imported = (sector_repo.latest_history_date(conn, parcel['vegga_unit_id'])
                            if parcel['vegga_unit_id'] else (None, None))

        return render_template(
            'sectors.html',
            parcel=parcel,
            sector_ids=sector_service.sector_ids(conn, parcel),
            references=sector_service.get_references(conn, parcel['id']),
            suggestions=sector_service.suggest_references(runs, period_from, period_to),
            period_from=period_from, period_to=period_to,
            table=sector_service.fortnight_table(runs),
            recent_runs=[r for r in reversed(runs) if r['start_local'].date() >= recent_since],
            alerts=sector_service.recent_alerts(conn, parcel, days=RECENT_RUN_DAYS),
            last_imported=imported,
            sync=sector_service.sync_status(parcel['vegga_unit_id']) if parcel['vegga_unit_id'] else None,
            factors={'high': sector_service.HIGH_FACTOR, 'low': sector_service.LOW_FACTOR,
                     'no_water': sector_service.NO_WATER_FACTOR},
        )

    @app.route('/parcela/<int:parcel_id>/sectors', methods=['POST'])
    @admin_required
    def save_sector_references(parcel_id):
        conn = get_connection()
        values = {}
        for sector_id in sector_service.sector_ids(conn, g.current_parcel):
            raw = request.form.get(f'ref_{sector_id}', '').strip().replace(',', '.')
            try:
                flow = float(raw) if raw else None
            except ValueError:
                flow = None
            if flow is not None and flow <= 0:
                flow = None
            values[sector_id] = (flow, request.form.get(f'notes_{sector_id}', '').strip() or None)
        sector_service.save_references(conn, parcel_id, values)
        return redirect(url_for('sectors', **{k: v for k, v in request.args.items() if k in ('from', 'to')}))

    @app.route('/parcela/<int:parcel_id>/sectors/sync', methods=['POST'])
    @admin_required
    def sync_sectors(parcel_id):
        unit_id = g.current_parcel['vegga_unit_id']
        if unit_id:
            sector_service.start_background_sync(unit_id, get_connection)
        return redirect(url_for('sectors'))
