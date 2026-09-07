import sqlite3
import os
import sys
from .config import get_db_path

def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        return os.path.join(getattr(sys, '_MEIPASS', ''), relative_path)
    return os.path.join(os.path.dirname(__file__), '..', relative_path)

DB_PATH = get_db_path()
SCHEMA_PATH = resource_path('db/schemas/schema.sql')

# Taules que van rebre una columna parcel_id quan es va introduir el suport multi-parcel·la.
# Les bases de dades noves ja la tenen via schema.sql; aquesta llista nomes serveix per
# actualitzar en calent una base de dades que ja existia abans d'aquest canvi.
TABLES_WITH_PARCEL_ID = ['workers', 'labor_types', 'labors', 'production', 'expense_types', 'expenses', 'documents']

def migrate_parcel_columns(conn):
    for table in TABLES_WITH_PARCEL_ID:
        columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if 'parcel_id' not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN parcel_id INTEGER NOT NULL DEFAULT 1")
    conn.commit()

def seed_first_parcel(conn):
    if not conn.execute("SELECT 1 FROM parcels LIMIT 1").fetchone():
        conn.execute("INSERT INTO parcels (id, name, vegga_unit_id) VALUES (1, 'Servereta', 9982)")
        conn.commit()

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
        conn.commit()
        seed_first_parcel(conn)
        migrate_parcel_columns(conn)

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    print(f"Connecting to DB at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully at:", DB_PATH)
