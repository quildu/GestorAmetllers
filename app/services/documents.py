import os
import uuid

from werkzeug.utils import secure_filename

from ..config import get_documents_path
from ..repositories import documents as documents_repo

DOCUMENTS_DIR = get_documents_path()
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'heic', 'webp'}
MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10MB per fitxer


def allowed_document(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_DOCUMENT_EXTENSIONS


def save_documents(conn, parcel_id, entity_type, entity_id, files):
    """Desa al disc i registra a la taula 'documents' els fitxers rebuts per a una entitat concreta."""
    for f in files:
        if not f or not f.filename:
            continue
        if not allowed_document(f.filename):
            continue

        original_filename = secure_filename(f.filename)
        ext = original_filename.rsplit('.', 1)[1].lower()
        stored_filename = f"{uuid.uuid4().hex}.{ext}"

        entity_dir = os.path.join(DOCUMENTS_DIR, str(parcel_id), entity_type, str(entity_id))
        os.makedirs(entity_dir, exist_ok=True)
        dest_path = os.path.join(entity_dir, stored_filename)
        f.save(dest_path)

        size_bytes = os.path.getsize(dest_path)
        if size_bytes > MAX_DOCUMENT_SIZE_BYTES:
            os.remove(dest_path)
            continue

        relative_path = f"{parcel_id}/{entity_type}/{entity_id}/{stored_filename}"
        documents_repo.insert(conn, parcel_id, entity_type, entity_id, original_filename, stored_filename, relative_path, f.mimetype, size_bytes)
    conn.commit()


def get_documents(conn, entity_type, entity_id):
    return documents_repo.list_by_entity(conn, entity_type, entity_id)


def get_documents_by_type_for_parcel(conn, entity_type, parcel_id):
    return documents_repo.list_by_entity_type_for_parcel(conn, entity_type, parcel_id)


def get_documents_grouped_by_entity(conn, entity_type, parcel_id):
    rows = get_documents_by_type_for_parcel(conn, entity_type, parcel_id)
    grouped = {}
    for row in rows:
        grouped.setdefault(row['entity_id'], []).append(row)
    return grouped


def get_document(conn, doc_id):
    return documents_repo.get(conn, doc_id)


def delete_document(conn, doc_id):
    documents_repo.soft_delete(conn, doc_id)
