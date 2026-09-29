"""Client de les dades obertes de la XEMA (Meteocat) al portal analisi.transparenciacatalunya.cat."""

import json
import re
import urllib.parse
import urllib.request

BASE_URL = "https://analisi.transparenciacatalunya.cat/resource"
DAILY_DATASET = "7bvh-jvq2"
STATIONS_DATASET = "yqwd-vj5e"

VAR_ETO = "1700"
VAR_RAIN = "1300"

STATION_CODE_RE = re.compile(r"^[A-Z0-9]{2,3}$")
TIMEOUT_SECONDS = 20


def _get_json(dataset, params):
    url = f"{BASE_URL}/{dataset}.json?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode("utf-8"))


def is_valid_station_code(code):
    return bool(code and STATION_CODE_RE.match(code))


def fetch_daily(station_code, since_date):
    """Torna {data 'YYYY-MM-DD': {'eto': float|None, 'rain': float|None}} des de since_date."""
    if not is_valid_station_code(station_code):
        raise ValueError(f"Codi d'estació no vàlid: {station_code!r}")
    rows = _get_json(DAILY_DATASET, {
        "$where": (
            f"codi_estacio='{station_code}' AND codi_variable in('{VAR_ETO}','{VAR_RAIN}') "
            f"AND data_lectura >= '{since_date}T00:00:00'"
        ),
        "$limit": 5000,
    })
    result = {}
    for row in rows:
        day = row["data_lectura"][:10]
        key = "eto" if row["codi_variable"] == VAR_ETO else "rain"
        try:
            value = float(row["valor"])
        except (KeyError, ValueError):
            continue
        result.setdefault(day, {"eto": None, "rain": None})[key] = value
    return result


def fetch_stations():
    rows = _get_json(STATIONS_DATASET, {
        "nom_estat_ema": "Operativa",
        "$select": "codi_estacio,nom_estacio,nom_comarca",
        "$order": "nom_comarca,nom_estacio",
        "$limit": 1000,
    })
    return [
        {"code": r["codi_estacio"], "name": r.get("nom_estacio", ""), "comarca": r.get("nom_comarca", "")}
        for r in rows if is_valid_station_code(r.get("codi_estacio"))
    ]
