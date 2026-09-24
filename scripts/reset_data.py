"""Eina de manteniment per netejar dades de prova de la base de dades real.

Dos modes:
  transactions  Esborra nomes labors, produccio, despeses i documents.
                Mante parcel·les, treballadors i catalegs (tipus de feina/despesa) intactes.
  full          Esborra TOT i deixa la BD com acabada d'instal·lar (torna a crear
                nomes la parcel·la "Servereta" per defecte amb els catalegs base).

Per seguretat, sense --confirm nomes es mostra un recompte (dry-run), no s'esborra res.

Execucio dins el contenidor de produccio:
    docker compose exec app python scripts/reset_data.py --mode transactions --confirm

Execucio local (fora de Docker), amb el mateix DB_PATH que fa servir l'app:
    python scripts/reset_data.py --mode transactions --confirm
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_connection, init_db, DB_PATH
from app.services.catalog import seed_data

TRANSACTION_TABLES = ['documents', 'expenses', 'production', 'labors']
FULL_RESET_TABLES = ['documents', 'expenses', 'production', 'labors', 'expense_types', 'labor_types', 'workers', 'parcels']


def count_rows(conn, tables):
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}


def main():
    parser = argparse.ArgumentParser(description="Neteja dades de prova de la base de dades.")
    parser.add_argument('--mode', choices=['transactions', 'full'], required=True,
                         help="'transactions': esborra labors/produccio/despeses/documents, mante parcel·les i catalegs. "
                              "'full': esborra absolutament tot i recrea la BD des de zero.")
    parser.add_argument('--confirm', action='store_true', help="Sense aixo nomes es mostra que s'esborraria (dry-run).")
    args = parser.parse_args()

    print(f"Base de dades: {DB_PATH}\n")

    conn = get_connection()
    tables = TRANSACTION_TABLES if args.mode == 'transactions' else FULL_RESET_TABLES

    print("Registres que s'esborrarien:")
    for table, count in count_rows(conn, tables).items():
        print(f"  {table}: {count}")

    if not args.confirm:
        print("\nDry-run: no s'ha esborrat res. Torna a executar amb --confirm per aplicar-ho de veritat.")
        conn.close()
        return

    for table in tables:
        conn.execute(f"DELETE FROM {table}")
    conn.commit()

    if args.mode == 'full':
        conn.execute("DELETE FROM sqlite_sequence")
        conn.commit()
        conn.close()
        init_db()
        seed_data()
        print("\nFET: base de dades reiniciada completament (parcel·la 'Servereta' i catalegs per defecte recreats).")
    else:
        conn.close()
        print("\nFET: treballs, produccio, despeses i documents esborrats. Parcel·les, treballadors i catalegs intactes.")


if __name__ == '__main__':
    main()
