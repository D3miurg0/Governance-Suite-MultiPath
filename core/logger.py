"""
Governance-Suite — Logger de sesiones
Crea un archivo de log por sesión en logs/
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from config import LOGS_DIR, LOG_LEVEL


def get_logger(name: str = "governance") -> logging.Logger:
    """Devuelve un logger configurado con archivo + consola."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # Handler de archivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"session_{timestamp}.log"
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    fh.setFormatter(fmt)

    # Handler de consola (sólo WARNING+)
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.WARNING)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger
