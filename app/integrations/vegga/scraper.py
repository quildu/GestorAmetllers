"""
Extreu dades de Vegga (app.veggadigital.com) fent login automatic i capturant
les respostes JSON internes que la pagina carrega en visitar cada URL indicada.

Les credencials es llegeixen de .env (VEGGA_EMAIL, VEGGA_PASSWORD).
Les respostes JSON capturades es desen a data/vegga_raw/<data_hora>/ per
poder-les inspeccionar abans de decidir com guardar-les a la base de dades.
"""

import json
import os
import re
import urllib.parse
from datetime import datetime

from playwright.sync_api import sync_playwright

from ...config import get_base_dir
from .importer import import_captured

BASE_DIR = get_base_dir()

SIGN_IN_URL = "https://app.veggadigital.com/authentication/sign-in"
BASE_APP_URL = "https://app.veggadigital.com"

EMAIL = os.getenv("VEGGA_EMAIL")
PASSWORD = os.getenv("VEGGA_PASSWORD")


def sanitize(url: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", url).strip("_")[:150]


def debug_dump(page, tag):
    out_dir = os.path.join(BASE_DIR, "data", "vegga_debug")
    os.makedirs(out_dir, exist_ok=True)
    png_path = os.path.join(out_dir, f"{tag}.png")
    html_path = os.path.join(out_dir, f"{tag}.html")
    try:
        page.screenshot(path=png_path, full_page=True)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(page.content())
        print(f"Captura de depuracio desada a: {png_path}")
    except Exception as e:
        print(f"No s'ha pogut desar la captura de depuracio: {e}")


def login(page):
    page.goto(SIGN_IN_URL)
    page.wait_for_load_state("networkidle")

    email_input = page.locator('vegga-input[formcontrolname="username"] input').first
    password_input = page.locator('vegga-input[formcontrolname="password"] input').first

    try:
        email_input.wait_for(state="visible", timeout=15000)
    except Exception:
        debug_dump(page, "login_email_not_found")
        raise

    email_input.fill(EMAIL)
    password_input.fill(PASSWORD)

    submit_button = page.locator('vegga-button.gtm--sign-in-sign-in').first
    submit_button.click()

    page.wait_for_load_state("networkidle", timeout=20000)
    page.wait_for_timeout(2000)

    if "authentication/sign-in" in page.url:
        debug_dump(page, "login_still_on_signin")
        raise RuntimeError(
            "Sembla que el login no ha funcionat (seguim a la pagina de sign-in). "
            "Revisa VEGGA_EMAIL/VEGGA_PASSWORD al .env, o mira la captura de "
            "depuracio a data/vegga_debug/."
        )


HISTORY_PAGE_SIZE = 200
HISTORY_MAX_PAGES = 500


def fetch_sector_history(unit: str, date_from: str, date_to: str, show: bool = False):
    """Torna els regs per sector (agrupats per dia) entre date_from i date_to ('YYYY-MM-DD').

    L'enllac directe a /history fa petar el frontal de Vegga; cal entrar a l'equip i clicar
    la pestanya. Aprofitem la peticio que fa la pagina per reutilitzar-ne l'URL i el token.
    """
    if not EMAIL or not PASSWORD:
        raise RuntimeError("Falten VEGGA_EMAIL / VEGGA_PASSWORD al fitxer .env.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not show)
        page = browser.new_page(viewport={"width": 1400, "height": 1000})
        try:
            login(page)
            page.goto(f"{BASE_APP_URL}/irrigation-control/devices/{unit}/programs")
            page.wait_for_load_state("networkidle", timeout=30000)
            with page.expect_request(lambda r: "/history/sectors" in r.url, timeout=45000) as req_info:
                page.get_by_text("Historial", exact=True).first.click()
            request = req_info.value
            base_url = request.url.split("?")[0]

            items = []
            seen = set()
            page_number = 1
            while True:
                query = urllib.parse.urlencode({
                    "from": date_from, "to": date_to, "grouping": "DAY", "sector": 0,
                    "pageNumber": page_number, "pageSize": HISTORY_PAGE_SIZE,
                })
                resp = page.request.get(f"{base_url}?{query}", headers=request.headers)
                if not resp.ok:
                    raise RuntimeError(f"Vegga ha respost {resp.status} a l'historial de sectors.")
                body = resp.json()
                batch = body.get("items", [])
                new = [it for it in batch if (it.get("sectorNumber"), it.get("dateFrom")) not in seen]
                seen.update((it.get("sectorNumber"), it.get("dateFrom")) for it in new)
                items.extend(new)
                # Vegga pot retallar el pageSize (p.ex. a 20): no es pot parar quan la pagina ve "curta",
                # nomes quan ve buida (o repetida) o ja tenim totalElements.
                total = body.get("totalElements")
                if not new or (total is not None and len(items) >= total) or page_number >= HISTORY_MAX_PAGES:
                    return items
                page_number += 1
        except Exception:
            debug_dump(page, "history_failed")
            raise
        finally:
            browser.close()


def _has_more_pages(body):
    # Respostes paginades de l'API agronic: {"content": [...], "totalPages": N, "number": 0, "last": false, ...}
    return (isinstance(body, dict) and "content" in body and body.get("number") == 0
            and body.get("last") is False and (body.get("totalPages") or 0) > 1)


def fetch_remaining_pages(page, paginated, captured):
    """La web de Vegga nomes carrega la primera pagina (p.ex. 20 neteges de filtre): demanem la resta."""
    for url, (headers, total_pages) in paginated.items():
        parts = urllib.parse.urlsplit(url)
        params = dict(urllib.parse.parse_qsl(parts.query))
        if "page" not in params:
            print(f"Resposta paginada sense parametre 'page', no es pot completar: {url}")
            continue
        first = int(params["page"])
        for n in range(first + 1, first + min(total_pages, HISTORY_MAX_PAGES)):
            params["page"] = str(n)
            page_url = urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(params)))
            resp = page.request.get(page_url, headers=headers)
            if not resp.ok:
                print(f"[{resp.status}] no s'ha pogut descarregar {page_url}")
                break
            body = resp.json()
            captured.append({"url": page_url, "status": resp.status, "body": body})
            if not body.get("content") or body.get("last"):
                break


def scrape(unit: str, pages: list[str], show: bool = False):
    if not EMAIL or not PASSWORD:
        raise RuntimeError("Falten VEGGA_EMAIL / VEGGA_PASSWORD al fitxer .env.")

    captured = []
    paginated = {}

    def on_response(response):
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return
        try:
            body = response.json()
        except Exception:
            return
        captured.append({"url": response.url, "status": response.status, "body": body})
        if _has_more_pages(body):
            paginated[response.url] = (response.request.headers, body["totalPages"])

    def dump_captured():
        out_dir = os.path.join(BASE_DIR, "data", "vegga_raw", datetime.now().strftime("%Y%m%d_%H%M%S"))
        os.makedirs(out_dir, exist_ok=True)

        if not captured:
            print("No s'ha capturat cap resposta JSON.")
            return

        for i, item in enumerate(captured):
            fname = f"{i:03d}_{sanitize(item['url'])}.json"
            with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as f:
                json.dump(item, f, ensure_ascii=False, indent=2)

        print(f"\nCapturades {len(captured)} respostes JSON a: {out_dir}")
        for item in captured:
            print(f"  [{item['status']}] {item['url']}")

        imported = import_captured(captured, unit)
        print(f"\nDesat a la base de dades: {imported}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not show)
        context = browser.new_context()
        page = context.new_page()
        page.on("response", on_response)

        try:
            print("Iniciant sessio a Vegga...")
            login(page)
            print("Login OK.")

            for name in pages:
                url = f"{BASE_APP_URL}/irrigation-control/unit/{unit}/{name}"
                print(f"Visitant {url} ...")
                page.goto(url)
                page.wait_for_load_state("networkidle", timeout=20000)
                page.wait_for_timeout(1500)

            fetch_remaining_pages(page, paginated, captured)
        finally:
            dump_captured()
            browser.close()
