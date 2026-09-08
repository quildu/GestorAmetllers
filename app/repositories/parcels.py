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


def create(conn, name):
    cur = conn.execute("INSERT INTO parcels (name) VALUES (?)", (name,))
    conn.commit()
    return cur.lastrowid
