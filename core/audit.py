import os
import sys
import shutil
import threading
import logging
from config import Config

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


class AuditCore:
    """Gestiona el estado global de la sesión (errores, logging, directorio)."""

    def __init__(self):
        self.access_errors: list = []
        self.global_lock: threading.Lock = threading.Lock()
        self.current_audit_dir: str = ""
        self.sid_cache: dict = {}
        os.makedirs(Config.LOGS_DIR, exist_ok=True)
        self.log_file: str = os.path.join(Config.LOGS_DIR, f"session_{Config.TIMESTAMP}.log")
        self._setup_logging()

    def _setup_logging(self):
        logging.basicConfig(
            filename=self.log_file,
            level=logging.ERROR,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def _update_logging_handler(self):
        logging.basicConfig(
            filename=self.log_file,
            level=logging.ERROR,
            format='%(asctime)s - %(levelname)s - %(message)s',
            force=True
        )

    def log_error(self, mensaje: str, tipo: str = "CRITICO"):
        full_msg = f"[{tipo}] {mensaje}"
        tqdm.write(f" [!] {full_msg}")
        logging.error(full_msg)
        with self.global_lock:
            self.access_errors.append(full_msg)

    def log_audit(self, operation: str, data: dict):
        """Registra un evento de auditoría en el log de sesión."""
        import json
        msg = f"[AUDIT:{operation}] {json.dumps(data, ensure_ascii=False)}"
        logging.info(msg)
        print(f" [*] {msg}")

    def on_walk_error(self, os_error: OSError):
        self.log_error(
            f"ACCESO DENEGADO (CARPETA) | {os.path.abspath(os_error.filename)} | {os_error.strerror}",
            "ADVERTENCIA"
        )

    def create_session_folder(self):
        """Crea carpeta audit_XX incremental dentro de output/."""
        os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
        counter = 1
        while True:
            folder_name = f"audit_{counter:02d}"
            full_path = os.path.join(Config.OUTPUT_DIR, folder_name)
            if not os.path.exists(full_path):
                os.makedirs(full_path)
                self.current_audit_dir = full_path
                self.log_file = os.path.join(Config.LOGS_DIR, f"{folder_name}_{Config.TIMESTAMP}.log")
                self._update_logging_handler()
                print(f"   [+] Sesión iniciada: {folder_name}")
                return
            counter += 1

    def cleanup_session(self):
        """Limpia carpeta de sesión si quedó vacía."""
        if not self.current_audit_dir or not os.path.exists(self.current_audit_dir):
            return
        logging.shutdown()
        remaining = os.listdir(self.current_audit_dir)
        if not remaining:
            try:
                os.rmdir(self.current_audit_dir)
                print(f" [-] Carpeta de sesión vacía eliminada.")
            except Exception as e:
                print(f"Error eliminando carpeta vacía: {e}")
