"""Consum real per sector (historial de Vegga) i deteccio de fuites / obstruccions.

Cada reg es compara amb el cabal de referencia del sector (m3/h). Els regs en que dos
sectors reguen alhora es marquen com a solapats: el comptador suma l'aigua de tots dos
i no es pot atribuir el volum a cap sector.
"""

import statistics
import threading
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from ..repositories import sector_flow as repo

LOCAL_TZ = ZoneInfo("Europe/Madrid")

MIN_RUN_SECONDS = 600
HIGH_FACTOR = 1.20
LOW_FACTOR = 0.80
NO_WATER_FACTOR = 0.10
SUGGEST_BAND = 0.15
FIRST_SYNC_DAYS = 365
RESYNC_OVERLAP_DAYS = 2
# Vegga sol comptar un segon de mes (7201 s per un reg de 2 h): sense marge, regs consecutius semblarien solapats.
OVERLAP_TOLERANCE = timedelta(minutes=2)

ALERT_KINDS = ('high', 'low', 'no_water')

STATUS_LABELS = {
    'ok': 'Correcte',
    'high': 'Possible fuita',
    'low': 'Poca aigua / obstrucció',
    'no_water': 'Sense aigua',
    'overlap': 'Regs solapats',
    'short': 'Reg curt',
    'no_ref': 'Sense referència',
}

_sync_lock = threading.Lock()
_sync_state = {}


def parse_utc(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def utc_iso(dt):
    return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def local_start_of_day_utc(day):
    return utc_iso(datetime.combine(day, datetime.min.time(), tzinfo=LOCAL_TZ))


# --- Sincronitzacio amb Vegga -------------------------------------------------

def sync_history(conn, unit_id):
    """Descarrega de Vegga els regs nous (i repassa els ultims dies). Torna el nombre de registres."""
    from ..integrations.vegga.importer import import_sector_history
    from ..integrations.vegga.scraper import fetch_sector_history

    latest, _ = repo.latest_history_date(conn, unit_id)
    today = date.today()
    if latest:
        since = parse_utc(latest).date() - timedelta(days=RESYNC_OVERLAP_DAYS)
    else:
        since = today - timedelta(days=FIRST_SYNC_DAYS)
    items = fetch_sector_history(str(unit_id), since.isoformat(), today.isoformat())
    return import_sector_history(conn, unit_id, items)


def start_background_sync(unit_id, connection_factory):
    """Llanca la sincronitzacio en un fil perque la peticio web no esperi el login a Vegga."""
    with _sync_lock:
        state = _sync_state.get(unit_id)
        if state and state['running']:
            return False
        _sync_state[unit_id] = {'running': True, 'started': time.time(), 'error': None, 'count': None}

    def run():
        try:
            count = sync_history(connection_factory(), unit_id)
            _sync_state[unit_id].update(running=False, count=count)
        except Exception as e:
            _sync_state[unit_id].update(running=False, error=str(e))

    threading.Thread(target=run, daemon=True).start()
    return True


def sync_status(unit_id):
    return _sync_state.get(unit_id)


# --- Analisi dels regs --------------------------------------------------------

def annotate_runs(rows, references):
    runs = []
    for r in rows:
        start = parse_utc(r['date_from'])
        duration = r['duration_seconds'] or 0
        runs.append({
            'sector': r['sector_id'],
            'date_from': r['date_from'],
            'start_local': start.astimezone(LOCAL_TZ),
            'start': start,
            'end': start + timedelta(seconds=duration),
            'minutes': duration / 60,
            'volume': r['volume_m3'] or 0,
            'flow': r['flow_m3h'] or 0,
            'overlap': False,
        })

    runs.sort(key=lambda x: x['start'])
    for i, run in enumerate(runs):
        for other in runs[i + 1:]:
            if other['start'] >= run['end'] - OVERLAP_TOLERANCE:
                break
            if other['sector'] != run['sector']:
                run['overlap'] = other['overlap'] = True

    for run in runs:
        ref_row = references.get(run['sector'])
        ref = ref_row['reference_flow_m3h'] if ref_row else None
        run['reference'] = ref
        run['deviation_pct'] = (run['flow'] - ref) / ref * 100 if ref else None
        run['status'] = _classify(run, ref)
        run['status_label'] = STATUS_LABELS[run['status']]
    return runs


def _classify(run, ref):
    if run['minutes'] * 60 < MIN_RUN_SECONDS:
        return 'short'
    if run['overlap']:
        return 'overlap'
    if not ref:
        return 'no_ref'
    if run['flow'] < ref * NO_WATER_FACTOR:
        return 'no_water'
    if run['flow'] > ref * HIGH_FACTOR:
        return 'high'
    if run['flow'] < ref * LOW_FACTOR:
        return 'low'
    return 'ok'


def _is_clean(run):
    return run['status'] not in ('short', 'overlap')


def suggest_references(runs, period_from, period_to):
    """Cabal tipic de cada sector en un periode net: mediana, descartant els regs allunyats."""
    flows = defaultdict(list)
    for run in runs:
        day = run['start_local'].date()
        if period_from <= day <= period_to and _is_clean(run):
            flows[run['sector']].append(run['flow'])
    result = {}
    for sector, values in flows.items():
        med = statistics.median(values)
        core = [v for v in values if abs(v - med) <= med * SUGGEST_BAND] or values
        result[sector] = {'value': round(statistics.median(core), 2), 'n': len(core), 'total': len(values)}
    return result


def fortnight_table(runs):
    buckets = defaultdict(list)
    for run in runs:
        if not _is_clean(run):
            continue
        d = run['start_local']
        label = f"{d.year}-{d.month:02d}-{'1' if d.day <= 15 else '2'}"
        buckets[(run['sector'], label)].append(run['flow'])
    labels = sorted({label for _, label in buckets})
    sectors = sorted({s for s, _ in buckets})
    return {
        'labels': labels,
        'rows': [
            {'sector': s, 'flows': [statistics.median(buckets[(s, lbl)]) if buckets.get((s, lbl)) else None for lbl in labels]}
            for s in sectors
        ],
    }


def weekly_real_volume(runs, today=None):
    today = today or date.today()
    since = today - timedelta(days=7)
    week = [r for r in runs if since <= r['start_local'].date() < today]
    return {
        'from': since, 'to': today - timedelta(days=1),
        'volume_m3': sum(r['volume'] for r in week),
        'runs': len(week),
    }


def load_runs(conn, parcel, days):
    if not parcel['vegga_unit_id']:
        return []
    since = local_start_of_day_utc(date.today() - timedelta(days=days))
    rows = repo.list_history(conn, parcel['vegga_unit_id'], since)
    return annotate_runs(rows, repo.get_references(conn, parcel['id']))


# --- Alertes ------------------------------------------------------------------

def record_alerts(conn, parcel, days):
    """Desa les anomalies dels ultims dies i torna les que encara no s'han notificat."""
    for run in load_runs(conn, parcel, days):
        if run['status'] in ALERT_KINDS:
            repo.insert_alert(conn, parcel['id'], run['sector'], run['date_from'], run['status'],
                              run['flow'], run['reference'])
    conn.commit()
    return repo.list_pending_notifications(conn, parcel['id'])


def recent_alerts(conn, parcel, days=7):
    since = local_start_of_day_utc(date.today() - timedelta(days=days))
    return [
        {**dict(a), 'start_local': parse_utc(a['date_from']).astimezone(LOCAL_TZ),
         'label': STATUS_LABELS.get(a['kind'], a['kind'])}
        for a in repo.list_recent_alerts(conn, parcel['id'], since)
    ]


def format_alert_line(alert):
    icon = {'high': '🔴', 'low': '🟠', 'no_water': '⚫'}.get(alert['kind'], '⚠️')
    start = parse_utc(alert['date_from']).astimezone(LOCAL_TZ)
    ref = alert['reference_flow_m3h']
    dev = f", {(alert['flow_m3h'] - ref) / ref * 100:+.0f} %" if ref else ""
    return (f"{icon} Sector {alert['sector_id']} · {start:%d/%m %H:%M} · {alert['flow_m3h']:.2f} m³/h "
            f"(ref. {ref:.2f}{dev}) → {STATUS_LABELS.get(alert['kind'], alert['kind'])}")


def mark_notified(conn, parcel_id, alerts):
    repo.mark_notified(conn, parcel_id, [(a['sector_id'], a['date_from']) for a in alerts])


# --- Referencies --------------------------------------------------------------

def get_references(conn, parcel_id):
    return repo.get_references(conn, parcel_id)


def save_references(conn, parcel_id, values):
    """values: {sector_id: (reference_flow o None, notes)}"""
    for sector_id, (flow, notes) in values.items():
        repo.save_reference(conn, parcel_id, sector_id, flow, notes)
    conn.commit()


def sector_ids(conn, parcel):
    ids = set(get_references(conn, parcel['id']))
    if parcel['vegga_unit_id']:
        ids |= set(repo.history_sector_ids(conn, parcel['vegga_unit_id']))
    return sorted(ids)
