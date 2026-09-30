"""Estat de les dades externes de la parcel·la: d'on venen, quan s'actualitzen i quan es va fer l'ultima vegada.

Els textos es construeixen a partir de les mateixes constants que governen la sincronitzacio,
perque la pagina no expliqui una cosa diferent del que fa el codi.
"""

from datetime import date, datetime, timezone

from ..repositories import meteo as meteo_repo
from ..repositories import sector_flow as sector_repo
from ..repositories import vegga as vegga_repo
from . import irrigation, sector_flow, vegga

# Si l'ultima actualitzacio es mes antiga que aixo, s'avisa que potser alguna cosa no funciona.
VEGGA_HISTORY_STALE_HOURS = 30
VEGGA_DEVICE_STALE_HOURS = 24 * 7
XEMA_STALE_DAYS = irrigation.XEMA_LAG_DAYS + 2


def _parse_sqlite_utc(value):
    """CURRENT_TIMESTAMP de SQLite ('YYYY-MM-DD HH:MM:SS', en UTC) -> datetime local."""
    if not value:
        return None
    dt = datetime.fromisoformat(value.replace('Z', '').replace('T', ' ')).replace(tzinfo=timezone.utc)
    return dt.astimezone(sector_flow.LOCAL_TZ)


def _hours_ago(dt):
    return (datetime.now(timezone.utc) - dt).total_seconds() / 3600 if dt else None


def _vegga_history(conn, unit_id):
    latest_run, imported = sector_repo.latest_history_date(conn, unit_id)
    synced_at = _parse_sqlite_utc(imported)
    return {
        'key': 'vegga_history',
        'icon': '🚰',
        'title': 'Vegga · historial de regs per sector',
        'what': "Els regs que ha fet cada sector: hores, m³ i cabal mesurat pel comptador.",
        'used_in': ["Necessitats de reg → «Aigua aplicada»", "Sectors i consum", "Avisos de Telegram de fuites / obstruccions"],
        'when': [
            f"Automàticament cada dia a les {sector_flow.DAILY_CHECK_AT} (comprovació diària del cabal, amb avisos per Telegram).",
            "Manualment amb el botó «🔄 Descarregar historial de Vegga» de la pàgina Sectors i consum (només administradors).",
            f"Cada vegada es tornen a baixar els últims {sector_flow.RESYNC_OVERLAP_DAYS} dies per completar els regs que encara no havien acabat.",
        ],
        'not_when': "Obrir les pàgines Necessitats de reg o Sectors i consum NO descarrega res: es mostra el que es va baixar l'última vegada.",
        'synced_at': synced_at,
        'latest_data': _parse_sqlite_utc(latest_run),
        'latest_data_label': 'Últim reg registrat',
        'stale': synced_at is None or _hours_ago(synced_at) > VEGGA_HISTORY_STALE_HOURS,
        'stale_hint': "Fa més d'un dia que no s'actualitza: potser la comprovació diària no s'està executant.",
        'action': ('sectors', 'Anar a Sectors i consum'),
    }


def _vegga_device(conn, unit_id):
    synced_at = _parse_sqlite_utc(vegga_repo.last_sync_at(conn, unit_id))
    return {
        'key': 'vegga_device',
        'icon': '💧',
        'title': 'Vegga · estat del programador',
        'what': "Programes (hores i dies de reg), sectors, comptadors, neteges de filtres i sensors.",
        'used_in': ["Programador Vegga", "Necessitats de reg → «Comparació amb la programació de Vegga»"],
        'when': [
            f"Quan algú obre la pàgina Programador Vegga i fa més de {vegga.VEGGA_SYNC_INTERVAL_HOURS} h de l'última actualització "
            "(la pàgina triga una mica a carregar perquè entra a Vegga).",
            "Manualment amb el botó «🔄 Actualitza ara» de la mateixa pàgina.",
        ],
        'not_when': "No s'actualitza sol: si ningú obre Programador Vegga, la comparació de la pàgina de reg "
                    "fa servir la programació que hi havia l'última vegada. Si has canviat programes a Vegga, obre-la abans.",
        'synced_at': synced_at,
        'latest_data': None,
        'stale': synced_at is None or _hours_ago(synced_at) > VEGGA_DEVICE_STALE_HOURS,
        'stale_hint': "Fa més d'una setmana que no s'actualitza: obre Programador Vegga per tenir la programació al dia.",
        'action': ('vegga', 'Anar a Programador Vegga'),
    }


def _xema(conn, station):
    latest_date, imported = meteo_repo.last_import(conn, station)
    latest = date.fromisoformat(latest_date) if latest_date else None
    return {
        'key': 'xema',
        'icon': '🌦️',
        'title': f'Meteocat (XEMA) · estació {station}',
        'what': "Evapotranspiració de referència (ETo) i pluja diària de l'estació meteorològica.",
        'used_in': ["Necessitats de reg → temps de reg recomanat i m³ recomanats"],
        'when': [
            f"Quan algú obre Necessitats de reg i l'última dada té més de {irrigation.XEMA_LAG_DAYS} dies. "
            f"Si falla, no es torna a provar fins al cap de {irrigation.XEMA_RETRY_SECONDS // 60} minuts.",
            "Manualment amb el botó «🔄 Actualitzar ETo» de la mateixa pàgina.",
        ],
        'not_when': f"El Meteocat publica les dades amb 1-2 dies de retard: és normal que falti ahir i avui. "
                    f"La recomanació setmanal usa els últims 7 dies disponibles.",
        'synced_at': _parse_sqlite_utc(imported),
        'latest_data': latest,
        'latest_data_label': 'Última dada d\'ETo',
        'stale': latest is None or (date.today() - latest).days > XEMA_STALE_DAYS,
        'stale_hint': "Les dades d'ETo són antigues: la recomanació de reg pot no reflectir el temps d'aquesta setmana.",
        'action': ('irrigation', 'Anar a Necessitats de reg'),
    }


def _manual_eto(conn, parcel):
    latest_date, imported = meteo_repo.last_import(conn, irrigation.station_key(parcel))
    latest = date.fromisoformat(latest_date) if latest_date else None
    return {
        'key': 'manual',
        'icon': '✍️',
        'title': 'ETo introduïda a mà',
        'never_label': "Encara no s'ha entrat cap dada",
        'what': "La parcel·la no té estació meteorològica assignada: l'ETo i la pluja s'han d'entrar a mà.",
        'used_in': ["Necessitats de reg → temps de reg recomanat"],
        'when': ["Només quan algú l'entra al formulari de Necessitats de reg."],
        'not_when': "Assignant una estació del Meteocat a la fitxa de la parcel·la es descarregarà sola.",
        'synced_at': _parse_sqlite_utc(imported),
        'latest_data': latest,
        'latest_data_label': 'Última dada entrada',
        'stale': latest is None or (date.today() - latest).days > 7,
        'stale_hint': "Fa més d'una setmana que no s'entra cap dada: la recomanació no està al dia.",
        'action': ('irrigation', 'Anar a Necessitats de reg'),
    }


def sources(conn, parcel):
    """Fonts de dades externes que fa servir aquesta parcel·la (nomes les que te configurades)."""
    items = []
    if parcel['meteo_station']:
        items.append(_xema(conn, parcel['meteo_station']))
    else:
        items.append(_manual_eto(conn, parcel))
    if parcel['vegga_unit_id']:
        items.append(_vegga_history(conn, parcel['vegga_unit_id']))
        items.append(_vegga_device(conn, parcel['vegga_unit_id']))
    for item in items:
        item['hours_ago'] = _hours_ago(item['synced_at'])
    return items
