def hours_since_sync(conn, unit_id):
    row = conn.execute("""
        SELECT (julianday('now') - julianday(MAX(snapshot_at))) * 24 AS hours_since
        FROM vegga_status WHERE unit_id = ?
    """, (unit_id,)).fetchone()
    return row['hours_since'] if row and row['hours_since'] is not None else None


def get_latest_status(conn, unit_id):
    return conn.execute(
        "SELECT * FROM vegga_status WHERE unit_id = ? ORDER BY id DESC LIMIT 1", (unit_id,)
    ).fetchone()


def get_latest_meters(conn, unit_id):
    return conn.execute("""
        SELECT * FROM vegga_water_meters
        WHERE unit_id = ? AND id IN (
            SELECT MAX(id) FROM vegga_water_meters WHERE unit_id = ? GROUP BY meter_id
        )
        ORDER BY CAST(meter_id AS INTEGER)
    """, (unit_id, unit_id)).fetchall()


def get_recent_filter_events(conn, unit_id, limit=20):
    return conn.execute("""
        SELECT * FROM vegga_filter_events
        WHERE unit_id = ?
        ORDER BY CAST(vegga_id AS INTEGER) DESC
        LIMIT ?
    """, (unit_id, limit)).fetchall()


def get_active_sectors(conn, unit_id):
    return conn.execute("""
        SELECT * FROM vegga_sectors
        WHERE unit_id = ? AND sector_op = 1
        ORDER BY sector_id
    """, (unit_id,)).fetchall()


def get_active_programs(conn, unit_id):
    return conn.execute("""
        SELECT * FROM vegga_programs
        WHERE unit_id = ? AND (duration_seconds > 0 OR sector1 > 0)
        ORDER BY program_id
    """, (unit_id,)).fetchall()


def get_latest_analog_sensors(conn, unit_id):
    return conn.execute("""
        SELECT * FROM vegga_analog_sensors
        WHERE unit_id = ? AND snapshot_at = (SELECT MAX(snapshot_at) FROM vegga_analog_sensors WHERE unit_id = ?)
    """, (unit_id, unit_id)).fetchall()


def get_latest_digital_sensors(conn, unit_id):
    return conn.execute("""
        SELECT * FROM vegga_digital_sensors
        WHERE unit_id = ? AND snapshot_at = (SELECT MAX(snapshot_at) FROM vegga_digital_sensors WHERE unit_id = ?)
    """, (unit_id, unit_id)).fetchall()
