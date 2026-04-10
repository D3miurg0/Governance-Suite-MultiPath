import os
import datetime

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

    # ── Tiempo ───────────────────────────────────────────────────────────────
    TIMESTAMP:      str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    MIN_YEAR_VALID: int = 1990
    MAX_YEAR_VALID: int = datetime.datetime.now().year + 1

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
