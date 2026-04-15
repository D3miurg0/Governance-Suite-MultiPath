import os
import datetime
from pathlib import Path

try:
    import ntsecuritycon as con
    import win32security
    import pywintypes
    WIN32_ENABLED = True
except ImportError:
    WIN32_ENABLED = False


class Config:
    """Constantes y configuración global de Governance-Suite."""

    # ── Identidad ────────────────────────────────────────────────────────────
    APP_NAME: str = "Governance-Suite"
    VERSION:  str = "2.0.0"

    # ── Rendimiento ──────────────────────────────────────────────────────────
    MAX_WORKERS: int = 16

    # ── Rutas ────────────────────────────────────────────────────────────────
    try:
        BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        BASE_DIR: str = os.getcwd()

    OUTPUT_DIR: str = os.path.join(BASE_DIR, "output")
    LOGS_DIR: Path = Path(BASE_DIR) / "logs"

    # ── Logging ──────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    # ── Tiempo ───────────────────────────────────────────────────────────────
    TIMESTAMP:      str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    MIN_YEAR_VALID: int = 1990
    MAX_YEAR_VALID: int = datetime.datetime.now().year + 1

    # ── GUI ──────────────────────────────────────────────────────────────────
    GUI_THEME:       str   = "dark"
    GUI_WINDOW_SIZE: str   = "1280x780"
    GUI_MIN_SIZE:    tuple = (900, 600)

    # ── Permisos NTFS ────────────────────────────────────────────────────────
    PERMISSIONS_MAP: dict = (
        {
            con.FILE_ALL_ACCESS: "Full Control",
            (con.FILE_GENERIC_READ | con.FILE_GENERIC_EXECUTE | con.DELETE | con.FILE_GENERIC_WRITE): "Modify",
            (con.FILE_GENERIC_READ | con.FILE_GENERIC_EXECUTE): "Read & Execute",
            con.FILE_GENERIC_READ: "Read",
            con.FILE_GENERIC_WRITE: "Write",
        }
        if WIN32_ENABLED
        else {}
    )
    INHERITED_ACE: int = 0x10


# ── Aliases módulo-nivel ──────────────────────────────────────────────────────
# Requeridos por importaciones directas: from config import APP_NAME, ...
APP_NAME        = Config.APP_NAME
VERSION         = Config.VERSION
GUI_THEME       = Config.GUI_THEME
GUI_WINDOW_SIZE = Config.GUI_WINDOW_SIZE
GUI_MIN_SIZE    = Config.GUI_MIN_SIZE
LOGS_DIR        = Config.LOGS_DIR
LOG_LEVEL       = Config.LOG_LEVEL
OUTPUT_DIR      = Config.OUTPUT_DIR
BASE_DIR        = Config.BASE_DIR
WIN32_ENABLED   = WIN32_ENABLED
