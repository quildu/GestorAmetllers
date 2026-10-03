"""Enviament d'avisos per Telegram. Configuracio al .env: TELEGRAM_BOT_TOKEN i TELEGRAM_CHAT_IDS."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from .. import config  # noqa: F401 - garanteix que .env s'ha carregat

TIMEOUT_SECONDS = 15


def _settings():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_ids = [c.strip() for c in os.getenv("TELEGRAM_CHAT_IDS", "").split(",") if c.strip()]
    return token, chat_ids


def is_configured():
    token, chat_ids = _settings()
    return bool(token and chat_ids)


def send_message(text):
    """Envia el missatge (HTML) a tots els xats configurats. Torna el nombre d'enviaments correctes."""
    token, chat_ids = _settings()
    if not token or not chat_ids:
        return 0
    sent = 0
    for chat_id in chat_ids:
        data = urllib.parse.urlencode({
            "chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": "true",
        }).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
        # Un error d'un xat no ha d'aturar la resta ni el servei: es deixa escrit al log amb el motiu de Telegram.
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
                if json.loads(resp.read().decode()).get("ok"):
                    sent += 1
        except urllib.error.HTTPError as e:
            print(f"Telegram ha rebutjat el missatge al xat {chat_id}: {e.code} {e.read().decode(errors='replace')[:300]}")
        except Exception as e:
            print(f"No s'ha pogut enviar a Telegram (xat {chat_id}): {e}")
    return sent
