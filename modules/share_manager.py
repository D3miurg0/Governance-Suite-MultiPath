"""
modules/share_manager.py
─────────────────────────────────────────────────────────────────────────────
Gestión de recursos compartidos SMB (shares) en Windows.
Permite exportar, migrar, actualizar ruta y recrear shares conservando
sus permisos SMB, lo cual es el paso complementario a la migración de
archivos con preservación de permisos NTFS.

Flujo típico de migración ReFS → NTFS:
  1. export_shares()          — respalda config + permisos de todos los shares
  2. (Robocopy / MigrationModule copia datos y ACLs NTFS)
  3. update_share_path()      — redirige el share a la nueva ruta sin eliminarlo
  4. verify_share()           — confirma que el share apunta a la ruta correcta
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


# Nivel de info para NetShareGetInfo / NetShareSetInfo
_SHARE_INFO_LEVEL = 502   # Incluye path, remark, permissions, max_uses, security

# Permisos SMB estándar (ACCESS_* de win32netcon)
_SMB_ACCESS_MAP = {
    win32netcon.ACCESS_READ:    "Read",
    win32netcon.ACCESS_WRITE:   "Change",
    win32netcon.ACCESS_CREATE:  "Change",
    win32netcon.ACCESS_EXEC:    "Read",
    win32netcon.ACCESS_DELETE:  "Change",
    win32netcon.ACCESS_ATRIB:   "Read",
    win32netcon.ACCESS_PERM:    "Full Control",
    win32netcon.ACCESS_ALL:     "Full Control",
} if WIN32_ENABLED else {}


class ShareManagerModule:
    """
    Módulo de gestión de shares SMB.

    Operaciones disponibles
    ────────────────────────
    list_shares()                         — lista todos los shares del servidor
    get_share_info(name)                  — detalle completo de un share
    get_share_permissions(name)           — lista ACEs del share (SMB level)
    export_shares(output_dir)             — exporta config + permisos a CSV/JSON
    update_share_path(name, new_path)     — cambia la ruta sin eliminar el share
    recreate_share(name, new_path, ...)   — elimina y recrea el share en nueva ruta
    verify_share(name, expected_path)     — valida que el share apunta a la ruta
    migrate_share(name, new_path)         — flujo completo: export → update → verify
    """

    def __init__(self, core=None):
        self.core = core
        self._server = None   # None = servidor local

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
                self.core.log_audit("SHARE", {"msg": msg, "level": level})

    # ──────────────────────────────────────────────────────────────────────
    # Consulta
    # ──────────────────────────────────────────────────────────────────────

    def list_shares(self) -> list[dict]:
        """
        Retorna todos los shares del servidor local.
        Equivalente a: Get-SmbShare | Select-Object Name, Path
        """
        if not self._check_win32():
            return []
        shares = []
        try:
            resume = 0
            while True:
                data, total, resume = win32net.NetShareEnum(self._server, 1, resume, 32768)
                for s in data:
                    shares.append({
                        "name":    s["netname"],
                        "path":    s["path"],
                        "comment": s.get("remark", ""),
                        "type":    s["type"],
                    })
                if not resume:
                    break
        except pywintypes.error as e:
            self._log(f"list_shares | {e.strerror}", "ERROR")
        return shares

    def get_share_info(self, name: str) -> Optional[dict]:
        """
        Retorna información detallada (nivel 502) de un share.
        Incluye path, remark, max_uses, current_uses, security descriptor.
        """
        if not self._check_win32():
            return None
        try:
            info = win32net.NetShareGetInfo(self._server, name, _SHARE_INFO_LEVEL)
            return {
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
        """
        Obtiene los permisos SMB (share-level) de un share.
        Nota: estos son distintos a los permisos NTFS de la carpeta.
        Retorna lista de dicts: {account, access_type, rights}
        """
        if not self._check_win32():
            return []
        results = []
        try:
            # Nivel 502 incluye security descriptor
            info = win32net.NetShareGetInfo(self._server, name, _SHARE_INFO_LEVEL)
            sd = info.get("security_descriptor")
            if not sd:
                self._log(f"No hay security descriptor en share '{name}'", "WARN")
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
                rights = "Full Control" if mask & 0x1F01FF else (
                    "Change" if mask & 0x1301BF else "Read"
                )
                results.append({
                    "share":       name,
                    "account":     account_str,
                    "access_type": access_type,
                    "rights":      rights,
                    "mask_hex":    f"0x{mask:08X}",
                })
        except pywintypes.error as e:
            self._log(f"get_share_permissions | {name} | {e.strerror}", "ERROR")
        return results

    # ──────────────────────────────────────────────────────────────────────
    # Exportación
    # ──────────────────────────────────────────────────────────────────────

    def export_shares(self, output_dir: str = ".") -> str:
        """
        Exporta la configuración de todos los shares a:
          - shares_config_<timestamp>.csv   (nombre, ruta, comentario, tipo)
          - shares_permissions_<timestamp>.csv (permisos SMB por share)
          - shares_backup_<timestamp>.json   (todo en un solo JSON para restaurar)

        Retorna la ruta del directorio de salida.
        """
        if not self._check_win32():
            return ""

        os.makedirs(output_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        shares = self.list_shares()
        if not shares:
            self._log("No se encontraron shares para exportar.", "WARN")
            return output_dir

        # CSV configuración
        cfg_file = os.path.join(output_dir, f"shares_config_{ts}.csv")
        with open(cfg_file, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["name", "path", "comment", "type"])
            w.writeheader()
            w.writerows(shares)

        # CSV permisos
        perm_file = os.path.join(output_dir, f"shares_permissions_{ts}.csv")
        all_perms = []
        for s in shares:
            all_perms.extend(self.get_share_permissions(s["name"]))
        with open(perm_file, "w", newline="", encoding="utf-8-sig") as f:
            if all_perms:
                w = csv.DictWriter(f, fieldnames=all_perms[0].keys())
                w.writeheader()
                w.writerows(all_perms)

        # JSON completo
        json_file = os.path.join(output_dir, f"shares_backup_{ts}.json")
        backup = []
        for s in shares:
            detail = self.get_share_info(s["name"]) or {}
            detail["smb_permissions"] = self.get_share_permissions(s["name"])
            backup.append(detail)
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(backup, f, indent=2, ensure_ascii=False, default=str)

        self._log(
            f"Export completado: {len(shares)} shares → {cfg_file} | {perm_file} | {json_file}"
        )
        print(f"✅  Backup generado en: {output_dir}")
        print(f"   Config:     {cfg_file}")
        print(f"   Permisos:   {perm_file}")
        print(f"   JSON full:  {json_file}")
        return output_dir

    # ──────────────────────────────────────────────────────────────────────
    # Migración de ruta
    # ──────────────────────────────────────────────────────────────────────

    def update_share_path(self, name: str, new_path: str) -> bool:
        """
        Actualiza la ruta de un share SMB existente SIN eliminarlo.
        Conserva todos los permisos SMB, comentario, max_uses, etc.

        Equivale a modificar la ruta en 'Computer Management > Shared Folders'
        sin tocar ninguna otra configuración.

        Requiere ejecutar como Administrador.
        """
        if not self._check_win32():
            return False

        if not os.path.isdir(new_path):
            self._log(f"update_share_path | La ruta destino no existe: {new_path}", "ERROR")
            print(f"❌  La ruta destino no existe: {new_path}")
            return False

        try:
            info = win32net.NetShareGetInfo(self._server, name, _SHARE_INFO_LEVEL)
            old_path = info.get("path", "(desconocida)")
            info["path"] = new_path
            win32net.NetShareSetInfo(self._server, name, _SHARE_INFO_LEVEL, info)

            self._log(
                f"update_share_path | '{name}' | {old_path} → {new_path}"
            )
            print(f"✅  Share '{name}' actualizado: {old_path} → {new_path}")
            return True
        except pywintypes.error as e:
            self._log(
                f"update_share_path | {name} | {e.strerror} (error {e.winerror})",
                "ERROR"
            )
            if e.winerror == 5:
                print("❌  Acceso denegado. Ejecutar como Administrador.")
            else:
                print(f"❌  Error al actualizar share: {e.strerror}")
            return False

    def recreate_share(
        self,
        name: str,
        new_path: str,
        comment: str = "",
        max_uses: int = -1,
    ) -> bool:
        """
        Elimina el share y lo recrea en la nueva ruta.
        Útil cuando update_share_path falla o cuando se necesita un recreo limpio.

        ADVERTENCIA: los permisos SMB se pierden a menos que se hayan exportado
        previamente con export_shares(). Se asigna Everyone/Read por defecto.
        Ajustar permisos SMB manualmente después si se requiere.
        """
        if not self._check_win32():
            return False

        if not os.path.isdir(new_path):
            self._log(f"recreate_share | La ruta no existe: {new_path}", "ERROR")
            print(f"❌  La ruta destino no existe: {new_path}")
            return False

        # Respaldar info antes de eliminar
        old_info = self.get_share_info(name)

        try:
            win32net.NetShareDel(self._server, name)
            self._log(f"recreate_share | '{name}' eliminado")
        except pywintypes.error as e:
            self._log(f"recreate_share | Error al eliminar '{name}': {e.strerror}", "ERROR")
            print(f"❌  No se pudo eliminar el share: {e.strerror}")
            return False

        new_info = {
            "netname":  name,
            "path":     new_path,
            "remark":   comment or (old_info.get("comment", "") if old_info else ""),
            "max_uses": max_uses if max_uses != -1 else (old_info.get("max_uses", -1) if old_info else -1),
            "type":     0,  # STYPE_DISKTREE
        }

        try:
            win32net.NetShareAdd(self._server, 2, new_info)
            self._log(f"recreate_share | '{name}' recreado en {new_path}")
            print(f"✅  Share '{name}' recreado en: {new_path}")
            print("⚠️   Revisar y reaplicar permisos SMB si es necesario.")
            return True
        except pywintypes.error as e:
            self._log(
                f"recreate_share | Error al crear '{name}': {e.strerror}",
                "ERROR"
            )
            print(f"❌  Error al recrear share: {e.strerror}")
            return False

    # ──────────────────────────────────────────────────────────────────────
    # Verificación y flujo completo
    # ──────────────────────────────────────────────────────────────────────

    def verify_share(self, name: str, expected_path: str) -> bool:
        """
        Confirma que el share apunta a la ruta esperada.
        Retorna True si coincide, False en caso contrario.
        """
        info = self.get_share_info(name)
        if not info:
            print(f"❌  Share '{name}' no encontrado.")
            return False

        current = info["path"].rstrip("\\").lower()
        expected = expected_path.rstrip("\\").lower()
        match = current == expected

        if match:
            print(f"✅  Verificación OK: '{name}' → {info['path']}")
        else:
            print(f"❌  Verificación FALLA: '{name}' apunta a '{info['path']}' (esperado: '{expected_path}')")
        return match

    def migrate_share(self, name: str, new_path: str, output_dir: str = ".") -> bool:
        """
        Flujo completo de migración de un share a nueva ruta:
          1. Exporta backup completo del share
          2. Actualiza la ruta (NetShareSetInfo — no pierde permisos SMB)
          3. Verifica que el cambio se aplicó correctamente

        Este método NO copia archivos. La copia de datos y ACLs NTFS debe
        hacerse previamente con MigrationModule.

        Retorna True si todos los pasos fueron exitosos.
        """
        if not self._check_win32():
            return False

        print(f"\n{'='*60}")
        print(f"  Migración de share: {name}")
        print(f"  Nueva ruta: {new_path}")
        print(f"{'='*60}")

        # Paso 1: Backup
        print("\n[1/3] Exportando backup del share...")
        self.export_shares(output_dir)

        # Paso 2: Actualizar ruta
        print("\n[2/3] Actualizando ruta del share...")
        ok = self.update_share_path(name, new_path)
        if not ok:
            print("\n❌  Migración abortada en paso 2.")
            return False

        # Paso 3: Verificar
        print("\n[3/3] Verificando...")
        result = self.verify_share(name, new_path)

        if result:
            print(f"\n✅  Migración completada. Share '{name}' operativo en {new_path}")
        else:
            print(f"\n⚠️   La ruta fue actualizada pero la verificación detectó diferencias.")

        return result
