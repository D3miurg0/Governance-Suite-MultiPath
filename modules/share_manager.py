"""
modules/share_manager.py
─────────────────────────────────────────────────────────────────────────────
Gestión de recursos compartidos SMB — con soporte MULTI-SERVIDOR.

El módulo ya NO está atado al servidor local. Cada instancia recibe un
`server` que puede ser:
  - None / ""          → servidor local (comportamiento anterior)
  - "NOMBRE_SERVIDOR"  → nombre NetBIOS
  - "192.168.x.x"      → dirección IP

Flujo típico multi-servidor:
  1. set_server(hostname_or_ip)    — apunta al servidor destino
  2. list_shares()                 — enumera todos sus shares
  3. migrate_share(name, new_path) — export → update → verify
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from typing import Optional

from config import WIN32_ENABLED

try:
    import win32net
    import win32netcon
    import win32security
    import pywintypes
except ImportError:
    pass

_SHARE_INFO_LEVEL = 502


class ShareManagerModule:
    """
    Módulo de gestión de shares SMB, compatible con múltiples servidores.

    Uso básico
    ──────────
    mgr = ShareManagerModule(core)
    mgr.set_server("FS01")          # cambia al servidor FS01
    shares = mgr.list_shares()      # enumera shares de FS01
    mgr.migrate_share("GDL", "E:\\GDL")
    """

    def __init__(self, core=None, server: str = ""):
        self.core = core
        # None = local, str = remote (NetBIOS name o IP)
        self._server: Optional[str] = server.strip() or None

    # ── Configuración de servidor ─────────────────────────────────────────

    def set_server(self, server: str):
        """
        Apunta el módulo a un servidor diferente.
        Pasar cadena vacía o None para operar en el servidor local.
        """
        clean = (server or "").strip()
        self._server = clean if clean else None
        label = self._server or "localhost"
        self._log(f"Servidor activo: {label}")

    @property
    def server_label(self) -> str:
        return self._server or "localhost"

    # ── Helpers internos ─────────────────────────────────────────────────

    def _check_win32(self) -> bool:
        if not WIN32_ENABLED:
            print("❌  pywin32 no disponible. Instalar: pip install pywin32")
            return False
        return True

    def _log(self, msg: str, level: str = "INFO"):
        print(f"[{level}] {msg}")
        if self.core:
            if level == "ERROR":
                self.core.log_error(msg, "SHARE")
            else:
                self.core.log_audit("SHARE", {"server": self.server_label,
                                               "msg": msg, "level": level})

    # ── Consulta ──────────────────────────────────────────────────────────

    def list_shares(self, skip_admin: bool = True) -> list[dict]:
        """
        Retorna todos los shares del servidor activo.
        Si skip_admin=True omite shares administrativos (C$, ADMIN$, IPC$).
        """
        if not self._check_win32():
            return []
        shares = []
        try:
            resume = 0
            while True:
                data, total, resume = win32net.NetShareEnum(
                    self._server, 1, resume, 32768
                )
                for s in data:
                    name = s["netname"]
                    # Filtrar shares administrativos (terminan en $)
                    if skip_admin and name.endswith("$"):
                        continue
                    shares.append({
                        "name":    name,
                        "path":    s["path"],
                        "comment": s.get("remark", ""),
                        "type":    s["type"],
                        "server":  self.server_label,
                    })
                if not resume:
                    break
        except pywintypes.error as e:
            self._log(f"list_shares [{self.server_label}] | {e.strerror}", "ERROR")
        return shares

    def get_share_info(self, name: str) -> Optional[dict]:
        """Detalle completo (nivel 502) de un share en el servidor activo."""
        if not self._check_win32():
            return None
        try:
            info = win32net.NetShareGetInfo(self._server, name, _SHARE_INFO_LEVEL)
            return {
                "server":       self.server_label,
                "name":         name,
                "path":         info.get("path", ""),
                "comment":      info.get("remark", ""),
                "max_uses":     info.get("max_uses", -1),
                "current_uses": info.get("current_uses", 0),
                "type":         info.get("type", 0),
                "permissions":  info.get("permissions", 0),
            }
        except pywintypes.error as e:
            self._log(f"get_share_info | {name} | {e.strerror}", "ERROR")
            return None

    def get_share_permissions(self, name: str) -> list[dict]:
        """Permisos SMB (share-level) de un share. Distintos a permisos NTFS."""
        if not self._check_win32():
            return []
        results = []
        try:
            info = win32net.NetShareGetInfo(self._server, name, _SHARE_INFO_LEVEL)
            sd = info.get("security_descriptor")
            if not sd:
                return results
            dacl = sd.GetSecurityDescriptorDacl()
            if not dacl:
                return results
            for i in range(dacl.GetAceCount()):
                (ace_type, _), mask, sid = dacl.GetAce(i)
                try:
                    account, domain, _ = win32security.LookupAccountSid(None, sid)
                    account_str = f"{domain}\\{account}" if domain else account
                except pywintypes.error:
                    account_str = str(sid)
                access_type = "Allow" if ace_type == 0 else "Deny"
                rights = ("Full Control" if mask & 0x1F01FF
                          else "Change" if mask & 0x1301BF
                          else "Read")
                results.append({
                    "server":      self.server_label,
                    "share":       name,
                    "account":     account_str,
                    "access_type": access_type,
                    "rights":      rights,
                    "mask_hex":    f"0x{mask:08X}",
                })
        except pywintypes.error as e:
            self._log(f"get_share_permissions | {name} | {e.strerror}", "ERROR")
        return results

    # ── Exportación ───────────────────────────────────────────────────────

    def export_shares(self, output_dir: str = ".") -> str:
        """
        Exporta config + permisos de todos los shares del servidor activo.
        Genera:
          shares_<server>_config_<ts>.csv
          shares_<server>_permissions_<ts>.csv
          shares_<server>_backup_<ts>.json
        """
        if not self._check_win32():
            return ""
        os.makedirs(output_dir, exist_ok=True)
        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        srv = (self._server or "local").replace("\\", "").replace("/", "")

        shares = self.list_shares(skip_admin=False)  # export incluye admin$
        if not shares:
            self._log("No se encontraron shares para exportar.", "WARN")
            return output_dir

        cfg_file = os.path.join(output_dir, f"shares_{srv}_config_{ts}.csv")
        with open(cfg_file, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["server", "name", "path", "comment", "type"])
            w.writeheader()
            w.writerows(shares)

        perm_file = os.path.join(output_dir, f"shares_{srv}_permissions_{ts}.csv")
        all_perms: list[dict] = []
        for s in shares:
            all_perms.extend(self.get_share_permissions(s["name"]))
        with open(perm_file, "w", newline="", encoding="utf-8-sig") as f:
            if all_perms:
                w = csv.DictWriter(f, fieldnames=list(all_perms[0].keys()))
                w.writeheader()
                w.writerows(all_perms)

        json_file = os.path.join(output_dir, f"shares_{srv}_backup_{ts}.json")
        backup = []
        for s in shares:
            detail = self.get_share_info(s["name"]) or {}
            detail["smb_permissions"] = self.get_share_permissions(s["name"])
            backup.append(detail)
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(backup, f, indent=2, ensure_ascii=False, default=str)

        self._log(
            f"Export [{srv}] completado: {len(shares)} shares → "
            f"{cfg_file} | {perm_file} | {json_file}"
        )
        return output_dir

    # ── Migración ─────────────────────────────────────────────────────────

    def update_share_path(self, name: str, new_path: str) -> bool:
        """
        Cambia la ruta de un share SIN eliminarlo (conserva permisos SMB).
        Requiere permisos de administrador en el servidor destino.
        """
        if not self._check_win32():
            return False
        if not os.path.isdir(new_path):
            self._log(f"update_share_path | Ruta no existe: {new_path}", "ERROR")
            return False
        try:
            info     = win32net.NetShareGetInfo(self._server, name, _SHARE_INFO_LEVEL)
            old_path = info.get("path", "?")
            info["path"] = new_path
            win32net.NetShareSetInfo(self._server, name, _SHARE_INFO_LEVEL, info)
            self._log(f"update_share_path | [{self.server_label}] '{name}' {old_path} → {new_path}")
            return True
        except pywintypes.error as e:
            self._log(
                f"update_share_path | [{self.server_label}] {name} | {e.strerror} ({e.winerror})",
                "ERROR"
            )
            return False

    def recreate_share(
        self, name: str, new_path: str,
        comment: str = "", max_uses: int = -1
    ) -> bool:
        """
        Elimina y recrea el share en la nueva ruta.
        ADVERTENCIA: los permisos SMB se resetean a Everyone/Read.
        """
        if not self._check_win32():
            return False
        if not os.path.isdir(new_path):
            self._log(f"recreate_share | Ruta no existe: {new_path}", "ERROR")
            return False
        old_info = self.get_share_info(name)
        try:
            win32net.NetShareDel(self._server, name)
        except pywintypes.error as e:
            self._log(f"recreate_share | Error al eliminar '{name}': {e.strerror}", "ERROR")
            return False
        new_info = {
            "netname":  name,
            "path":     new_path,
            "remark":   comment or (old_info.get("comment", "") if old_info else ""),
            "max_uses": max_uses if max_uses != -1
                        else (old_info.get("max_uses", -1) if old_info else -1),
            "type":     0,
        }
        try:
            win32net.NetShareAdd(self._server, 2, new_info)
            self._log(f"recreate_share | [{self.server_label}] '{name}' recreado en {new_path}")
            return True
        except pywintypes.error as e:
            self._log(f"recreate_share | Error al crear '{name}': {e.strerror}", "ERROR")
            return False

    def verify_share(self, name: str, expected_path: str) -> bool:
        """Confirma que el share apunta a la ruta esperada."""
        info = self.get_share_info(name)
        if not info:
            return False
        current  = info["path"].rstrip("\\").lower()
        expected = expected_path.rstrip("\\").lower()
        return current == expected

    def migrate_share(
        self, name: str, new_path: str, output_dir: str = "."
    ) -> bool:
        """
        Flujo completo para UN share en el servidor activo:
          1. Exporta backup de TODOS los shares del servidor
          2. Actualiza la ruta (sin perder permisos SMB)
          3. Verifica el cambio
        """
        if not self._check_win32():
            return False
        self._log(f"migrate_share | [{self.server_label}] '{name}' → '{new_path}'")
        self.export_shares(output_dir)
        ok = self.update_share_path(name, new_path)
        if not ok:
            return False
        return self.verify_share(name, new_path)
