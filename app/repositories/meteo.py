def latest_date(conn, station_code, source='xema'):
    row = conn.execute(
        "SELECT MAX(date) AS d FROM meteo_daily WHERE station_code = ? AND source = ?",
        (station_code, source)
    ).fetchone()
    return row['d'] if row else None


def upsert_xema(conn, station_code, daily):
    # No sobreescrivim les dades que l'usuari ha entrat a ma.
    conn.executemany("""
        INSERT INTO meteo_daily (station_code, date, eto, rain, source)
        VALUES (?, ?, ?, ?, 'xema')
        ON CONFLICT(station_code, date) DO UPDATE SET
            eto = excluded.eto, rain = excluded.rain, imported_at = CURRENT_TIMESTAMP
        WHERE meteo_daily.source = 'xema'
    """, [(station_code, day, v['eto'], v['rain']) for day, v in daily.items()])
    conn.commit()


def upsert_manual(conn, station_code, date, eto, rain):
    conn.execute("""
        INSERT INTO meteo_daily (station_code, date, eto, rain, source)
        VALUES (?, ?, ?, ?, 'manual')
        ON CONFLICT(station_code, date) DO UPDATE SET
            eto = excluded.eto, rain = excluded.rain, source = 'manual', imported_at = CURRENT_TIMESTAMP
    """, (station_code, date, eto, rain))
    conn.commit()


def list_range(conn, station_code, since_date):
    return conn.execute("""
        SELECT * FROM meteo_daily
        WHERE station_code = ? AND date >= ? AND eto IS NOT NULL
        ORDER BY date DESC
    """, (station_code, since_date)).fetchall()
