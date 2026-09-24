def list_with_totals(conn):
    return conn.execute("""
        SELECT p.*,
            (SELECT COALESCE(SUM(total_income), 0) FROM production WHERE parcel_id = p.id AND is_deleted = 0) as income_total,
            (SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE parcel_id = p.id AND is_deleted = 0)
                + (SELECT COALESCE(SUM(total_price), 0) FROM labors WHERE parcel_id = p.id AND is_deleted = 0) as expenses_total
        FROM parcels p
        WHERE p.is_deleted = 0
        ORDER BY p.name
    """).fetchall()


def get_active(conn, parcel_id):
    return conn.execute("SELECT * FROM parcels WHERE id = ? AND is_deleted = 0", (parcel_id,)).fetchone()


def list_all(conn):
    return conn.execute("SELECT * FROM parcels WHERE is_deleted = 0 ORDER BY name").fetchall()


def create(conn, name, hectares=0):
    cur = conn.execute("INSERT INTO parcels (name, hectares) VALUES (?, ?)", (name, hectares))
    conn.commit()
    return cur.lastrowid


def update_hectares(conn, parcel_id, hectares):
    conn.execute("UPDATE parcels SET hectares = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (hectares, parcel_id))
    conn.commit()
