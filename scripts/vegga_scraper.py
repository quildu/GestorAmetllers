"""
Extreu dades de Vegga (app.veggadigital.com) fent login automatic i capturant
les respostes JSON internes que la pagina carrega en visitar cada URL indicada.

Us:
    python scripts/vegga_scraper.py --unit 9982 --pages filters,sectors
    python scripts/vegga_scraper.py --unit 9982 --pages filters,sectors --show

Les credencials es llegeixen de .env (VEGGA_EMAIL, VEGGA_PASSWORD).
Les respostes JSON capturades es desen a data/vegga_raw/<data_hora>/ per
poder-les inspeccionar abans de decidir com guardar-les a la base de dades.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.append(BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, '.env'))

from scripts.vegga_import import import_captured

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


def scrape(unit: str, pages: list[str], show: bool = False):
    if not EMAIL or not PASSWORD:
        raise RuntimeError("Falten VEGGA_EMAIL / VEGGA_PASSWORD al fitxer .env.")

    captured = []

    def on_response(response):
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return
        try:
            body = response.json()
        except Exception:
            return
        captured.append({"url": response.url, "status": response.status, "body": body})

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
        finally:
            dump_captured()
            browser.close()


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
