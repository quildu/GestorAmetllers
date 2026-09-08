def insert(conn, parcel_id, entity_type, entity_id, original_filename, stored_filename, relative_path, mime_type, size_bytes):
    conn.execute(
        "INSERT INTO documents (parcel_id, entity_type, entity_id, original_filename, stored_filename, relative_path, mime_type, size_bytes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (parcel_id, entity_type, entity_id, original_filename, stored_filename, relative_path, mime_type, size_bytes)
    )


def list_by_entity(conn, entity_type, entity_id):
    return conn.execute(
        "SELECT * FROM documents WHERE entity_type = ? AND entity_id = ? AND is_deleted = 0 ORDER BY uploaded_at DESC",
        (entity_type, entity_id)
    ).fetchall()


def list_by_entity_type_for_parcel(conn, entity_type, parcel_id):
    return conn.execute(
        "SELECT * FROM documents WHERE entity_type = ? AND parcel_id = ? AND is_deleted = 0 ORDER BY uploaded_at",
        (entity_type, parcel_id)
    ).fetchall()


def get(conn, doc_id):
    return conn.execute("SELECT * FROM documents WHERE id=? AND is_deleted = 0", (doc_id,)).fetchone()


def soft_delete(conn, doc_id):
    conn.execute("UPDATE documents SET is_deleted = 1 WHERE id = ?", (doc_id,))
    conn.commit()
