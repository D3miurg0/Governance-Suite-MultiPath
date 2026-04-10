"""
Governance-Suite — Configuración centralizada
"""
import os
from pathlib import Path

# Directorios base
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"
LOCALES_DIR = BASE_DIR / "locales"

# Crear directorios si no existen
OUTPUT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Idioma por defecto
DEFAULT_LANG = os.environ.get("GSUITE_LANG", "es")

# Versión
VERSION = "1.0.0"
APP_NAME = "Governance-Suite"

# GUI
GUI_THEME = "clam"           # Opciones: clam, alt, default, classic
GUI_WINDOW_SIZE = "1200x750"
GUI_MIN_SIZE = (900, 600)

# CLI
CLI_PAGE_SIZE = 25           # Filas por página en tablas CLI
CLI_COLOR = True             # Habilitar colores ANSI en CLI

# Exportación
DEFAULT_EXPORT_FORMAT = "csv"   # csv | excel | json
EXCEL_MAX_ROWS = 100_000

# Logging
LOG_LEVEL = os.environ.get("GSUITE_LOG_LEVEL", "INFO")
LOG_ROTATION = "7 days"

# Red / Servidores
DEFAULT_TIMEOUT = 30        # segundos
DEFAULT_THREADS = 4         # hilos para escaneo paralelo
SMB_PORT = 445
