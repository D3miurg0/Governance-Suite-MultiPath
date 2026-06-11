"""
Governance-Suite — Migración de archivos
Copia, mueve y verifica integridad de archivos entre rutas locales o UNC.
Soporta filtro por fecha de modificación (date_from, date_to, year).
Soporta múltiples pares origen→destino ejecutados en paralelo (migrate_multi_paths).
"""
import os
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Callable, Tuple
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


def _passes_date_filter(
    f: Path,
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    year: Optional[int],
) -> bool:
    """Devuelve True si el archivo cumple el filtro de fecha de modificación."""
    try:
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
    except Exception:
        return True
    if year is not None and mtime.year != year:
        return False
    if date_from is not None and mtime < date_from:
        return False
    if date_to is not None and mtime > date_to:
        return False
    return True


def copy_file(
    src: str,
    dst: str,
    verify: bool = True,
    overwrite: bool = False,
    sync_only: bool = False,
) -> Dict:
    """Copia un archivo con verificación de integridad opcional.

    sync_only=True : solo copia si origen es más nuevo o tiene distinto tamaño.
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
        if not overwrite and not sync_only:
            result["status"] = "skipped"
            result["error"] = "Destino ya existe"
            return result
        if sync_only and not _is_newer_or_different(src_path, dst_path):
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
    sync_only: bool = False,
    threads: int = DEFAULT_THREADS,
    progress_callback: Optional[Callable] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    year: Optional[int] = None,
) -> List[Dict]:
    """Migra un directorio completo con soporte multihilo.

    sync_only=True : compara fecha y tamaño antes de copiar.
    date_from      : solo archivos modificados desde esta fecha.
    date_to        : solo archivos modificados hasta esta fecha.
    year           : shortcut — solo archivos del año indicado.
    """
    src_root = Path(src_dir)
    dst_root = Path(dst_dir)

    if not src_root.exists():
        raise FileNotFoundError(f"Directorio origen no encontrado: {src_dir}")

    files = [
        f for f in src_root.rglob("*")
        if f.is_file()
        and (not extensions or f.suffix.lower() in extensions)
        and _passes_date_filter(f, date_from, date_to, year)
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
    logger.info(
        f"Migración completada: {ok} nuevos, {updated} actualizados, "
        f"{skipped} omitidos, {errors} errores"
    )
    return results


# ---------------------------------------------------------------------------
# Multi-path: migra N pares origen→destino con progreso unificado
# ---------------------------------------------------------------------------

def migrate_multi_paths(
    paths: List[Tuple[str, str]],
    extensions: Optional[List[str]] = None,
    verify: bool = True,
    overwrite: bool = False,
    sync_only: bool = False,
    threads_per_path: int = DEFAULT_THREADS,
    parallel_paths: bool = True,
    progress_callback: Optional[Callable] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    year: Optional[int] = None,
) -> Dict[str, List[Dict]]:
    """Migra múltiples pares (src_dir, dst_dir) de forma paralela o secuencial.

    Args:
        paths            : lista de tuplas (src_dir, dst_dir).
        parallel_paths   : True → cada ruta en su propio hilo de nivel superior;
                           False → rutas procesadas una tras otra.
        progress_callback: fn(path_index, src, done, total, result)
                           recibe el índice de la ruta, el origen, el avance del
                           lote actual y el resultado individual del archivo.
        threads_per_path : hilos internos por cada migrate_directory.
        Resto de parámetros: idénticos a migrate_directory.

    Returns:
        dict { src_dir: [results] } — una clave por cada ruta origen.
    """
    if not paths:
        return {}

    all_results: Dict[str, List[Dict]] = {}

    def _run_single(idx: int, src: str, dst: str) -> Tuple[str, List[Dict]]:
        """Ejecuta una migración individual y envuelve el callback con el índice."""
        def _cb(done, total, r):
            if progress_callback:
                progress_callback(idx, src, done, total, r)

        results = migrate_directory(
            src, dst,
            extensions=extensions,
            verify=verify,
            overwrite=overwrite,
            sync_only=sync_only,
            threads=threads_per_path,
            progress_callback=_cb,
            date_from=date_from,
            date_to=date_to,
            year=year,
        )
        return src, results

    if parallel_paths:
        # Cada ruta en un hilo de nivel superior (paths en paralelo)
        with ThreadPoolExecutor(max_workers=len(paths)) as executor:
            futures = [
                executor.submit(_run_single, idx, src, dst)
                for idx, (src, dst) in enumerate(paths)
            ]
            for future in as_completed(futures):
                src, results = future.result()
                all_results[src] = results
    else:
        # Rutas en secuencia
        for idx, (src, dst) in enumerate(paths):
            src_key, results = _run_single(idx, src, dst)
            all_results[src_key] = results

    # Resumen global al log
    total_files = sum(len(v) for v in all_results.values())
    ok      = sum(1 for v in all_results.values() for r in v if r["status"] == "ok")
    updated = sum(1 for v in all_results.values() for r in v if r["status"] == "updated")
    skipped = sum(1 for v in all_results.values() for r in v if r["status"] == "skipped")
    errors  = sum(1 for v in all_results.values() for r in v if r["status"] == "error")
    logger.info(
        f"Multi-path completado ({len(paths)} rutas, {total_files} archivos): "
        f"{ok} nuevos, {updated} actualizados, {skipped} omitidos, {errors} errores"
    )
    return all_results
