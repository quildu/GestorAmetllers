import os
import sys

from dotenv import load_dotenv


def get_base_dir():
    # Detecta si estem corrent com a executable empaquetat
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


base_dir = get_base_dir()

# Carregar .env des del directori base
env_path = os.path.join(base_dir, ".env")
load_dotenv(env_path)


def get_db_path():
    # 1. Prioritat: Variable d'entorn (.env)
    db_path = os.getenv("DB_PATH")

    # 2. Defecte si no hi es
    if not db_path:
        db_path = "db/farm.db"

    # Si la ruta es relativa, la fem absoluta respecte al directori base
    if not os.path.isabs(db_path):
        db_path = os.path.normpath(os.path.join(base_dir, db_path))

    return db_path


def get_documents_path():
    documents_path = os.getenv("DOCUMENTS_PATH")

    if not documents_path:
        documents_path = "documents"

    if not os.path.isabs(documents_path):
        documents_path = os.path.normpath(os.path.join(base_dir, documents_path))

    return documents_path
