"""Necessitats de reg per goteig a partir de l'ETo (metode FAO-56 / IRTA).

ETc = ETo x Kc(mes) x Kr(cobertura); necessitats netes = ETc - pluja efectiva;
litres/arbre = mm x marc (m2) / eficiencia; temps = litres / (goters x cabal).
"""

import time
from datetime import date, timedelta

from ..integrations.meteo import xema
from ..repositories import meteo as meteo_repo
from ..repositories import vegga as vegga_repo

# Kc mensual (gener..desembre). 0 = repos vegetatiu, no es recomana regar.
CROPS = {
    'ametller':  {'label': 'Ametller',  'kc': [0, 0, 0.40, 0.55, 0.75, 0.90, 0.95, 0.95, 0.80, 0.65, 0.40, 0]},
    'olivera':   {'label': 'Olivera',   'kc': [0.50, 0.50, 0.55, 0.60, 0.60, 0.55, 0.50, 0.50, 0.55, 0.60, 0.60, 0.50]},
    'vinya':     {'label': 'Vinya',     'kc': [0, 0, 0, 0.30, 0.45, 0.60, 0.70, 0.70, 0.55, 0.40, 0, 0]},
    'avellaner': {'label': 'Avellaner', 'kc': [0, 0, 0.30, 0.50, 0.70, 0.85, 0.90, 0.90, 0.80, 0.60, 0, 0]},
    'noguera':   {'label': 'Noguera',   'kc': [0, 0, 0, 0.50, 0.75, 0.95, 1.05, 1.05, 0.90, 0.65, 0, 0]},
    'pistatxer': {'label': 'Pistatxer', 'kc': [0, 0, 0, 0.40, 0.70, 0.95, 1.10, 1.10, 0.90, 0.60, 0, 0]},
    'fruiter':   {'label': 'Fruiter (pomera, presseguer...)', 'kc': [0, 0, 0.45, 0.60, 0.80, 0.95, 1.00, 1.00, 0.85, 0.65, 0, 0]},
}

MONTH_NAMES = ['Gen', 'Feb', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Oct', 'Nov', 'Des']

MIN_EFFECTIVE_RAIN_MM = 5
EFFECTIVE_RAIN_FACTOR = 0.75
ADULT_COVER = 0.65
COVER_GROWTH_PER_YEAR = 0.12
XEMA_LAG_DAYS = 2
XEMA_RETRY_SECONDS = 3600
HISTORY_DAYS = 21
MANUAL_STATION = 'MANUAL'

_last_sync_attempt = {}
_stations_cache = {'at': 0, 'items': []}


def crop_choices():
    return [(key, c['label']) for key, c in CROPS.items()]


def crop_label(key):
    return CROPS[key]['label'] if key in CROPS else (key or '')


def list_stations():
    if not _stations_cache['items'] or time.time() - _stations_cache['at'] > 86400:
        try:
            _stations_cache['items'] = xema.fetch_stations()
            _stations_cache['at'] = time.time()
        except Exception:
            pass
    return _stations_cache['items']


def station_key(parcel):
    return parcel['meteo_station'] or MANUAL_STATION


def sync_eto_if_stale(conn, station_code, force=False):
    """Descarrega l'ETo de la XEMA si les dades locals estan endarrerides. Torna un missatge d'error o None."""
    if not xema.is_valid_station_code(station_code):
        return None
    today = date.today()
    latest = meteo_repo.latest_date(conn, station_code)
    if not force and latest and latest >= (today - timedelta(days=XEMA_LAG_DAYS)).isoformat():
        return None
    if not force and time.time() - _last_sync_attempt.get(station_code, 0) < XEMA_RETRY_SECONDS:
        return None
    _last_sync_attempt[station_code] = time.time()

    since = today - timedelta(days=HISTORY_DAYS + 7)
    if latest and not force:
        since = max(since, date.fromisoformat(latest) - timedelta(days=3))
    try:
        daily = xema.fetch_daily(station_code, since.isoformat())
    except Exception as e:
        return f"No s'han pogut descarregar les dades de la XEMA: {e}"
    meteo_repo.upsert_xema(conn, station_code, daily)
    return None


def save_manual_eto(conn, parcel, day, eto, rain):
    meteo_repo.upsert_manual(conn, station_key(parcel), day, eto, rain)


def _cover_fraction(parcel, today):
    if parcel['canopy_cover_pct']:
        return min(1.0, parcel['canopy_cover_pct'] / 100), 'entrada'
    if parcel['planting_year']:
        age = max(1, today.year - parcel['planting_year'])
        return min(ADULT_COVER, COVER_GROWTH_PER_YEAR * age), 'edat'
    return None, None


def _kr(cover):
    # Fereres (1981): reduccio per cobertura en reg localitzat.
    if cover is None:
        return 1.0
    return min(1.0, 2 * cover)


def effective_rain(rain_mm):
    if not rain_mm or rain_mm < MIN_EFFECTIVE_RAIN_MM:
        return 0.0
    return rain_mm * EFFECTIVE_RAIN_FACTOR


def missing_fields(parcel):
    required = {
        'crop': 'cultiu', 'row_spacing': 'distància entre files', 'tree_spacing': 'distància entre arbres',
        'emitter_flow': 'cabal del goter', 'emitter_spacing': 'separació entre goters',
    }
    missing = [label for field, label in required.items() if not parcel[field]]
    if parcel['crop'] and parcel['crop'] not in CROPS:
        missing.append('cultiu amb Kc conegut')
    return missing


def tree_geometry(parcel):
    area = parcel['row_spacing'] * parcel['tree_spacing']
    hose_lines = parcel['hose_lines'] or 1
    emitters = parcel['tree_spacing'] / parcel['emitter_spacing'] * hose_lines
    flow_per_tree = emitters * parcel['emitter_flow']
    return {
        'area_m2': area,
        'trees_per_ha': 10000 / area,
        'emitters_per_tree': emitters,
        'flow_per_tree_lh': flow_per_tree,
        'application_rate_mmh': flow_per_tree / area,
        'hose_lines': hose_lines,
    }


SEQUENTIAL_PROGRAM = 1
WEEK_DAYS = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')


def _chain_head(program, by_id):
    """Un programa sequencial arrenca quan acaba el de start_minutes: els dies que valen son els del primer de la cadena."""
    seen = set()
    while program and program['program_type'] == SEQUENTIAL_PROGRAM:
        if program['program_id'] in seen:
            return None
        seen.add(program['program_id'])
        program = by_id.get(program['start_minutes'])
    return program


def _programmed_minutes_per_sector(conn, unit_id):
    programs = vegga_repo.get_active_programs(conn, unit_id)
    by_id = {p['program_id']: p for p in programs}
    sectors = {}
    for p in programs:
        if not p['sector1'] or not p['duration_seconds']:
            continue
        head = _chain_head(p, by_id)
        active_days = sum(1 for d in WEEK_DAYS if head and head[d])
        if not active_days:
            continue
        s = sectors.setdefault(p['sector1'], {'sector': p['sector1'], 'minutes_week': 0, 'programs': []})
        s['minutes_week'] += p['duration_seconds'] / 60 * active_days
        s['programs'].append(p['name'])
    return sorted(sectors.values(), key=lambda s: s['sector'])


def compute(conn, parcel, today=None):
    today = today or date.today()
    since = (today - timedelta(days=HISTORY_DAYS)).isoformat()
    rows = meteo_repo.list_range(conn, station_key(parcel), since)

    result = {'missing': missing_fields(parcel), 'crop_label': crop_label(parcel['crop']),
              'age': today.year - parcel['planting_year'] if parcel['planting_year'] else None}
    if result['missing']:
        result['days'] = [dict(r) for r in rows]
        return result

    geo = tree_geometry(parcel)
    efficiency = parcel['irrigation_efficiency'] or 0.9
    cover, cover_source = _cover_fraction(parcel, today)
    kr = _kr(cover)
    kc_table = CROPS[parcel['crop']]['kc']

    days = []
    for r in rows:
        kc = kc_table[int(r['date'][5:7]) - 1]
        etc = r['eto'] * kc * kr
        pe = effective_rain(r['rain'])
        days.append({
            'date': r['date'], 'eto': r['eto'], 'rain': r['rain'], 'source': r['source'],
            'kc': kc, 'etc': etc, 'pe': pe, 'net': max(0.0, etc - pe),
        })

    week = days[:7]
    weekly = None
    if week:
        etc_sum = sum(d['etc'] for d in week)
        pe_sum = sum(d['pe'] for d in week)
        # Si falten dies, s'extrapola a 7 dies perque la xifra sigui comparable amb Vegga.
        net_mm_week = max(0.0, etc_sum - pe_sum) * 7 / len(week)
        litres_tree_week = net_mm_week * geo['area_m2'] / efficiency
        minutes_week = litres_tree_week / geo['flow_per_tree_lh'] * 60
        weekly = {
            'from': week[-1]['date'], 'to': week[0]['date'], 'days': len(week),
            'eto_sum': sum(d['eto'] for d in week), 'rain_sum': sum(d['rain'] or 0 for d in week),
            'etc_sum': etc_sum, 'pe_sum': pe_sum, 'net_mm': net_mm_week,
            'litres_tree_week': litres_tree_week,
            'litres_tree_day': litres_tree_week / 7,
            'minutes_week': minutes_week,
            'minutes_day': minutes_week / 7,
            'm3_ha_week': net_mm_week * 10 / efficiency,
        }

    comparison = []
    if weekly and parcel['vegga_unit_id']:
        for s in _programmed_minutes_per_sector(conn, parcel['vegga_unit_id']):
            recommended = weekly['minutes_week']
            diff_pct = (s['minutes_week'] - recommended) / recommended * 100 if recommended else None
            comparison.append({**s, 'recommended': recommended, 'diff_pct': diff_pct})

    result.update({
        'geometry': geo, 'efficiency': efficiency, 'cover': cover, 'cover_source': cover_source, 'kr': kr,
        'kc_now': kc_table[today.month - 1],
        'kc_table': list(zip(MONTH_NAMES, kc_table)),
        'days': days, 'weekly': weekly, 'comparison': comparison,
    })
    return result
