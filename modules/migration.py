import os
import time
import shutil
import datetime
import concurrent.futures
from config import Config, WIN32_ENABLED
from core.utils import Utils
from core.compat import tqdm

try:
    import win32security
    import pywintypes
except ImportError:
    pass


class MigrationModule:
    """Migración paralela/streaming de archivos con manejo de permisos NTFS."""

    def __init__(self, core):
        self.core = core
        self._reset_counters()

    def _reset_counters(self):
        self.copied_count    = 0
        self.omitted_count   = 0
        self.duplicate_count = 0
        self.error_count     = 0
        self.duplicate_list  = []

    def _copy_file_worker(self, src: str, dst: str, copy_permissions: bool) -> str:
        if not WIN32_ENABLED and copy_permissions:
            return "ERROR_PYWIN32_NO_DISPONIBLE"
        for attempt in range(3):
            try:
                shutil.copy2(src, dst)
                if copy_permissions:
                    try:
                        sd = win32security.GetFileSecurity(src, win32security.DACL_SECURITY_INFORMATION)
                        win32security.SetFileSecurity(dst, win32security.DACL_SECURITY_INFORMATION, sd)
                        return "COPIADO_PERMISOS_OK"
                    except pywintypes.error as e:
                        self.core.log_error(f"PERMISOS FALLO | {dst} | {e}", "PERMISOS")
                        if e.winerror in (5, 1314):
                            return f"PERMISOS_ERROR_{e.winerror}"
                        raise
                return "COPIADO_SIN_PERMISOS"
            except (IOError, OSError) as e:
                es_red  = hasattr(e, "winerror") and e.winerror in (59, 64)
                es_lock = hasattr(e, "winerror") and e.winerror in (32, 5)
                if (es_red or es_lock) and attempt < 2:
                    time.sleep((attempt + 1) * 5)
                else:
                    self.core.log_error(f"ERROR COPIA | {src} | {e}", "COPIA")
                    return f"ERROR_FATAL: {e}"
            except Exception as e:
                self.core.log_error(f"ERROR COPIA | {src} | {e}", "COPIA")
                return f"ERROR_FATAL: {e}"
        return "ERROR_REINTENTOS_AGOTADOS"

    def _register_result(self, result: str):
        """Actualiza contadores según el resultado de _copy_file_worker."""
        with self.core.global_lock:
            if "COPIADO" in result:
                self.copied_count += 1
            elif "ERROR" in result:
                self.error_count += 1

    def execute_migration(
        self,
        source_path: str,
        destination_path: str,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        permissions: bool,
        parallel_mode: bool,
        flat_copy_mode: bool,
        overwrite: bool = False,
    ):
        self._reset_counters()
        if not os.path.exists(source_path):
            self.core.log_error("La ruta de origen no existe.", "GENERAL")
            return

        print(f"Migración: {source_path} -> {destination_path}")
        print(f"Modo: {'Paralelo' if parallel_mode else 'Streaming'} | Permisos: {permissions} | Plano: {flat_copy_mode}")
        start_time = time.time()

        src_long = Utils.get_long_unc_path(source_path)
        dst_long = Utils.get_long_unc_path(destination_path)

        if parallel_mode:
            self._parallel_migration(src_long, dst_long, start_date, end_date, permissions, flat_copy_mode, overwrite)
        else:
            self._streaming_migration(src_long, dst_long, start_date, end_date, permissions, flat_copy_mode, overwrite)

        elapsed = time.time() - start_time
        self.core.log_audit("MIGRATION", {
            "source":      source_path,
            "destination": destination_path,
            "copied":      self.copied_count,
            "omitted":     self.omitted_count,
            "errors":      self.error_count,
            "duplicates":  self.duplicate_count,
            "elapsed":     f"{elapsed:.2f}s",
        })
        print(
            f"\n--- Resumen: Copiados: {self.copied_count} | "
            f"Omitidos: {self.omitted_count} | "
            f"Errores: {self.error_count} | "
            f"Duplicados: {self.duplicate_count} ---"
        )

    def _parallel_migration(self, src, dst, start_date, end_date, permissions, flat_copy_mode, overwrite):
        files_to_copy = []
        folders_to_create = {}

        print("--- FASE 1: Analizando ---")
        with tqdm(desc="Analizando", unit="obj") as pbar:
            for root, dirs, files in os.walk(src, onerror=self.core.on_walk_error):
                for file in files:
                    pbar.update(1)
                    src_full = os.path.join(root, file)
                    try:
                        stats = os.stat(src_full)
                        if not Utils.is_file_valid(src_full, stats, start_date, end_date, flat_copy_mode):
                            with self.core.global_lock:
                                self.omitted_count += 1
                            continue
                        rel_path = os.path.relpath(src_full, src)
                        dst_full = os.path.join(dst, rel_path)
                        if os.path.exists(dst_full) and not overwrite:
                            with self.core.global_lock:
                                self.duplicate_count += 1
                                self.duplicate_list.append(src_full)
                        else:
                            files_to_copy.append((src_full, dst_full))
                            temp = root
                            while len(temp) >= len(src):
                                if temp in folders_to_create:
                                    break
                                rel_p = os.path.relpath(temp, src)
                                folders_to_create[temp] = os.path.join(dst, rel_p)
                                if temp == src:
                                    break
                                temp = os.path.dirname(temp)
                    except Exception as e:
                        self.core.log_error(f"ERROR LECTURA | {src_full} | {e}", "LECTURA")
                        with self.core.global_lock:
                            self.error_count += 1

        print(f"\n--- FASE 2: Creando {len(folders_to_create)} carpetas ---")
        for src_f, dst_f in tqdm(
            sorted(folders_to_create.items(), key=lambda x: len(x[1])), desc="Carpetas"
        ):
            try:
                os.makedirs(dst_f, exist_ok=True)
                shutil.copystat(src_f, dst_f)
            except Exception as e:
                self.core.log_error(f"ERROR CARPETA | {dst_f} | {e}", "COPIA")
                with self.core.global_lock:
                    self.error_count += 1

        print(f"\n--- FASE 3: Copiando {len(files_to_copy)} archivos ---")
        with concurrent.futures.ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
            futures = {
                executor.submit(self._copy_file_worker, s, d, permissions): s
                for s, d in files_to_copy
            }
            for fut in tqdm(concurrent.futures.as_completed(futures), total=len(files_to_copy), desc="Copiando"):
                self._register_result(fut.result())

    def _streaming_migration(self, src, dst, start_date, end_date, permissions, flat_copy_mode, overwrite):
        with tqdm(desc="Procesando", unit="obj") as pbar:
            for root, dirs, files in os.walk(src, onerror=self.core.on_walk_error):
                for file in files:
                    pbar.update(1)
                    src_full = os.path.join(root, file)
                    try:
                        stats = os.stat(src_full)
                        if not Utils.is_file_valid(src_full, stats, start_date, end_date, flat_copy_mode):
                            with self.core.global_lock:
                                self.omitted_count += 1
                            continue
                        rel = os.path.relpath(src_full, src)
                        dst_full = os.path.join(dst, rel)
                        if os.path.exists(dst_full) and not overwrite:
                            with self.core.global_lock:
                                self.duplicate_count += 1
                        else:
                            os.makedirs(os.path.dirname(dst_full), exist_ok=True)
                            res = self._copy_file_worker(src_full, dst_full, permissions)
                            self._register_result(res)
                    except Exception as e:
                        self.core.log_error(f"ERROR STREAM | {src_full} | {e}", "LECTURA")
                        with self.core.global_lock:
                            self.error_count += 1
