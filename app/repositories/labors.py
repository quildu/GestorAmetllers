def insert(conn, parcel_id, date_str, worker_id, labor_type_id, hours, price_per_hour, total_price, description):
    cur = conn.execute(
        "INSERT INTO labors (parcel_id, date, worker_id, labor_type_id, hours, price_per_hour, total_price, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (parcel_id, date_str, worker_id, labor_type_id, hours, price_per_hour, total_price, description)
    )
    conn.commit()
    return cur.lastrowid


def update(conn, parcel_id, item_id, date_str, worker_id, labor_type_id, hours, price_per_hour, total_price, description):
    conn.execute(
        "UPDATE labors SET date=?, worker_id=?, labor_type_id=?, hours=?, price_per_hour=?, total_price=?, description=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND parcel_id=?",
        (date_str, worker_id, labor_type_id, hours, price_per_hour, total_price, description, item_id, parcel_id)
    )
    conn.commit()


def get(conn, parcel_id, item_id):
    return conn.execute("SELECT * FROM labors WHERE id=? AND parcel_id=? AND is_deleted = 0", (item_id, parcel_id)).fetchone()


def list_by_parcel(conn, parcel_id):
    return conn.execute("""
        SELECT l.*, w.name as worker_name, lt.name as labor_type_name
        FROM labors l
        JOIN workers w ON l.worker_id = w.id
        JOIN labor_types lt ON l.labor_type_id = lt.id
        WHERE l.is_deleted = 0 AND l.parcel_id = ?
        ORDER BY l.date DESC
    """, (parcel_id,)).fetchall()


def sum_by_parcel(conn, parcel_id):
    return conn.execute("SELECT SUM(total_price) FROM labors WHERE is_deleted = 0 AND parcel_id = ?", (parcel_id,)).fetchone()[0] or 0


def soft_delete(conn, parcel_id, item_id):
    conn.execute("UPDATE labors SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND parcel_id = ?", (item_id, parcel_id))
    conn.commit()


def list_all_by_parcel(conn, parcel_id):
    """Per a l'exportació CSV: inclou també els registres esborrats (comportament original)."""
    return conn.execute("SELECT * FROM labors WHERE parcel_id = ?", (parcel_id,)).fetchall()
