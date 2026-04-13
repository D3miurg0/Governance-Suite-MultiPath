import os
import json
import logging
import threading
from pathlib import Path
from config import Config
from core.compat import tqdm


class AuditCore:
    """
    Estado global de sesión: directorio de salida, lock compartido,
    caché de SIDs y logging estructurado por handler explícito.
    """

    def __init__(self):
        self.access_errors: list = []
        self.global_lock: threading.Lock = threading.Lock()
        self.current_audit_dir: str = ""
        self.sid_cache: dict = {}

        # Crear directorio de logs
        Config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_file = Config.LOGS_DIR / f"session_{Config.TIMESTAMP}.log"
        self.log_file: str = str(log_file)

        # Logger propio — no usa basicConfig para evitar conflictos
        self._logger = logging.getLogger(f"governance.session.{Config.TIMESTAMP}")
        self._logger.setLevel(logging.DEBUG)
        self._logger.propagate = False
        self._attach_file_handler(self.log_file)

    def _attach_file_handler(self, path: str):
        """Adjunta un FileHandler al logger de sesión."""
        # Eliminar handlers anteriores del mismo logger
        for h in self._logger.handlers[:]:
            try:
                h.close()
            except Exception:
                pass
            self._logger.removeHandler(h)

        fh = logging.FileHandler(path, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        self._logger.addHandler(fh)

    def log_error(self, mensaje: str, tipo: str = "CRITICO"):
        full_msg = f"[{tipo}] {mensaje}"
        tqdm.write(f" [!] {full_msg}")
        self._logger.error(full_msg)
        with self.global_lock:
            self.access_errors.append(full_msg)

    def log_audit(self, operation: str, data: dict):
        """Registra un evento de auditoría estructurado (JSON) en el log."""
        msg = f"[AUDIT:{operation}] {json.dumps(data, ensure_ascii=False)}"
        self._logger.info(msg)
        print(f" [*] {msg}")

    def log_info(self, mensaje: str):
        self._logger.info(mensaje)

    def on_walk_error(self, os_error: OSError):
        self.log_error(
            f"ACCESO DENEGADO | {os.path.abspath(os_error.filename)} | {os_error.strerror}",
            "ADVERTENCIA",
        )

    def create_session_folder(self):
        """Crea carpeta audit_XX incremental dentro de output/ y redirige el log."""
        os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
        counter = 1
        while True:
            folder_name = f"audit_{counter:02d}"
            full_path = os.path.join(Config.OUTPUT_DIR, folder_name)
            if not os.path.exists(full_path):
                os.makedirs(full_path)
                self.current_audit_dir = full_path
                # Redirigir log a archivo con nombre de sesión
                new_log = str(Config.LOGS_DIR / f"{folder_name}_{Config.TIMESTAMP}.log")
                self.log_file = new_log
                self._attach_file_handler(new_log)
                print(f"   [+] Sesión iniciada: {folder_name}")
                return
            counter += 1

    def cleanup_session(self):
        """Cierra handlers y elimina carpeta de sesión si quedó vacía."""
        for h in self._logger.handlers[:]:
            try:
                h.close()
            except Exception:
                pass
        logging.shutdown()

        if not self.current_audit_dir or not os.path.exists(self.current_audit_dir):
            return
        if not os.listdir(self.current_audit_dir):
            try:
                os.rmdir(self.current_audit_dir)
                print(" [-] Carpeta de sesión vacía eliminada.")
            except Exception as e:
                print(f" [!] Error eliminando carpeta vacía: {e}")
