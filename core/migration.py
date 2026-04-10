"""
Governance-Suite — Migración de archivos
Copia, mueve y verifica integridad de archivos entre rutas locales o UNC.
"""
import os
import shutil
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.logger import get_logger
from config import DEFAULT_THREADS

logger = get_logger("migration")


def compute_checksum(path: str, algorithm: str = "md5") -> str:
    """Calcula checksum de un archivo."""
    h = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_file(
    src: str,
    dst: str,
    verify: bool = True,
    overwrite: bool = False,
) -> Dict:
    """Copia un archivo con verificación de integridad opcional."""
    src_path, dst_path = Path(src), Path(dst)
    result = {"src": src, "dst": dst, "status": "pending", "error": None}

    if not src_path.exists():
        result["status"] = "error"
        result["error"] = "Archivo origen no encontrado"
        return result

    if dst_path.exists() and not overwrite:
        result["status"] = "skipped"
        result["error"] = "Destino ya existe"
        return result

    try:
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if verify:
            src_hash = compute_checksum(src)
            dst_hash = compute_checksum(dst)
            if src_hash != dst_hash:
                result["status"] = "error"
                result["error"] = f"Checksum mismatch: {src_hash} vs {dst_hash}"
                return result
            result["checksum"] = src_hash
        result["status"] = "ok"
        logger.info(f"Copiado: {src} → {dst}")
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        logger.error(f"Error copiando {src}: {e}")

    return result


def migrate_directory(
    src_dir: str,
    dst_dir: str,
    extensions: Optional[List[str]] = None,
    verify: bool = True,
    overwrite: bool = False,
    threads: int = DEFAULT_THREADS,
    progress_callback: Optional[Callable] = None,
) -> List[Dict]:
    """Migra un directorio completo con soporte multihilo."""
    src_root = Path(src_dir)
    dst_root = Path(dst_dir)
    files = [
        f for f in src_root.rglob("*")
        if f.is_file() and (
            not extensions or f.suffix.lower() in extensions
        )
    ]
    total = len(files)
    results = []
    completed = 0

    def _copy(f):
        rel = f.relative_to(src_root)
        dst = dst_root / rel
        return copy_file(str(f), str(dst), verify, overwrite)

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(_copy, f): f for f in files}
        for future in as_completed(futures):
            r = future.result()
            results.append(r)
            completed += 1
            if progress_callback:
                progress_callback(completed, total, r)

    ok = sum(1 for r in results if r["status"] == "ok")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    errors = sum(1 for r in results if r["status"] == "error")
    logger.info(f"Migración completada: {ok} OK, {skipped} omitidos, {errors} errores")
    return results
