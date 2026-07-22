"""
modules/share_manager.py
─────────────────────────────────────────────────────────────────────────────
Gestión de recursos compartidos SMB.

NetShareEnum niveles:
  Nivel 1 → dict con claves: netname, type, remark          (SIN path)
  Nivel 2 → dict con claves: netname, type, remark, path,
                               permissions, max_uses, current_uses,
                               passwd, security_descriptor       (CON path)

Siempre usar nivel 2 para tener la ruta.
Servidor local: pasar None a win32net, NO un string vacío.
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

_SHARE_INFO_LEVEL = 502   # usado solo en GetInfo/SetInfo
_ENUM_LEVEL       = 2     # DEBE ser 2 para obtener 'path' en NetShareEnum


class ShareManagerModule:

    def __init__(self, core=None, server: str = ""):
        self.core = core
        self._server: Optional[str] = server.strip() or None

    # ── Servidor ─────────────────────────────────────────────────────────

    def set_server(self, server: str):
        clean = (server or "").strip()
        self._server = clean if clean else None
        self._log(f"Servidor activo: {self.server_label}")

    @property
    def server_label(self) -> str:
        return self._server or "localhost"

    # ── Helpers ──────────────────────────────────────────────────────────

    def _check_win32(self) -> bool:
        if not WIN32_ENABLED:
            print("\u274c  pywin32 no disponible. Instalar: pip install pywin32")
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

    # ── Consulta ─────────────────────────────────────────────────────────

    def list_shares(self, skip_admin: bool = True) -> list[dict]:
        """
        Enumera shares del servidor con nivel 2 (incluye ruta).
        IPC$ siempre se excluye (no es un share de disco).
        Si skip_admin=True también omite los que terminan en $.
        """
        if not self._check_win32():
            return []
        shares = []
        try:
            resume = 0
            while True:
                # Nivel 2: devuelve dicts con 'netname','type','remark','path',...
                data, _total, resume = win32net.NetShareEnum(
                    self._server, _ENUM_LEVEL, resume, 65535
                )
                self._log(f"NetShareEnum devolvio {len(data)} entradas (resume={resume})")
                for s in data:
                    name = s.get("netname", "")
                    if name == "IPC$":
                        continue
                    if skip_admin and name.endswith("$"):
                        continue
                    shares.append({
                        "name":    name,
                        "path":    s.get("path", ""),
                        "comment": s.get("remark", ""),
                        "type":    s.get("type", 0),
                        "server":  self.server_label,
                    })
                if not resume:
                    break
        except pywintypes.error as e:
            self._log(
                f"list_shares [{self.server_label}] | code={e.winerror} | {e.strerror}",
                "ERROR"
            )
        return shares

    def get_share_info(self, name: str) -> Optional[dict]:
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
        if not self._check_win32():
            return []
        results = []
        try:
            info = win32net.NetShareGetInfo(self._server, name, _SHARE_INFO_LEVEL)
            sd   = info.get("security_descriptor")
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
                          else "Change"   if mask & 0x1301BF
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

    def get_active_sessions(self, share_name: str) -> list[dict]:
        """Retorna lista de sesiones activas que tienen archivos abiertos en el share."""
        if not self._check_win32():
            return []
        sessions = []
        try:
            data, _, _ = win32net.NetSessionEnum(self._server, None, None, 502)
            for s in data:
                if s.get('num_opens', 0) > 0:
                    sessions.append({
                        'user': s.get('username', ''),
                        'client': s.get('cname', ''),
                        'open_files': s.get('num_opens', 0),
                    })
        except pywintypes.error as e:
            self._log(f"get_active_sessions | {e.strerror}", "ERROR")
        return sessions

    # ── Exportación ──────────────────────────────────────────────────────

    def export_shares(self, output_dir: str = ".") -> str:
        if not self._check_win32():
            return ""
        os.makedirs(output_dir, exist_ok=True)
        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        srv = (self._server or "local").replace("\\\\", "").replace("/", "")

        shares = self.list_shares(skip_admin=False)
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
                w2 = csv.DictWriter(f, fieldnames=list(all_perms[0].keys()))
                w2.writeheader()
                w2.writerows(all_perms)

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
                f"update_share_path | [{self.server_label}] {name} | "
                f"{e.strerror} (code={e.winerror})",
                "ERROR"
            )
            return False

    def recreate_share(
        self, name: str, new_path: str,
        comment: str = "", max_uses: int = -1
    ) -> bool:
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
        info = self.get_share_info(name)
        if not info:
            return False
        current  = info["path"].rstrip("\\").lower()
        expected = expected_path.rstrip("\\").lower()
        return current == expected

    def migrate_share(
        self, name: str, new_path: str, output_dir: str = "."
    ) -> bool:
        if not self._check_win32():
            return False
        self._log(f"migrate_share | [{self.server_label}] '{name}' → '{new_path}'")
        self.export_shares(output_dir)
        ok = self.update_share_path(name, new_path)
        if not ok:
            return False
        return self.verify_share(name, new_path)
