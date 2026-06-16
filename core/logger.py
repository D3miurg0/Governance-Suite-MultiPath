"""
Governance-Suite — Logger de sesiones
Crea un archivo de log por sesión en logs/
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from config import LOGS_DIR, LOG_LEVEL


_shared_file_handler = None


def get_logger(name: str = "governance") -> logging.Logger:
    """Devuelve un logger configurado con archivo + consola."""
    global _shared_file_handler
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # Handler de archivo (compartido)
    if _shared_file_handler is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = LOGS_DIR / f"session_{timestamp}.log"
        _shared_file_handler = logging.FileHandler(log_file, encoding="utf-8")
        _shared_file_handler.setLevel(logging.DEBUG)
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        _shared_file_handler.setFormatter(fmt)

    # Handler de consola (sólo WARNING+)
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.WARNING)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    ch.setFormatter(fmt)

    logger.addHandler(_shared_file_handler)
    logger.addHandler(ch)
    return logger
