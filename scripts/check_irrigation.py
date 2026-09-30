"""
Comprovacio diaria del reg: descarrega l'historial de Vegga de cada parcel·la, compara el
cabal de cada reg amb la referencia del sector i avisa per Telegram de les anomalies noves.

Us:
    python scripts/check_irrigation.py                 # una comprovacio ara
    python scripts/check_irrigation.py --daemon            # cada dia a IRRIGATION_CHECK_AT (07:30 per defecte)
    python scripts/check_irrigation.py --test-telegram # envia un missatge de prova
"""

import argparse
import html
import os
import sys
import time
import traceback
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_connection, init_db
from app.integrations import telegram
from app.repositories import parcels as parcels_repo
from app.services import sector_flow

CHECK_DAYS = 3
MAX_TELEGRAM_LINES = 25  # Telegram talla els missatges de mes de 4096 caracters


def check_parcel(conn, parcel, days, sync=True):
    if sync:
        count = sector_flow.sync_history(conn, parcel['vegga_unit_id'])
        print(f"[{parcel['name']}] {count} registres descarregats de Vegga")

    pending = sector_flow.record_alerts(conn, parcel, days)
    references = sector_flow.get_references(conn, parcel['id'])
    if not references:
        print(f"[{parcel['name']}] cap sector té cabal de referència: no es pot comprovar")
    print(f"[{parcel['name']}] {len(pending)} anomalies noves")

    if pending:
        lines = [f"🚰 <b>{html.escape(parcel['name'])}</b>: regs amb cabal anòmal"]
        lines += [sector_flow.format_alert_line(a) for a in pending[:MAX_TELEGRAM_LINES]]
        if len(pending) > MAX_TELEGRAM_LINES:
            lines.append(f"… i {len(pending) - MAX_TELEGRAM_LINES} més. Mira la pàgina de sectors de l'app.")
        if telegram.send_message("\n".join(lines)):
            sector_flow.mark_notified(conn, parcel['id'], pending)
        elif not telegram.is_configured():
            print("Telegram no configurat: les anomalies només es veuran a l'app.")


def run_once(days, sync=True):
    init_db()
    conn = get_connection()
    for parcel in parcels_repo.list_all(conn):
        if not parcel['vegga_unit_id']:
            continue
        try:
            check_parcel(conn, parcel, days, sync)
        except Exception as e:
            traceback.print_exc()
            telegram.send_message(
                f"⚠️ <b>{html.escape(parcel['name'])}</b>: la comprovació diària del reg ha fallat.\n"
                f"<code>{html.escape(str(e))[:500]}</code>"
            )


def seconds_until(hhmm):
    hour, minute = (int(x) for x in hhmm.split(':'))
    now = datetime.now()
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Comprovació diària del cabal de reg per sector.")
    parser.add_argument("--days", type=int, default=CHECK_DAYS, help="Dies enrere a revisar")
    parser.add_argument("--no-sync", action="store_true", help="No descarregar de Vegga, només revisar la BD")
    parser.add_argument("--daemon", action="store_true", help="Queda en marxa i comprova cada dia")
    parser.add_argument("--at", default=sector_flow.DAILY_CHECK_AT, help="Hora de la comprovació diària (HH:MM, hora local)")
    parser.add_argument("--test-telegram", action="store_true", help="Envia un missatge de prova i surt")
    args = parser.parse_args()

    if args.test_telegram:
        sent = telegram.send_message("✅ Prova del Gestor de Casa Rita: els avisos de reg funcionen.")
        print(f"Missatges enviats: {sent}" if sent else "Telegram no configurat (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_IDS).")
        sys.exit(0 if sent else 1)

    if not args.daemon:
        run_once(args.days, sync=not args.no_sync)
        sys.exit(0)

    print(f"Comprovació diària programada a les {args.at}.", flush=True)
    while True:
        time.sleep(seconds_until(args.at))
        print(f"--- {datetime.now():%Y-%m-%d %H:%M} ---", flush=True)
        run_once(args.days)
