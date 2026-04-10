import os
import sys
import csv
import datetime
import time
import concurrent.futures
from config import Config
from core.utils import Utils

try:
    from tqdm import tqdm
    USE_TQDM = True
except ImportError:
    USE_TQDM = False
    class tqdm:
        def __init__(self, iterable=None, desc=None, unit='it', **kwargs): self.iterable = iterable
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def update(self, n=1): pass
        @staticmethod
        def write(s): print(s)
        def __iter__(self): return iter(self.iterable)


class ScanModule:
    """Escaneo multi-hilo de metadatos de archivos en rutas locales y UNC."""

    def __init__(self, core):
        self.core = core

    def _get_file_metadata(self, stats: os.stat_result):
        try:
            dt_mod = datetime.datetime.fromtimestamp(stats.st_mtime)
            dt_cre = datetime.datetime.fromtimestamp(stats.st_ctime)
            year_num = dt_mod.year
            year_str = str(year_num) if Config.MIN_YEAR_VALID <= year_num <= Config.MAX_YEAR_VALID else "Fecha_Invalida"
            return dt_mod.strftime('%Y-%m-%d %H:%M:%S'), dt_cre.strftime('%Y-%m-%d %H:%M:%S'), year_str
        except Exception:
            return "Error", "Error", "Fecha_Invalida"

    def _worker_process_file_scan(self, full_path: str, file_name: str):
        try:
            stats = os.stat(full_path)
            size = stats.st_size
            mb, gb = Utils.convert_bytes(size)
            mod, cre, yr = self._get_file_metadata(stats)
            readable = full_path.replace("\\\\?\\UNC\\", "\\\\").replace("\\\\?\\", "")
            return (True, {'name': file_name, 'path': readable, 'mb': mb, 'gb': gb, 'mod': mod, 'cre': cre, 'year': yr})
        except OSError:
            return (False, None)
        except Exception as e:
            return (False, f"Error: {e}")

    def _process_scan_result(self, future, file_handles: dict, output_path: str):
        try:
            success, data = future.result()
            if success:
                yr = data['year']
                if yr not in file_handles:
                    os.makedirs(output_path, exist_ok=True)
                    csv_name = os.path.join(output_path, f'Reporte_{yr}.csv')
                    mode = 'a' if os.path.exists(csv_name) else 'w'
                    f = open(csv_name, mode, newline='', encoding='utf-8-sig')
                    writer = csv.writer(f)
                    if mode == 'w':
                        writer.writerow(['Nombre', 'Ruta_Completa', 'MB', 'GB', 'Modificacion', 'Creacion'])
                    file_handles[yr] = {'file': f, 'writer': writer}
                file_handles[yr]['writer'].writerow(
                    [data['name'], data['path'], data['mb'], data['gb'], data['mod'], data['cre']]
                )
            elif data:
                self.core.log_error(data, "ERROR_LECTURA_ARCHIVO")
        except Exception:
            pass

    def _clean_unit_name(self, path: str) -> str:
        parts = os.path.normpath(path).split(os.sep)
        if parts[0] == '' and len(parts) > 1 and parts[1] == '':
            name = f"{parts[2]}_{parts[3]}" if len(parts) > 3 else parts[2]
        else:
            name = parts[-1] if parts[-1] else parts[-2]
        return name.replace('\\', '_').replace('$', '').replace(':', '').strip('_') + "_Scan"

    def run_scan(self, drive_path: str):
        """Orquesta el escaneo multi-hilo de un path."""
        print(f"\n" + "-" * 60)
        print(f"   PROCESANDO: {drive_path}")
        print("-" * 60)
        long_path = Utils.get_long_unc_path(drive_path)
        if not os.path.exists(long_path):
            self.core.log_error(f"No se accede a: {drive_path}", "CRITICO")
            return
        folder_name = self._clean_unit_name(drive_path)
        out_dir = os.path.join(self.core.current_audit_dir, folder_name)
        file_handles = {}
        total_files = 0
        start_t = time.time()
        pbar = tqdm(desc="Escaneando", unit="files", mininterval=0.5) if USE_TQDM else None
        with concurrent.futures.ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
            futures_set = set()
            try:
                for root, dirs, files in os.walk(long_path, onerror=self.core.on_walk_error):
                    for name in files:
                        full_path = os.path.join(root, name)
                        futures_set.add(executor.submit(self._worker_process_file_scan, full_path, name))
                        if len(futures_set) >= Config.MAX_WORKERS * 100:
                            done, futures_set = concurrent.futures.wait(
                                futures_set, return_when=concurrent.futures.FIRST_COMPLETED
                            )
                            for f in done:
                                self._process_scan_result(f, file_handles, out_dir)
                                total_files += 1
                                if pbar:
                                    pbar.update(1)
                for f in concurrent.futures.as_completed(futures_set):
                    self._process_scan_result(f, file_handles, out_dir)
                    total_files += 1
                    if pbar:
                        pbar.update(1)
            except KeyboardInterrupt:
                print("\n   [!] Cancelado.")
                executor.shutdown(wait=False)
                raise
            finally:
                if pbar:
                    pbar.close()
        for h in file_handles.values():
            try:
                h['file'].close()
            except Exception:
                pass
        elapsed = round(time.time() - start_t, 2)
        print(f"\n   > FINALIZADO: {total_files} archivos en {elapsed}s. Reportes en: {out_dir}")
