def latest_history_date(conn, unit_id):
    row = conn.execute(
        "SELECT MAX(date_from) AS d, MAX(imported_at) AS imported FROM vegga_irrigation_history WHERE unit_id = ?",
        (unit_id,)
    ).fetchone()
    return row['d'], row['imported']


def list_history(conn, unit_id, since_utc):
    return conn.execute("""
        SELECT * FROM vegga_irrigation_history
        WHERE unit_id = ? AND date_from >= ?
        ORDER BY date_from
    """, (unit_id, since_utc)).fetchall()


def history_sector_ids(conn, unit_id):
    rows = conn.execute(
        "SELECT DISTINCT sector_id FROM vegga_irrigation_history WHERE unit_id = ?", (unit_id,)
    ).fetchall()
    return [r['sector_id'] for r in rows]


def get_references(conn, parcel_id):
    rows = conn.execute("SELECT * FROM irrigation_sectors WHERE parcel_id = ?", (parcel_id,)).fetchall()
    return {r['sector_id']: r for r in rows}


def save_reference(conn, parcel_id, sector_id, reference_flow, notes):
    conn.execute("""
        INSERT INTO irrigation_sectors (parcel_id, sector_id, reference_flow_m3h, notes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(parcel_id, sector_id) DO UPDATE SET
            reference_flow_m3h = excluded.reference_flow_m3h, notes = excluded.notes,
            updated_at = CURRENT_TIMESTAMP
    """, (parcel_id, sector_id, reference_flow, notes))


def insert_alert(conn, parcel_id, sector_id, date_from, kind, flow, reference):
    """Torna True si l'alerta es nova."""
    cur = conn.execute("""
        INSERT OR IGNORE INTO irrigation_alerts (parcel_id, sector_id, date_from, kind, flow_m3h, reference_flow_m3h)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (parcel_id, sector_id, date_from, kind, flow, reference))
    return cur.rowcount == 1


def mark_notified(conn, parcel_id, keys):
    conn.executemany(
        "UPDATE irrigation_alerts SET notified = 1 WHERE parcel_id = ? AND sector_id = ? AND date_from = ?",
        [(parcel_id, sector_id, date_from) for sector_id, date_from in keys]
    )
    conn.commit()


def list_pending_notifications(conn, parcel_id):
    return conn.execute("""
        SELECT * FROM irrigation_alerts WHERE parcel_id = ? AND notified = 0 ORDER BY date_from, sector_id
    """, (parcel_id,)).fetchall()


def list_recent_alerts(conn, parcel_id, since_utc):
    return conn.execute("""
        SELECT * FROM irrigation_alerts WHERE parcel_id = ? AND date_from >= ?
        ORDER BY date_from DESC, sector_id
    """, (parcel_id, since_utc)).fetchall()
