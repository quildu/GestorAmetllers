import os
import sys


def resource_path(relative_path):
    """Localitza recursos (templates/static/db schema) tant en desenvolupament
    com empaquetats amb PyInstaller (on viuen sota sys._MEIPASS)."""
    if getattr(sys, "frozen", False):
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), relative_path)
