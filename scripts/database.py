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

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            conn.executescript(f.read())
        conn.commit()

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    print(f"Connecting to DB at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully at:", DB_PATH)
