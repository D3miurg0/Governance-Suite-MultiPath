import os
import subprocess
import datetime


class Utils:
    """Utilidades estáticas compartidas por todos los módulos."""

    @staticmethod
    def get_long_unc_path(path: str) -> str:
        r"""Aplica prefijo \\?\ para superar el límite de 260 caracteres en Windows."""
        path = os.path.normpath(path)
        if path.startswith("\\\\"):
            if not path.startswith("\\\\\\\\\\\\\\\\"):
                return f"\\\\\\\\?\\\\UNC\\\\{path.lstrip('\\\\')}"
        elif path and not path.startswith("\\\\\\\\\\\\\\\\"):
            return f"\\\\\\\\?\\\\{path}"
        return path

    @staticmethod
    def convert_bytes(size_in_bytes: int) -> tuple:
        if not size_in_bytes:
            return 0.0, 0.0
        mb = size_in_bytes / (1024 * 1024)
        gb = size_in_bytes / (1024 * 1024 * 1024)
        return round(mb, 2), round(gb, 4)

    @staticmethod
    def get_extension(filename: str) -> str:
        try:
            ext = os.path.splitext(str(filename))[1].lower()
            return ext if ext else '.sin_extension'
        except Exception:
            return '.invalido'

    @staticmethod
    def get_top_folder(ruta: str) -> str:
        try:
            parts = os.path.normpath(str(ruta)).split(os.sep)
            if ruta.startswith('\\\\\\\\'):
                if len(parts) >= 4:
                    return os.sep.join(parts[:4])
            return parts[0]
        except Exception:
            return 'Ruta_Invalida'

    @staticmethod
    def is_file_valid(
        file_path: str,
        stats: os.stat_result,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        flat_copy_mode: bool,
        min_mb: float = 1.0
    ) -> bool:
        if flat_copy_mode:
            return stats.st_size > 0
        f_mod = datetime.datetime.fromtimestamp(stats.st_mtime)
        mb, _ = Utils.convert_bytes(stats.st_size)
        return start_date <= f_mod <= end_date and mb >= min_mb

    @staticmethod
    def discover_shares(server_ip: str, core) -> list:
        share_paths = []
        clean_server = server_ip.strip('\\\\')
        try:
            result = subprocess.run(
                ['net', 'view', f'\\\\\\\\{clean_server}'],
                capture_output=True, text=True, encoding='cp850', timeout=10
            )
        except Exception as e:
            core.log_error(f"Error net view en \\\\\\\\{clean_server}: {e}", "ADVERTENCIA")
            return []
        if result.returncode != 0:
            core.log_error(f"No se pudo listar shares de \\\\\\\\{clean_server}", "ADVERTENCIA")
            return []
        lines = result.stdout.splitlines()
        parsing = False
        for line in lines:
            if line.startswith('---'):
                parsing = True
                continue
            if parsing and ('complet' in line.lower()):
                break
            if parsing:
                parts = line.strip().split()
                if len(parts) >= 2 and parts[0].startswith('\\\\\\\\'):
                    share_paths.append(parts[0])
        return share_paths
