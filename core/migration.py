"""
Governance-Suite — Migración de archivos
─────────────────────────────────────────────────────────────────────────────
Copia, mueve y verifica integridad de archivos entre rutas locales o UNC.
Soporta filtro por fecha de modificación (date_from, date_to, year).
Soporta múltiples pares origen→destino ejecutados en paralelo.

Modo Robocopy (issue #3):
  Para volúmenes grandes (> 1 TB) se recomienda usar use_robocopy=True.
  Invoca robocopy.exe con /COPYALL /E /MT:{threads} /R:3 /W:10 /LOG+
  y parsea el resumen final para construir el resultado estándar.
  El progreso en tiempo real se reporta leyendo el pipe stdout línea a línea
  en un hilo daemon.
─────────────────────────────────────────────────────────────────────────────
"""
import os
import re
import json
import shutil
import hashlib
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.logger import get_logger
from config import DEFAULT_THREADS

logger = get_logger("migration")


# ── Utilidades ─────────────────────────────────────────────────────────────

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


# ── Códigos de retorno de Robocopy ──────────────────────────────────────────
#
# Robocopy usa códigos de bits, NO código de salida tradicional 0/1.
#   0 = sin archivos (nada que copiar)       → éxito
#   1 = archivos copiados                    → éxito
#   2 = archivos extras en destino            → éxito
#   3 = 1+2                                  → éxito
#   4 = archivos desajustados (Mismatch)      → éxito (con advertencia)
#   5..7 = combinaciones anteriores           → éxito
#   8+ = al menos un fallo                   → error
#
_ROBOCOPY_SUCCESS_CODES = {0, 1, 2, 3, 4, 5, 6, 7}

# Regex para parsear las líneas del resumen de Robocopy
# Ejemplo: "           Files :     123456   123000       456         0         0         0"
_RC_SUMMARY_RE = re.compile(
    r"^\s+(Files|Dirs|Bytes)\s*:\s*(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)",
    re.IGNORECASE
)


# ── Robocopy ───────────────────────────────────────────────────────────────

def robocopy_directory(
    src_dir: str,
    dst_dir: str,
    threads: int = 8,
    verify: bool = False,
    overwrite: bool = True,
    sync_only: bool = False,
    log_dir: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    year: Optional[int] = None,
    progress_callback: Optional[Callable] = None,
    extra_flags: Optional[List[str]] = None,
) -> Dict:
    """
    Migra un directorio usando robocopy.exe (Windows).

    Retorna dict con claves:
        status          : 'ok' | 'error'
        returncode      : código de salida de robocopy (ver _ROBOCOPY_SUCCESS_CODES)
        files_copied    : archivos copiados
        files_skipped   : archivos omitidos
        files_failed    : archivos con error
        dirs_copied     : directorios copiados
        bytes_copied    : bytes copiados (int)
        log_file        : ruta al log generado (o None)
        lines           : lista de líneas relevantes capturadas del stdout
        error_msg       : mensaje de error si status=='error'

    Parámetros clave:
        threads     : número de hilos Robocopy (/MT:N, max 128)
        verify      : si True, usa /CHECKSUM en lugar de /FFT para comparar
        overwrite   : si False, añade /XO (excluir archivos más viejos)
        sync_only   : si True, añade /XO para solo copiar actualizados
        log_dir     : carpeta donde guardar el log de Robocopy (.log)
        date_from   : /MAXAGE no soportado por fecha exacta — se traslada a
                      /MINAGE en días calculados desde hoy
        date_to     : /MAXAGE en días calculados desde hoy
        extra_flags : lista de flags adicionales que se pasan al final
    """
    src_path = Path(src_dir)
    if not src_path.exists():
        return {
            "status": "error",
            "error_msg": f"Directorio origen no encontrado: {src_dir}",
            "returncode": -1,
            "files_copied": 0, "files_skipped": 0, "files_failed": 0,
            "dirs_copied": 0, "bytes_copied": 0,
            "log_file": None, "lines": [],
        }

    Path(dst_dir).mkdir(parents=True, exist_ok=True)

    # ── Construir comando ────────────────────────────────────────────────
    mt = max(1, min(int(threads), 128))
    cmd = [
        "robocopy",
        str(src_dir),
        str(dst_dir),
        "/COPYALL",   # Copia todos los atributos: Data, Attributes, Timestamps, Security, Owner, aUditing
        "/E",         # Incluye subdirectorios vacíos
        f"/MT:{mt}",  # Multihilo
        "/R:3",       # 3 reintentos por archivo fallido
        "/W:10",      # 10 segundos entre reintentos
        "/NP",        # Sin barra de porcentaje en stdout (para parseo limpio)
        "/UNICODE",   # Nombres de archivo Unicode
        "/TEE",       # Log a archivo Y a stdout simultáneamente
    ]

    # Verificación por checksum
    if verify:
        cmd.append("/CHECKSUM")
    else:
        cmd.append("/FFT")   # FAT File Times — tolerancia de 2 s para timestamps NTFS

    # Modo sync: solo archivos más nuevos
    if sync_only or not overwrite:
        cmd.append("/XO")    # eXclude Older — omite archivos más viejos en origen

    # Filtro por fecha: Robocopy acepta /MINAGE y /MAXAGE en días o como fecha YYYYMMDD
    today = datetime.now()
    if date_from is not None:
        cmd.append(f"/MINAGE:{date_from.strftime('%Y%m%d')}")
    if date_to is not None:
        cmd.append(f"/MAXAGE:{date_to.strftime('%Y%m%d')}")
    if year is not None and date_from is None and date_to is None:
        # Aproximación: solo archivos del año indicado
        cmd.append(f"/MINAGE:{year}0101")
        cmd.append(f"/MAXAGE:{year}1231")

    # Log en archivo
    log_file: Optional[str] = None
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_src = Path(src_dir).name.replace("\\", "_").replace("/", "_")[:40]
        log_file = os.path.join(log_dir, f"robocopy_{safe_src}_{ts}.log")
        cmd += ["/LOG+:" + log_file]

    # Flags extra (pueden venir de la GUI: /MIR, /MOVE, etc.)
    if extra_flags:
        cmd.extend(extra_flags)

    logger.info(f"Robocopy CMD: {' '.join(cmd)}")

    # ── Ejecutar y leer stdout en tiempo real ──────────────────────────────
    captured_lines: List[str] = []
    files_copied = files_skipped = files_failed = 0
    dirs_copied  = 0
    bytes_copied = 0

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except FileNotFoundError:
        return {
            "status": "error",
            "error_msg": "robocopy.exe no encontrado. Solo disponible en Windows.",
            "returncode": -1,
            "files_copied": 0, "files_skipped": 0, "files_failed": 0,
            "dirs_copied": 0, "bytes_copied": 0,
            "log_file": log_file, "lines": [],
        }

    line_count = [0]  # contador mutable para el closure del callback

    def _read_stdout():
        """Lee stdout de robocopy línea a línea y dispara el callback."""
        for raw in proc.stdout:
            line = raw.rstrip()
            if not line:
                continue
            captured_lines.append(line)
            line_count[0] += 1
            # Llamar al callback con número de líneas procesadas como proxy de progreso
            if progress_callback:
                # done=líneas leídas, total=-1 indica progreso indeterminado
                # El caller puede usar esto para actualizar un log/status en la GUI
                progress_callback(line_count[0], -1, {"line": line, "status": "running"})

    reader = threading.Thread(target=_read_stdout, daemon=True)
    reader.start()
    proc.wait()
    reader.join(timeout=5)

    returncode = proc.returncode

    # ── Parsear resumen del output ──────────────────────────────────────────
    #
    # El resumen de Robocopy tiene este formato (columnas fijas):
    #   Total  Copied  Skipped  Mismatch  Failed  Extras
    #
    for line in captured_lines:
        m = _RC_SUMMARY_RE.match(line)
        if not m:
            continue
        kind = m.group(1).lower()
        try:
            # group(3) = Copied, group(4) = Skipped, group(6) = Failed
            copied  = int(m.group(3).replace(",", "").replace(".", ""))
            skipped = int(m.group(4).replace(",", "").replace(".", ""))
            failed  = int(m.group(6).replace(",", "").replace(".", ""))
            if kind == "files":
                files_copied  = copied
                files_skipped = skipped
                files_failed  = failed
            elif kind == "dirs":
                dirs_copied = copied
            elif kind == "bytes":
                bytes_copied = copied
        except (ValueError, IndexError):
            pass

    success = returncode in _ROBOCOPY_SUCCESS_CODES
    status  = "ok" if success else "error"
    error_msg = None if success else (
        f"Robocopy terminó con código {returncode} — revisa el log para detalles."
    )

    if success:
        logger.info(
            f"Robocopy [{src_dir}→{dst_dir}]: "
            f"{files_copied} copiados, {files_skipped} omitidos, "
            f"{files_failed} fallidos, {bytes_copied} bytes, rc={returncode}"
        )
    else:
        logger.error(
            f"Robocopy ERROR [{src_dir}→{dst_dir}]: rc={returncode} — "
            f"{files_failed} archivos fallidos"
        )

    return {
        "status":        status,
        "returncode":    returncode,
        "files_copied":  files_copied,
        "files_skipped": files_skipped,
        "files_failed":  files_failed,
        "dirs_copied":   dirs_copied,
        "bytes_copied":  bytes_copied,
        "log_file":      log_file,
        "lines":         captured_lines[-200:],   # últimas 200 líneas para no saturar memoria
        "error_msg":     error_msg,
    }


# ── copy_file (modo Python) ────────────────────────────────────────────────────

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


# ── migrate_directory ──────────────────────────────────────────────────────────

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
    use_robocopy: bool = False,
    robocopy_threads: int = 8,
    robocopy_log_dir: Optional[str] = None,
    robocopy_extra_flags: Optional[List[str]] = None,
) -> List[Dict]:
    """
    Migra un directorio completo con soporte multihilo (Python) o Robocopy.

    Cuando use_robocopy=True:
      - Ignora el parámetro 'extensions' (Robocopy no filtra extensiones de
        forma nativa sin /XF; para eso usar extra_flags=['/XF *.tmp *.bak'])
      - Retorna una lista de un solo elemento dict con el resumen de Robocopy
        (compatible con el formato esperado por migrate_multi_paths)
      - El progress_callback recibe: (done, total=-1, {'line':..., 'status':'running'})
        donde done es el número de líneas de stdout procesadas (progreso aproximado)

    Cuando use_robocopy=False:
      - Comportamiento original: copia archivo por archivo con shutil.copy2
      - Soporta filtrado por extensión y verificación MD5
      - El progress_callback recibe: (done, total, result_dict)
    """
    if use_robocopy:
        result = robocopy_directory(
            src_dir=src_dir,
            dst_dir=dst_dir,
            threads=robocopy_threads,
            verify=verify,
            overwrite=overwrite,
            sync_only=sync_only,
            log_dir=robocopy_log_dir,
            date_from=date_from,
            date_to=date_to,
            year=year,
            progress_callback=progress_callback,
            extra_flags=robocopy_extra_flags,
        )
        # Adaptar al formato de lista para compatibilidad con el resto del código
        return [{
            "src":       src_dir,
            "dst":       dst_dir,
            "status":    result["status"],
            "error":     result.get("error_msg"),
            "files_copied":  result["files_copied"],
            "files_skipped": result["files_skipped"],
            "files_failed":  result["files_failed"],
            "bytes_copied":  result["bytes_copied"],
            "log_file":      result["log_file"],
            "robocopy_rc":   result["returncode"],
            "mode":          "robocopy",
        }]

    # ── Modo Python (comportamiento original) ─────────────────────────────
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


# ── migrate_multi_paths ──────────────────────────────────────────────────────────

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
    use_robocopy: bool = False,
    robocopy_threads: int = 8,
    robocopy_log_dir: Optional[str] = None,
    robocopy_extra_flags: Optional[List[str]] = None,
) -> Dict[str, List[Dict]]:
    """
    Migra múltiples pares (src_dir, dst_dir) de forma paralela o secuencial.

    Cuando use_robocopy=True, cada ruta se procesa con robocopy_directory().
    El callback reporta líneas de stdout en tiempo real (total=-1).

    Args:
        paths            : lista de tuplas (src_dir, dst_dir).
        parallel_paths   : True → cada ruta en su propio hilo de nivel superior;
                           False → rutas procesadas una tras otra.
        progress_callback: fn(path_index, src, done, total, result)
        use_robocopy     : True para usar robocopy.exe (recomendado > 1 TB)
        robocopy_threads : hilos /MT para robocopy (1-128)
        robocopy_log_dir : carpeta donde guardar logs de robocopy
        robocopy_extra_flags: flags adicionales para robocopy
        Resto de parámetros: idénticos a migrate_directory.

    Returns:
        dict { src_dir: [results] } — una clave por cada ruta origen.
    """
    if not paths:
        return {}

    all_results: Dict[str, List[Dict]] = {}

    def _run_single(idx: int, src: str, dst: str) -> Tuple[str, List[Dict]]:
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
            use_robocopy=use_robocopy,
            robocopy_threads=robocopy_threads,
            robocopy_log_dir=robocopy_log_dir,
            robocopy_extra_flags=robocopy_extra_flags,
        )
        return src, results

    if parallel_paths:
        with ThreadPoolExecutor(max_workers=len(paths)) as executor:
            futures = [
                executor.submit(_run_single, idx, src, dst)
                for idx, (src, dst) in enumerate(paths)
            ]
            for future in as_completed(futures):
                src, results = future.result()
                all_results[src] = results
    else:
        for idx, (src, dst) in enumerate(paths):
            src_key, results = _run_single(idx, src, dst)
            all_results[src_key] = results

    total_files = sum(len(v) for v in all_results.values())
    ok      = sum(1 for v in all_results.values() for r in v if r["status"] == "ok")
    updated = sum(1 for v in all_results.values() for r in v if r["status"] == "updated")
    skipped = sum(1 for v in all_results.values() for r in v if r["status"] == "skipped")
    errors  = sum(1 for r in all_results.values() for r in r if r["status"] == "error")
    mode_tag = "robocopy" if use_robocopy else "python"
    logger.info(
        f"Multi-path [{mode_tag}] completado ({len(paths)} rutas, {total_files} entradas): "
        f"{ok} nuevos, {updated} actualizados, {skipped} omitidos, {errors} errores"
    )
    return all_results


# ── rollback_migration ──────────────────────────────────────────────────────────

def rollback_migration(
    log_path: str,
    progress_callback: Optional[Callable] = None
) -> Dict[str, int]:
    """
    Lee un archivo JSON de log de migración y elimina los archivos que fueron
    creados o sobreescritos ("status": "ok" o "updated") en el directorio destino.
    """
    if not os.path.exists(log_path):
        raise FileNotFoundError(f"Log de migración no encontrado: {log_path}")

    with open(log_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("El archivo de log no tiene el formato esperado (lista de resultados).")

    target_files = [item for item in data if item.get("status") in ("ok", "updated")]
    total = len(target_files)
    results = {"deleted": 0, "errors": 0, "not_found": 0}

    for idx, item in enumerate(target_files):
        dst = item.get("dst")
        if not dst:
            continue
        try:
            if os.path.exists(dst):
                os.remove(dst)
                results["deleted"] += 1
                logger.info(f"Rollback: Eliminado {dst}")
            else:
                results["not_found"] += 1
                logger.warning(f"Rollback: Archivo no encontrado {dst}")
        except Exception as e:
            results["errors"] += 1
            logger.error(f"Rollback error en {dst}: {e}")
        if progress_callback:
            progress_callback(idx + 1, total, item)

    logger.info(
        f"Rollback completado: {results['deleted']} eliminados, "
        f"{results['not_found']} no encontrados, {results['errors']} errores"
    )
    return results
