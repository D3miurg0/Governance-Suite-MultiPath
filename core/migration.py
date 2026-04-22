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


def _is_newer_or_different(src: Path, dst: Path) -> bool:
    """Devuelve True si src es más nuevo o tiene distinto tamaño que dst."""
    try:
        s = src.stat()
        d = dst.stat()
        return s.st_size != d.st_size or s.st_mtime > d.st_mtime
    except Exception:
        return True


def copy_file(
    src: str,
    dst: str,
    verify: bool = True,
    overwrite: bool = False,
    sync_mode: bool = False,
) -> Dict:
    """Copia un archivo con verificación de integridad opcional.

    sync_mode=True: solo copia si origen es más nuevo o tiene distinto tamaño.
    overwrite=True : sobreescribe sin comparar fecha/tamaño.
    """
    src_path, dst_path = Path(src), Path(dst)
    result = {"src": src, "dst": dst, "status": "pending", "error": None}

    if not src_path.exists():
        result["status"] = "error"
        result["error"] = "Archivo origen no encontrado"
        return result

    dst_existed = dst_path.exists()

    if dst_existed:
        if not overwrite and not sync_mode:
            result["status"] = "skipped"
            result["error"] = "Destino ya existe"
            return result
        if sync_mode and not _is_newer_or_different(src_path, dst_path):
            result["status"] = "skipped"
            result["error"] = "Origen igual al destino (fecha/tamaño)"
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
        # fix: usar dst_existed (capturado antes de copiar) para distinguir ok vs updated
        result["status"] = "updated" if dst_existed else "ok"
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
    sync_only: bool = False,   # fix: renombrado de sync_mode a sync_only para coincidir con GUI
    threads: int = DEFAULT_THREADS,
    progress_callback: Optional[Callable] = None,
) -> List[Dict]:
    """Migra un directorio completo con soporte multihilo.

    sync_only=True: compara fecha y tamaño antes de copiar.
    """
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

    def _copy(f):
        rel = f.relative_to(src_root)
        dst = dst_root / rel
        return copy_file(str(f), str(dst), verify, overwrite, sync_only)

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(_copy, f): f for f in files}
        completed = 0
        for future in as_completed(futures):
            r = future.result()
            results.append(r)
            completed += 1
            if progress_callback:
                progress_callback(completed, total, r)

    ok      = sum(1 for r in results if r["status"] == "ok")
    updated = sum(1 for r in results if r["status"] == "updated")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    errors  = sum(1 for r in results if r["status"] == "error")
    logger.info(f"Migración completada: {ok} nuevos, {updated} actualizados, {skipped} omitidos, {errors} errores")
    return results
