import os
import sys
import datetime
from pathlib import Path

try:
    import ntsecuritycon as con
    import win32security
    import pywintypes
    WIN32_ENABLED = True
except ImportError:
    WIN32_ENABLED = False

# Detecta si corre como .exe compilado (PyInstaller) o como script normal
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))


class Config:
    APP_NAME        = 'Governance Suite'
    APP_NAME_FULL   = 'Governance Suite — File Governance Platform'
    VERSION         = '2.2.0'
    GUI_THEME       = 'clam'
    GUI_WINDOW_SIZE = '1280x780'
    GUI_MIN_SIZE    = (900, 600)
    MAX_WORKERS     = 8
    BASE_DIR        = BASE_DIR
    OUTPUT_DIR      = BASE_DIR / 'output'
    LOGS_DIR        = BASE_DIR / 'logs'
    ICON_PATH       = BASE_DIR / 'assets' / 'icon.ico'
    LOG_LEVEL       = 'INFO'
    TIMESTAMP       = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    MIN_YEAR_VALID  = 1990
    MAX_YEAR_VALID  = datetime.datetime.now().year + 1
    PERMISSIONS_MAP = {}
    INHERITED_ACE   = 0x10

if WIN32_ENABLED:
    Config.PERMISSIONS_MAP = {
        con.FILE_GENERIC_READ: "Read",
        con.FILE_GENERIC_READ | con.FILE_GENERIC_EXECUTE: "Read & Execute",
        con.FILE_GENERIC_WRITE: "Write",
        (con.FILE_GENERIC_READ | con.FILE_GENERIC_WRITE | con.FILE_GENERIC_EXECUTE | con.DELETE): "Modify",
        con.FILE_ALL_ACCESS: "Full Control",
    }


# Aliases de acceso directo
APP_NAME        = Config.APP_NAME
APP_NAME_FULL   = Config.APP_NAME_FULL
VERSION         = Config.VERSION
GUI_THEME       = Config.GUI_THEME
GUI_WINDOW_SIZE = Config.GUI_WINDOW_SIZE
GUI_MIN_SIZE    = Config.GUI_MIN_SIZE
ICON_PATH       = Config.ICON_PATH
LOGS_DIR        = Config.LOGS_DIR
LOG_LEVEL       = Config.LOG_LEVEL
OUTPUT_DIR      = Config.OUTPUT_DIR
BASE_DIR        = Config.BASE_DIR
MAX_WORKERS     = Config.MAX_WORKERS
PERMISSIONS_MAP = Config.PERMISSIONS_MAP
INHERITED_ACE   = Config.INHERITED_ACE
TIMESTAMP       = Config.TIMESTAMP
MIN_YEAR_VALID  = Config.MIN_YEAR_VALID
MAX_YEAR_VALID  = Config.MAX_YEAR_VALID
DEFAULT_THREADS = 8
DEFAULT_TIMEOUT = 5
WIN32_ENABLED   = WIN32_ENABLED

# --- Auto-crear directorios esenciales al arrancar ---
for _dir in (Config.LOGS_DIR, Config.OUTPUT_DIR):
    _dir.mkdir(parents=True, exist_ok=True)
