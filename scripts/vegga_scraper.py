"""
Wrapper de línia de comandes per a l'extracció de dades de Vegga.
La lògica real viu a app/integrations/vegga/scraper.py, reutilitzada també
pel servei de sincronització de l'aplicació web (app/services/vegga.py).

Us:
    python scripts/vegga_scraper.py --unit 9982 --pages filters,sectors
    python scripts/vegga_scraper.py --unit 9982 --pages filters,sectors --show
"""

import argparse
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.integrations.vegga.scraper import scrape

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extreu dades de Vegga via login automatic.")
    parser.add_argument("--unit", required=True, help="ID de l'equip/unitat de reg (p.ex. 9982)")
    parser.add_argument("--pages", default="filters,sectors", help="Subpagines a visitar, separades per coma")
    parser.add_argument("--show", action="store_true", help="Mostra el navegador (per depurar)")
    args = parser.parse_args()

    try:
        scrape(args.unit, [p.strip() for p in args.pages.split(",") if p.strip()], args.show)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
