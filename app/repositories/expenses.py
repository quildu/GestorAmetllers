def insert(conn, parcel_id, date_str, expense_type_id, description, amount):
    cur = conn.execute(
        "INSERT INTO expenses (parcel_id, date, expense_type_id, description, amount) VALUES (?, ?, ?, ?, ?)",
        (parcel_id, date_str, expense_type_id, description, amount)
    )
    conn.commit()
    return cur.lastrowid


def update(conn, parcel_id, item_id, date_str, expense_type_id, description, amount):
    conn.execute(
        "UPDATE expenses SET date=?, expense_type_id=?, description=?, amount=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND parcel_id=?",
        (date_str, expense_type_id, description, amount, item_id, parcel_id)
    )
    conn.commit()


def get(conn, parcel_id, item_id):
    return conn.execute("SELECT * FROM expenses WHERE id=? AND parcel_id=? AND is_deleted = 0", (item_id, parcel_id)).fetchone()


def list_by_parcel(conn, parcel_id):
    return conn.execute("""
        SELECT e.*, et.name as expense_type_name
        FROM expenses e
        JOIN expense_types et ON e.expense_type_id = et.id
        WHERE e.is_deleted = 0 AND e.parcel_id = ?
        ORDER BY e.date DESC
    """, (parcel_id,)).fetchall()


def sum_by_parcel(conn, parcel_id):
    return conn.execute("SELECT SUM(amount) FROM expenses WHERE is_deleted = 0 AND parcel_id = ?", (parcel_id,)).fetchone()[0] or 0


def sum_by_type(conn, parcel_id):
    return conn.execute("""
        SELECT et.name, SUM(e.amount) as total
        FROM expenses e
        JOIN expense_types et ON e.expense_type_id = et.id
        WHERE e.is_deleted = 0 AND e.parcel_id = ?
        GROUP BY et.name
    """, (parcel_id,)).fetchall()


def soft_delete(conn, parcel_id, item_id):
    conn.execute("UPDATE expenses SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND parcel_id = ?", (item_id, parcel_id))
    conn.commit()


def list_all_by_parcel(conn, parcel_id):
    """Per a l'exportació CSV: inclou també els registres esborrats (comportament original)."""
    return conn.execute("SELECT * FROM expenses WHERE parcel_id = ?", (parcel_id,)).fetchall()
