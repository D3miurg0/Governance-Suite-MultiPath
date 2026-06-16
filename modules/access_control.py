"""
modules/access_control.py
─────────────────────────────────────────────────────────────────────────────
Gestión de derechos de acceso NTFS en entorno Active Directory.
Implementa los controles ISO/IEC 27001:2022:
  • 5.15 — Control de acceso (otorgar, denegar, consultar)
  • 5.18 — Derechos de acceso (revocar, revisar sobrantes, ciclo de vida)

Todas las operaciones de escritura quedan registradas en AuditCore.
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import csv
import os
from datetime import datetime
from typing import Optional

from config import Config, WIN32_ENABLED
from core.utils import Utils

try:
    import win32security
    import win32net
    import win32netcon
    import pywintypes
    import ntsecuritycon as con
except ImportError:
    pass

# ── Niveles de permiso reconocidos (ISO 5.15 — mínimo privilegio) ─────────
PERMISSION_LEVELS: dict[str, int] = {}
if WIN32_ENABLED:
    import ntsecuritycon as _con
    PERMISSION_LEVELS = {
        "Read":            _con.FILE_GENERIC_READ,
        "Read & Execute":  _con.FILE_GENERIC_READ | _con.FILE_GENERIC_EXECUTE,
        "Write":           _con.FILE_GENERIC_WRITE,
        "Modify":          (_con.FILE_GENERIC_READ | _con.FILE_GENERIC_WRITE
                            | _con.FILE_GENERIC_EXECUTE | _con.DELETE),
        "Full Control":    _con.FILE_ALL_ACCESS,
    }


class AccessControlModule:
    """
    Módulo de gestión de derechos de acceso NTFS alineado a ISO 27001:2022.

    Operaciones disponibles
    ────────────────────────
    Consulta (5.15 / 5.18)
      list_access(path)              — lista todos los ACEs de una ruta
      effective_access(path, user)   — calcula acceso efectivo de un usuario/grupo
      review_orphan_access(path)     — detecta ACEs de cuentas no resolvibles (sobrantes)

    Escritura (5.15)
      grant_access(path, account, level, inherit)  — otorga permiso Allow
      deny_access(path, account, level)            — aplica ACE Deny explícito

    Revocación (5.18)
      revoke_access(path, account)                 — elimina todos los ACEs del usuario
      revoke_inherited_overrides(path)             — elimina ACEs explícitos que duplican herencia

    Exportación
      export_access_report(path, depth, output_dir) — CSV completo para auditoría
    """

    def __init__(self, core):
        self.core = core

    # ──────────────────────────────────────────────────────────────────────
    # Utilidades internas
    # ──────────────────────────────────────────────────────────────────────

    def _check_win32(self) -> bool:
        if not WIN32_ENABLED:
            print("❌  pywin32 no disponible. Instalar: pip install pywin32")
            return False
        return True

    def _resolve_sid(self, sid) -> str:
        """Resuelve SID → DOMINIO\\cuenta usando caché del AuditCore."""
        sid_str = str(sid)
        if sid_str in self.core.sid_cache:
            return self.core.sid_cache[sid_str]
        try:
            account, domain, _ = win32security.LookupAccountSid(None, sid)
            name = f"{domain}\\{account}" if domain else account
        except pywintypes.error:
            name = sid_str          # SID sin resolver → posible cuenta sobrante
        self.core.sid_cache[sid_str] = name
        return name

    def _lookup_account(self, account: str):
        """
        Convierte 'DOMINIO\\usuario' o 'usuario' en un objeto SID de Windows.
        Raises pywintypes.error si la cuenta no existe en el dominio/DC.
        """
        sid, domain, _ = win32security.LookupAccountName(None, account)
        return sid

    def _get_dacl(self, path: str):
        """Devuelve (security_descriptor, dacl) de una ruta NTFS."""
        long_path = Utils.get_long_unc_path(path)
        sd = win32security.GetFileSecurity(
            long_path,
            win32security.DACL_SECURITY_INFORMATION
        )
        dacl = sd.GetSecurityDescriptorDacl()
        return sd, dacl, long_path

    def _set_dacl(self, long_path: str, sd, dacl):
        """Aplica el DACL modificado a la ruta."""
        sd.SetSecurityDescriptorDacl(True, dacl, False)
        win32security.SetFileSecurity(
            long_path,
            win32security.DACL_SECURITY_INFORMATION,
            sd
        )

    def _ace_type_str(self, ace_type: int) -> str:
        return "Allow" if ace_type == con.ACCESS_ALLOWED_ACE_TYPE else "Deny"

    def _mask_to_str(self, mask: int) -> str:
        for level, m in PERMISSION_LEVELS.items():
            if mask == m:
                return level
        # Descomponer bits conocidos
        parts = []
        if mask & con.FILE_GENERIC_READ:    parts.append("Read")
        if mask & con.FILE_GENERIC_WRITE:   parts.append("Write")
        if mask & con.FILE_GENERIC_EXECUTE: parts.append("Execute")
        if mask & con.DELETE:               parts.append("Delete")
        if mask & con.WRITE_DAC:            parts.append("Change Permissions")
        if mask & con.WRITE_OWNER:          parts.append("Take Ownership")
        return " | ".join(parts) if parts else f"Especial (0x{mask:08X})"

    def _inherit_flags(self, inherit: bool) -> int:
        """Flags de herencia estándar para carpetas: OI + CI."""
        if not inherit:
            return 0
        return (
            win32security.OBJECT_INHERIT_ACE
            | win32security.CONTAINER_INHERIT_ACE
        )

    # ──────────────────────────────────────────────────────────────────────
    # ISO 5.15 — Consulta de acceso
    # ──────────────────────────────────────────────────────────────────────

    def list_access(self, path: str) -> list[dict]:
        """
        Lista todos los ACEs (Allow y Deny) de una ruta.
        Retorna lista de dicts con: account, type, permissions,
        inherited, mask, sid_raw.
        """
        if not self._check_win32():
            return []
        results = []
        try:
            _, dacl, _ = self._get_dacl(path)
            if not dacl:
                return []
            for i in range(dacl.GetAceCount()):
                (ace_type, ace_flags), mask, sid = dacl.GetAce(i)
                results.append({
                    "path":       path,
                    "account":    self._resolve_sid(sid),
                    "type":       self._ace_type_str(ace_type),
                    "permissions": self._mask_to_str(mask),
                    "mask":       mask,
                    "inherited":  bool(ace_flags & Config.INHERITED_ACE),
                    "sid_raw":    str(sid),
                })
        except pywintypes.error as e:
            self.core.log_error(f"list_access | {path} | {e.strerror}", "PERMISOS")
        return results

    def effective_access(self, path: str, account: str) -> dict:
        """
        Calcula el acceso efectivo de una cuenta sobre una ruta.
        Evalúa Allow y Deny; los Deny tienen precedencia (NTFS estándar).
        ISO 5.15 — principio de mínimo privilegio.
        """
        if not self._check_win32():
            return {}
        aces = self.list_access(path)
        if not aces:
            return {"account": account, "path": path, "effective_mask": 0, "summary": "Sin ACEs"}

        account_lower = account.lower()
        allow_mask = 0
        deny_mask  = 0

        for ace in aces:
            if ace["account"].lower() == account_lower:
                if ace["type"] == "Allow":
                    allow_mask |= ace["mask"]
                else:
                    deny_mask  |= ace["mask"]

        effective = allow_mask & ~deny_mask
        return {
            "account":        account,
            "path":           path,
            "allow_mask":     allow_mask,
            "deny_mask":      deny_mask,
            "effective_mask": effective,
            "summary":        self._mask_to_str(effective) if effective else "Sin acceso efectivo",
        }

    def review_orphan_access(self, path: str, depth: int = 2) -> list[dict]:
        """
        Detecta ACEs cuyo SID no puede resolverse contra el DC.
        Indica cuentas eliminadas, deshabilitadas o mal migradas.
        ISO 5.18 — revisión y eliminación de derechos sobrantes.
        """
        if not self._check_win32():
            return []
        orphans = []
        long_path = Utils.get_long_unc_path(path)

        for root, dirs, _ in os.walk(long_path, onerror=self.core.on_walk_error):
            try:
                rel = os.path.relpath(root, long_path)
                cur_depth = 0 if rel == "." else rel.count(os.sep) + 1
            except ValueError:
                cur_depth = 0
            if depth != -1 and cur_depth > depth:
                dirs[:] = []
                continue

            for ace_info in self.list_access(root):
                # Si el account sigue siendo el SID en bruto → no resolvible
                raw = ace_info["sid_raw"]
                if ace_info["account"] == raw:
                    orphans.append({
                        "path":        root,
                        "sid":         raw,
                        "type":        ace_info["type"],
                        "permissions": ace_info["permissions"],
                        "inherited":   ace_info["inherited"],
                        "iso_control": "5.18 — Derecho sobrante (SID no resolvible)",
                    })
        return orphans

    # ──────────────────────────────────────────────────────────────────────
    # ISO 5.15 — Asignación de acceso
    # ──────────────────────────────────────────────────────────────────────

    def grant_access(
        self,
        path: str,
        account: str,
        level: str = "Read",
        inherit: bool = True,
    ) -> bool:
        """
        Agrega un ACE Allow a la DACL de la ruta.
        ISO 5.15 — asignación formal de derechos de acceso.

        level: 'Read' | 'Read & Execute' | 'Write' | 'Modify' | 'Full Control'
        inherit: True → OI+CI (propagación a subcarpetas y archivos)
        """
        if not self._check_win32():
            return False
        if level not in PERMISSION_LEVELS:
            print(f"❌  Nivel inválido: {level}. Opciones: {list(PERMISSION_LEVELS)}")
            return False
        try:
            sid = self._lookup_account(account)
        except pywintypes.error as e:
            self.core.log_error(
                f"grant_access | Cuenta no encontrada: {account} | {e.strerror}",
                "ACCESO"
            )
            print(f"❌  Cuenta no encontrada en el dominio: {account}")
            return False

        try:
            sd, dacl, long_path = self._get_dacl(path)
            if dacl is None:
                dacl = win32security.ACL()

            mask  = PERMISSION_LEVELS[level]
            flags = self._inherit_flags(inherit)
            dacl.AddAccessAllowedAceEx(win32security.ACL_REVISION, flags, mask, sid)
            self._set_dacl(long_path, sd, dacl)

            self.core.log_audit("ACCESS_GRANT", {
                "path":    path,
                "account": account,
                "level":   level,
                "inherit": inherit,
                "iso":     "5.15",
            })
            print(f"✅  Permiso '{level}' otorgado a '{account}' en: {path}")
            return True
        except pywintypes.error as e:
            self.core.log_error(
                f"grant_access | {path} | {account} | {e.strerror}", "ACCESO"
            )
            print(f"❌  Error al otorgar permiso: {e.strerror}")
            return False

    def deny_access(
        self,
        path: str,
        account: str,
        level: str = "Full Control",
    ) -> bool:
        """
        Agrega un ACE Deny explícito (precede a cualquier Allow).
        ISO 5.15 — restricción explícita de acceso.
        """
        if not self._check_win32():
            return False
        if level not in PERMISSION_LEVELS:
            print(f"❌  Nivel inválido: {level}.")
            return False
        try:
            sid = self._lookup_account(account)
        except pywintypes.error as e:
            self.core.log_error(
                f"deny_access | Cuenta no encontrada: {account} | {e.strerror}",
                "ACCESO"
            )
            print(f"❌  Cuenta no encontrada: {account}")
            return False

        try:
            sd, dacl, long_path = self._get_dacl(path)
            if dacl is None:
                dacl = win32security.ACL()

            mask = PERMISSION_LEVELS[level]
            # Deny sin herencia por defecto — para evitar bloqueos accidentales en árbol
            dacl.AddAccessDeniedAceEx(win32security.ACL_REVISION, 0, mask, sid)
            self._set_dacl(long_path, sd, dacl)

            self.core.log_audit("ACCESS_DENY", {
                "path":    path,
                "account": account,
                "level":   level,
                "iso":     "5.15",
            })
            print(f"🚫  Deny '{level}' aplicado a '{account}' en: {path}")
            return True
        except pywintypes.error as e:
            self.core.log_error(
                f"deny_access | {path} | {account} | {e.strerror}", "ACCESO"
            )
            print(f"❌  Error al aplicar Deny: {e.strerror}")
            return False

    # ──────────────────────────────────────────────────────────────────────
    # ISO 5.18 — Revocación de acceso
    # ──────────────────────────────────────────────────────────────────────

    def revoke_access(self, path: str, account: str) -> bool:
        """
        Elimina TODOS los ACEs explícitos (Allow y Deny) del usuario/grupo
        de la DACL de la ruta. Los ACEs heredados no se tocan.
        ISO 5.18 — baja/revocación formal de derechos de acceso.
        """
        if not self._check_win32():
            return False
        try:
            sid_target = self._lookup_account(account)
        except pywintypes.error as e:
            self.core.log_error(
                f"revoke_access | Cuenta no encontrada: {account} | {e.strerror}",
                "ACCESO"
            )
            print(f"❌  Cuenta no encontrada: {account}")
            return False

        try:
            sd, dacl, long_path = self._get_dacl(path)
            if not dacl:
                print("ℹ️  Sin DACL en la ruta.")
                return False

            # Reconstruir DACL sin los ACEs del usuario objetivo
            new_dacl  = win32security.ACL()
            removed   = 0
            str_target = str(sid_target)

            for i in range(dacl.GetAceCount()):
                (ace_type, ace_flags), mask, sid = dacl.GetAce(i)
                is_inherited = bool(ace_flags & Config.INHERITED_ACE)
                if str(sid) == str_target and not is_inherited:
                    removed += 1
                    continue    # Saltar este ACE → queda revocado
                if ace_type == con.ACCESS_ALLOWED_ACE_TYPE:
                    new_dacl.AddAccessAllowedAceEx(
                        win32security.ACL_REVISION, ace_flags, mask, sid
                    )
                elif ace_type == con.ACCESS_DENIED_ACE_TYPE:
                    new_dacl.AddAccessDeniedAceEx(
                        win32security.ACL_REVISION, ace_flags, mask, sid
                    )

            self._set_dacl(long_path, sd, new_dacl)

            self.core.log_audit("ACCESS_REVOKE", {
                "path":         path,
                "account":      account,
                "aces_removed": removed,
                "iso":          "5.18",
            })
            print(f"✅  {removed} ACE(s) revocados para '{account}' en: {path}")
            return True
        except pywintypes.error as e:
            self.core.log_error(
                f"revoke_access | {path} | {account} | {e.strerror}", "ACCESO"
            )
            print(f"❌  Error al revocar: {e.strerror}")
            return False

    def revoke_inherited_overrides(self, path: str) -> int:
        """
        Elimina ACEs explícitos que duplican exactamente un ACE heredado
        (mismo SID, mismo mask, mismo tipo). Reduce ruido en la DACL.
        ISO 5.18 — eliminación de permisos redundantes / sobrantes.
        Retorna el número de ACEs eliminados.
        """
        if not self._check_win32():
            return 0
        try:
            sd, dacl, long_path = self._get_dacl(path)
            if not dacl:
                return 0

            aces = [
                ((t, f), m, s)
                for i in range(dacl.GetAceCount())
                for (t, f), m, s in [dacl.GetAce(i)]
            ]

            # Índices de ACEs heredados
            inherited_set = {
                (t, m, str(s))
                for (t, f), m, s in aces
                if f & Config.INHERITED_ACE
            }

            new_dacl = win32security.ACL()
            removed  = 0
            for (ace_type, ace_flags), mask, sid in aces:
                is_inherited = bool(ace_flags & Config.INHERITED_ACE)
                key = (ace_type, mask, str(sid))
                # Eliminar solo si es explícito Y duplica uno heredado
                if not is_inherited and key in inherited_set:
                    removed += 1
                    continue
                if ace_type == con.ACCESS_ALLOWED_ACE_TYPE:
                    new_dacl.AddAccessAllowedAceEx(
                        win32security.ACL_REVISION, ace_flags, mask, sid
                    )
                elif ace_type == con.ACCESS_DENIED_ACE_TYPE:
                    new_dacl.AddAccessDeniedAceEx(
                        win32security.ACL_REVISION, ace_flags, mask, sid
                    )

            if removed:
                self._set_dacl(long_path, sd, new_dacl)
                self.core.log_audit("ACCESS_CLEANUP", {
                    "path":    path,
                    "removed": removed,
                    "iso":     "5.18",
                })
            return removed
        except pywintypes.error as e:
            self.core.log_error(
                f"revoke_inherited_overrides | {path} | {e.strerror}", "ACCESO"
            )
            return 0

    # ──────────────────────────────────────────────────────────────────────
    # Exportación — reporte CSV completo
    # ──────────────────────────────────────────────────────────────────────

    def export_access_report(
        self,
        path: str,
        depth: int = 2,
        output_dir: Optional[str] = None,
    ) -> str:
        """
        Recorre el árbol de carpetas hasta 'depth' niveles y genera un CSV
        con todas las ACEs, incluyendo columna ISO_Flag para ACEs sobrantes.
        ISO 5.15 + 5.18 — trazabilidad de derechos de acceso.
        """
        if not self._check_win32():
            return ""

        out_dir   = output_dir or self.core.current_audit_dir
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file  = os.path.join(out_dir, f"Reporte_AccesoISO_{timestamp}.csv")
        os.makedirs(out_dir, exist_ok=True)

        long_path = Utils.get_long_unc_path(path)
        rows_written = 0

        try:
            with open(out_file, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Ruta", "Cuenta", "Tipo", "Permisos", "Mascara_Hex",
                    "Heredado", "ISO_Control", "Timestamp_Auditoria"
                ])
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                for root, dirs, _ in os.walk(
                    long_path, onerror=self.core.on_walk_error
                ):
                    try:
                        rel = os.path.relpath(root, long_path)
                        cur_depth = 0 if rel == "." else rel.count(os.sep) + 1
                    except ValueError:
                        cur_depth = 0
                    if depth != -1 and cur_depth > depth:
                        dirs[:] = []
                        continue

                    readable_path = root.replace("\\\\?\\UNC\\", "\\\\").replace("\\\\?\\", "")
                    for ace in self.list_access(root):
                        is_orphan  = ace["account"] == ace["sid_raw"]
                        iso_flag   = "5.18 — Sobrante" if is_orphan else "5.15 — Activo"
                        writer.writerow([
                            readable_path,
                            ace["account"],
                            ace["type"],
                            ace["permissions"],
                            f"0x{ace['mask']:08X}",
                            "Sí" if ace["inherited"] else "No",
                            iso_flag,
                            ts,
                        ])
                        rows_written += 1
        except KeyboardInterrupt:
            print("\n   [!] Exportación interrumpida.")
        except Exception as e:
            self.core.log_error(f"export_access_report | {e}", "CRITICO")

        self.core.log_audit("ACCESS_REPORT", {
            "path":  path,
            "depth": depth,
            "rows":  rows_written,
            "file":  out_file,
            "iso":   "5.15 / 5.18",
        })
        print(f"\n✅  Reporte generado ({rows_written} filas): {out_file}")
        return out_file
