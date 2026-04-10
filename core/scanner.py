"""
Governance-Suite — Scanner de servidores remotos
Escanea rutas UNC / rutas locales para obtener estructura de directorios y archivos.
"""
import os
import socket
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Generator, List, Dict, Optional
from core.logger import get_logger
from config import DEFAULT_THREADS, DEFAULT_TIMEOUT

logger = get_logger("scanner")


def ping_host(host: str, timeout: int = DEFAULT_TIMEOUT) -> bool:
    """Verifica conectividad básica al host."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.gethostbyname(host)
        return True
    except socket.error:
        return False


def scan_directory(
    path: str,
    recursive: bool = True,
    extensions: Optional[List[str]] = None,
    exclude_hidden: bool = True,
) -> Generator[Dict, None, None]:
    """
    Escanea un directorio y genera un dict por cada elemento encontrado.
    Campos: path, name, size, modified, is_dir, extension
    """
    root = Path(path)
    if not root.exists():
        logger.error(f"Ruta no encontrada: {path}")
        raise FileNotFoundError(f"Ruta no encontrada: {path}")

    iterator = root.rglob("*") if recursive else root.iterdir()

    for item in iterator:
        try:
            if exclude_hidden and item.name.startswith("."):
                continue
            stat = item.stat()
            ext = item.suffix.lower() if not item.is_dir() else ""
            if extensions and ext not in extensions:
                continue
            yield {
                "path": str(item),
                "name": item.name,
                "size": stat.st_size if not item.is_dir() else 0,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "is_dir": item.is_dir(),
                "extension": ext,
            }
        except (PermissionError, OSError) as e:
            logger.warning(f"Sin acceso: {item} — {e}")
            continue


def scan_multiple(
    paths: List[str],
    recursive: bool = True,
    extensions: Optional[List[str]] = None,
    threads: int = DEFAULT_THREADS,
) -> Dict[str, List[Dict]]:
    """Escanea múltiples rutas en paralelo."""
    results = {}

    def _scan(p):
        return p, list(scan_directory(p, recursive, extensions))

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(_scan, p): p for p in paths}
        for future in as_completed(futures):
            path, data = future.result()
            results[path] = data
            logger.info(f"Escaneo completo: {path} — {len(data)} elementos")

    return results
