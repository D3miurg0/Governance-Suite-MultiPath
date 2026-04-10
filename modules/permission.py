import os
import csv
from config import Config, WIN32_ENABLED
from core.utils import Utils

try:
    import win32security
    import pywintypes
    import ntsecuritycon as con
except ImportError:
    pass

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


class PermissionModule:
    """Auditoría de permisos ACL NTFS con exportación CSV."""

    def __init__(self, core):
        self.core = core

    def _resolve_sid_with_cache(self, sid) -> str:
        sid_str = str(sid)
        if sid_str in self.core.sid_cache:
            return self.core.sid_cache[sid_str]
        try:
            account, domain, _ = win32security.LookupAccountSid(None, sid)
            nombre = f"{domain}\\{account}"
        except pywintypes.error:
            nombre = sid_str
        self.core.sid_cache[sid_str] = nombre
        return nombre

    def _parse_permissions_mask(self, mask: int) -> str:
        for key, name in Config.PERMISSIONS_MAP.items():
            if mask == key:
                return name
        extras = []
        if WIN32_ENABLED:
            if mask & con.WRITE_DAC:
                extras.append("CHANGE PERMISSIONS")
            if mask & con.WRITE_OWNER:
                extras.append("TAKE OWNERSHIP")
            if mask & con.DELETE:
                extras.append("DELETE")
        return f"Special ({', '.join(extras)})" if extras else f"Permisos Especiales ({mask})"

    def _analyze_folder_permissions(self, folder_path: str) -> list:
        if not WIN32_ENABLED:
            return [[folder_path, "PYWIN32 NO DISPONIBLE", "", "", ""]]
        rows = []
        try:
            sec_desc = win32security.GetFileSecurity(folder_path, win32security.DACL_SECURITY_INFORMATION)
            dacl = sec_desc.GetSecurityDescriptorDacl()
            if not dacl:
                return []
            for i in range(dacl.GetAceCount()):
                ace = dacl.GetAce(i)
                (ace_type, ace_flags), mask, sid = ace
                user_group = self._resolve_sid_with_cache(sid)
                perm_type = "Allow" if ace_type == con.ACCESS_ALLOWED_ACE_TYPE else "Deny"
                inherited = "Heredado" if (ace_flags & Config.INHERITED_ACE) else "Explícito"
                readable = self._parse_permissions_mask(mask)
                rows.append([folder_path, user_group, perm_type, readable, inherited])
        except pywintypes.error as e:
            rows.append([folder_path, f"ERROR: {e.strerror}", "", "", ""])
            self.core.log_error(f"ACL: {folder_path} -> {e.strerror}", "PERMISOS")
        except Exception as e:
            rows.append([folder_path, f"ERROR INESPERADO: {e}", "", "", ""])
        return rows

    def generate_permission_matrix(self, path: str, depth: int = 2):
        """Escanea permisos ACL y exporta a CSV."""
        if not WIN32_ENABLED:
            print("❌ ERROR: pywin32 requerido. Instale con: pip install pywin32")
            return
        if not path:
            print("ERROR: No se proporcionó ruta.")
            return
        source_long = Utils.get_long_unc_path(path)
        file_name = f'Reporte_Permisos_{Config.TIMESTAMP}.csv'
        output_file = os.path.join(self.core.current_audit_dir, file_name)
        print(f"\n📍 Reporte: {output_file}")
        try:
            with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["Ruta de Carpeta", "Usuario o Grupo", "Tipo", "Permisos", "Nivel"])
                with tqdm(desc="Carpetas", unit=" dirs") as pbar:
                    for root, dirs, files in os.walk(source_long, topdown=True, onerror=self.core.on_walk_error):
                        pbar.update(1)
                        try:
                            rel = os.path.relpath(root, source_long)
                            cur_depth = 0 if rel == '.' else rel.count(os.sep) + 1
                        except ValueError:
                            cur_depth = 0
                        if depth != -1 and cur_depth > depth:
                            dirs[:] = []
                            continue
                        writer.writerows(self._analyze_folder_permissions(root))
        except KeyboardInterrupt:
            print("\n--- INTERRUMPIDO ---")
        except Exception as e:
            self.core.log_error(f"ERROR FATAL: {e}", "CRITICO")
        print(f"\n✅ Auditoría finalizada. Reporte en: {output_file}")
