"""Accés a dades per a les taules de catàleg senzilles: workers, labor_types i expense_types."""

DEFAULT_LABOR_TYPES = ['Poda', 'Sulfatar', 'Recol·lecció', 'Reg', 'Altres']
DEFAULT_EXPENSE_TYPES = ['Productes', 'Aigua', 'Averies', 'Gasoil', 'Altres']


def list_workers(conn, parcel_id):
    return conn.execute("SELECT * FROM workers WHERE is_deleted = 0 AND parcel_id = ? ORDER BY name", (parcel_id,)).fetchall()


def list_labor_types(conn, parcel_id):
    return conn.execute("SELECT * FROM labor_types WHERE is_deleted = 0 AND parcel_id = ? ORDER BY name", (parcel_id,)).fetchall()


def list_expense_types(conn, parcel_id):
    return conn.execute("SELECT * FROM expense_types WHERE is_deleted = 0 AND parcel_id = ? ORDER BY name", (parcel_id,)).fetchall()


def insert_worker(conn, parcel_id, name):
    cur = conn.execute("INSERT INTO workers (name, parcel_id) VALUES (?, ?)", (name, parcel_id))
    conn.commit()
    return cur.lastrowid


def insert_labor_type(conn, parcel_id, name):
    cur = conn.execute("INSERT INTO labor_types (name, parcel_id) VALUES (?, ?)", (name, parcel_id))
    conn.commit()
    return cur.lastrowid


def insert_expense_type(conn, parcel_id, name):
    cur = conn.execute("INSERT INTO expense_types (name, parcel_id) VALUES (?, ?)", (name, parcel_id))
    conn.commit()
    return cur.lastrowid


def seed_defaults_for_parcel(conn, parcel_id):
    conn.executemany("INSERT INTO labor_types (name, parcel_id) VALUES (?, ?)",
                      [(name, parcel_id) for name in DEFAULT_LABOR_TYPES])
    conn.executemany("INSERT INTO expense_types (name, parcel_id) VALUES (?, ?)",
                      [(name, parcel_id) for name in DEFAULT_EXPENSE_TYPES])
    conn.commit()


def has_labor_types(conn, parcel_id):
    return conn.execute("SELECT 1 FROM labor_types WHERE parcel_id = ? LIMIT 1", (parcel_id,)).fetchone() is not None


def has_expense_types(conn, parcel_id):
    return conn.execute("SELECT 1 FROM expense_types WHERE parcel_id = ? LIMIT 1", (parcel_id,)).fetchone() is not None


def seed_default_labor_types(conn, parcel_id):
    conn.executemany("INSERT INTO labor_types (name, parcel_id) VALUES (?, ?)",
                      [(name, parcel_id) for name in DEFAULT_LABOR_TYPES])


def seed_default_expense_types(conn, parcel_id):
    conn.executemany("INSERT INTO expense_types (name, parcel_id) VALUES (?, ?)",
                      [(name, parcel_id) for name in DEFAULT_EXPENSE_TYPES])
