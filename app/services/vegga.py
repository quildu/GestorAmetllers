from ..repositories import vegga as vegga_repo

VEGGA_PAGES = ["a25/programs", "sectors", "fertilizers", "filters", "sensors"]
VEGGA_SYNC_INTERVAL_HOURS = 4


def sync_if_stale(conn, unit_id, force=False):
    """Sincronitza amb Vegga si fa massa temps que no ho fem (o si es força). Torna (needs_sync, sync_error)."""
    hours_since = vegga_repo.hours_since_sync(conn, unit_id)
    needs_sync = force or hours_since is None or hours_since > VEGGA_SYNC_INTERVAL_HOURS

    sync_error = None
    if needs_sync:
        # Import diferit: evita dependre de Playwright si no cal sincronitzar.
        from ..integrations.vegga.scraper import scrape as vegga_scrape
        try:
            vegga_scrape(str(unit_id), VEGGA_PAGES, show=False)
        except Exception as e:
            sync_error = str(e)

    return needs_sync, sync_error


def get_dashboard_data(conn, unit_id):
    return {
        'status': vegga_repo.get_latest_status(conn, unit_id),
        'meters': vegga_repo.get_latest_meters(conn, unit_id),
        'filter_events': vegga_repo.get_recent_filter_events(conn, unit_id),
        'sectors': vegga_repo.get_active_sectors(conn, unit_id),
        'programs': vegga_repo.get_active_programs(conn, unit_id),
        'analog_sensors': vegga_repo.get_latest_analog_sensors(conn, unit_id),
        'digital_sensors': vegga_repo.get_latest_digital_sensors(conn, unit_id),
    }
