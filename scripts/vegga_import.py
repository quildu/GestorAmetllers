"""
Interpreta les respostes JSON capturades de Vegga (per vegga_scraper.py) i les
desa a la base de dades local, perque l'app les pugui mostrar sense haver
d'anar a buscar-les cada cop a Vegga.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.database import get_connection


def _bool_to_int(v):
    return 1 if v else 0


def import_status(conn, unit_id, body):
    ram = body.get("ram") or {}
    conn.execute("""
        INSERT INTO vegga_status (
            unit_id, device_date, connected, alarm, out_service,
            system_stop_malfunction, conditional_stop_malfunction, general_malfunction,
            flow_malfunction, counter_malfunction, fertilizer_malfunction, filter_malfunction,
            ph_malfunction, ce_malfunction, definitive_stop_malfunction,
            tension_vcc, battery_load, last_reception
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        unit_id, ram.get("date"), _bool_to_int(body.get("connected")),
        _bool_to_int(ram.get("alarm")), _bool_to_int(ram.get("outService")),
        _bool_to_int(ram.get("systemStopMalfunction")), _bool_to_int(ram.get("conditionalStopMalfunction")),
        _bool_to_int(ram.get("generalMalfunction")), _bool_to_int(ram.get("flowMalfunction")),
        _bool_to_int(ram.get("counterMalfunction")), _bool_to_int(ram.get("ferlitzerMalfunction")),
        _bool_to_int(ram.get("filterMalfunction")), _bool_to_int(ram.get("phMalfunction")),
        _bool_to_int(ram.get("ceMalfunction")), _bool_to_int(ram.get("definitiveStopMalfunction")),
        ram.get("tensionVcc"), _bool_to_int(ram.get("bateryLoad")), ram.get("lastReception"),
    ))


def import_meters(conn, unit_id, body):
    for m in body:
        meter_id = m["pk"]["id"]
        conn.execute("""
            INSERT INTO vegga_water_meters (unit_id, meter_id, total_volume, x_flow, leak_flow)
            VALUES (?, ?, ?, ?, ?)
        """, (unit_id, meter_id, m.get("totalVolume"), m.get("xFlow"), m.get("leakFlow")))


def import_filter_events(conn, unit_id, body):
    for ev in body.get("content", []):
        vegga_id = ev["pk"]["id"]
        conn.execute("""
            INSERT OR IGNORE INTO vegga_filter_events (unit_id, vegga_id, event_date, number, duration_value)
            VALUES (?, ?, ?, ?, ?)
        """, (unit_id, vegga_id, ev.get("date"), ev.get("number"), ev.get("value4")))


def import_sectors(conn, unit_id, body):
    for s in body:
        sector_id = s["pk"]["id"]
        conn.execute("""
            INSERT INTO vegga_sectors (unit_id, sector_id, name, output, sector_op, program_list, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(unit_id, sector_id) DO UPDATE SET
                name=excluded.name, output=excluded.output, sector_op=excluded.sector_op,
                program_list=excluded.program_list, updated_at=CURRENT_TIMESTAMP
        """, (unit_id, sector_id, s.get("name"), s.get("output"), _bool_to_int(s.get("sectorOp")),
              ",".join(str(p) for p in s.get("programList", []))))


def import_programs(conn, unit_id, body):
    for p in body:
        program_id = p["pk"]["id"]
        conn.execute("""
            INSERT INTO vegga_programs (
                unit_id, program_id, name, sector1, start_minutes, duration_seconds, fertilizer1,
                monday, tuesday, wednesday, thursday, friday, saturday, sunday, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(unit_id, program_id) DO UPDATE SET
                name=excluded.name, sector1=excluded.sector1, start_minutes=excluded.start_minutes,
                duration_seconds=excluded.duration_seconds, fertilizer1=excluded.fertilizer1,
                monday=excluded.monday, tuesday=excluded.tuesday, wednesday=excluded.wednesday,
                thursday=excluded.thursday, friday=excluded.friday, saturday=excluded.saturday,
                sunday=excluded.sunday, updated_at=CURRENT_TIMESTAMP
        """, (
            unit_id, program_id, p.get("name"), p.get("sector1"), p.get("start"), p.get("value"),
            p.get("fertilizer1"), _bool_to_int(p.get("monday")), _bool_to_int(p.get("tuesday")),
            _bool_to_int(p.get("wednesday")), _bool_to_int(p.get("thursday")), _bool_to_int(p.get("friday")),
            _bool_to_int(p.get("saturday")), _bool_to_int(p.get("sunday")),
        ))


def import_analogs(conn, unit_id, body):
    for a in body:
        sensor_id = a["pk"]["id"]
        conn.execute("""
            INSERT INTO vegga_analog_sensors (unit_id, sensor_id, name, x_value, min_graphics, max_graphics)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (unit_id, sensor_id, a.get("name"), a.get("xValue"), a.get("minGraphics"), a.get("maxGraphics")))


def import_digitals(conn, unit_id, body):
    for d in body:
        sensor_id = d["pk"]["id"]
        conn.execute("""
            INSERT INTO vegga_digital_sensors (unit_id, sensor_id, name, x_state)
            VALUES (?, ?, ?, ?)
        """, (unit_id, sensor_id, d.get("name"), d.get("xState")))


def import_captured(captured, unit_id):
    """captured: llista de {"url", "status", "body"} tal com les recull vegga_scraper.py"""
    conn = get_connection()
    imported = {"status": 0, "meters": 0, "filters": 0, "sectors": 0, "programs": 0, "analogs": 0, "digitals": 0}

    for item in captured:
        url = item["url"]
        body = item["body"]

        if f"/units/{unit_id}?add=format" in url:
            import_status(conn, unit_id, body)
            imported["status"] += 1
        elif f"/devices/A2500/{unit_id}/sectors" in url:
            import_sectors(conn, unit_id, body)
            imported["sectors"] += 1
        elif f"/devices/A2500/{unit_id}/programs" in url:
            import_programs(conn, unit_id, body)
            imported["programs"] += 1
        elif f"/units/{unit_id}/meters" in url:
            import_meters(conn, unit_id, body)
            imported["meters"] += 1
        elif f"/units/{unit_id}/filters/register" in url:
            import_filter_events(conn, unit_id, body)
            imported["filters"] += 1
        elif f"/units/{unit_id}/analogs" in url:
            import_analogs(conn, unit_id, body)
            imported["analogs"] += 1
        elif f"/units/{unit_id}/digitals" in url:
            import_digitals(conn, unit_id, body)
            imported["digitals"] += 1

    conn.commit()
    return imported
