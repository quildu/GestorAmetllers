import sqlite3
import os

from .config import get_db_path
from .paths import resource_path

DB_PATH = get_db_path()
SCHEMA_PATH = resource_path("db/schemas/schema.sql")

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
        conn.execute("INSERT INTO parcels (id, name, vegga_unit_id, hectares) VALUES (1, 'Servereta', 9982, 7)")
        conn.commit()

# Columnes afegides despres de la creacio inicial d'aquestes taules; cal donar-les
# d'alta en calent a les bases de dades que ja existien abans d'aquest canvi.
def migrate_extra_columns(conn):
    parcel_columns = [row[1] for row in conn.execute("PRAGMA table_info(parcels)").fetchall()]
    if 'hectares' not in parcel_columns:
        conn.execute("ALTER TABLE parcels ADD COLUMN hectares REAL NOT NULL DEFAULT 0")

    expense_columns = [row[1] for row in conn.execute("PRAGMA table_info(expenses)").fetchall()]
    if 'invoice_group' not in expense_columns:
        conn.execute("ALTER TABLE expenses ADD COLUMN invoice_group TEXT")

    # Cal crear l'index despres d'assegurar que la columna existeix (executescript
    # de schema.sql corre abans que aquesta migracio, i fallaria en BDs existents).
    conn.execute("CREATE INDEX IF NOT EXISTS idx_expenses_invoice_group ON expenses(invoice_group)")

    conn.commit()

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
        conn.commit()
        seed_first_parcel(conn)
        migrate_parcel_columns(conn)
        migrate_extra_columns(conn)

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    print(f"Connecting to DB at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully at:", DB_PATH)
