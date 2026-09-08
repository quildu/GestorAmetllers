def insert(conn, parcel_id, date_str, kilos, price_per_kilo, total_income):
    cur = conn.execute(
        "INSERT INTO production (parcel_id, date, kilos, price_per_kilo, total_income) VALUES (?, ?, ?, ?, ?)",
        (parcel_id, date_str, kilos, price_per_kilo, total_income)
    )
    conn.commit()
    return cur.lastrowid


def update(conn, parcel_id, item_id, date_str, kilos, price_per_kilo, total_income):
    conn.execute(
        "UPDATE production SET date=?, kilos=?, price_per_kilo=?, total_income=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND parcel_id=?",
        (date_str, kilos, price_per_kilo, total_income, item_id, parcel_id)
    )
    conn.commit()


def get(conn, parcel_id, item_id):
    return conn.execute("SELECT * FROM production WHERE id=? AND parcel_id=? AND is_deleted = 0", (item_id, parcel_id)).fetchone()


def list_by_parcel(conn, parcel_id):
    return conn.execute("SELECT * FROM production WHERE is_deleted = 0 AND parcel_id = ? ORDER BY date DESC", (parcel_id,)).fetchall()


def sum_by_parcel(conn, parcel_id):
    return conn.execute("SELECT SUM(total_income) FROM production WHERE is_deleted = 0 AND parcel_id = ?", (parcel_id,)).fetchone()[0] or 0


def soft_delete(conn, parcel_id, item_id):
    conn.execute("UPDATE production SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND parcel_id = ?", (item_id, parcel_id))
    conn.commit()


def list_all_by_parcel(conn, parcel_id):
    """Per a l'exportació CSV: inclou també els registres esborrats (comportament original)."""
    return conn.execute("SELECT * FROM production WHERE parcel_id = ?", (parcel_id,)).fetchall()
