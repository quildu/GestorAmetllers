def build_date_str(day, month, year):
    """Compon una data ISO (YYYY-MM-DD) a partir dels camps separats dels formularis."""
    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
