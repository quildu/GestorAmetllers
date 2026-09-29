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


EDITABLE_FIELDS = (
    'name', 'hectares', 'vegga_unit_id', 'crop', 'variety', 'planting_year',
    'row_spacing', 'tree_spacing', 'canopy_cover_pct', 'emitter_flow',
    'emitter_spacing', 'hose_lines', 'irrigation_efficiency', 'meteo_station',
)


def create(conn, data):
    fields = [f for f in EDITABLE_FIELDS if f in data]
    cur = conn.execute(
        f"INSERT INTO parcels ({', '.join(fields)}) VALUES ({', '.join('?' for _ in fields)})",
        [data[f] for f in fields]
    )
    conn.commit()
    return cur.lastrowid


def update(conn, parcel_id, data):
    fields = [f for f in EDITABLE_FIELDS if f in data]
    assignments = ', '.join(f"{f} = ?" for f in fields)
    conn.execute(
        f"UPDATE parcels SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        [data[f] for f in fields] + [parcel_id]
    )
    conn.commit()
