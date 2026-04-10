"""
Governance-Suite — Auditoría de permisos NTFS
Lee y procesa ACLs de directorios en Windows (requiere win32security)
o permisos POSIX en Linux.
"""
import os
import sys
import stat
from pathlib import Path
from typing import List, Dict, Optional
from core.logger import get_logger

logger = get_logger("permission")

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    try:
        import win32security
        import ntsecuritycon as con
        WIN32_AVAILABLE = True
    except ImportError:
        WIN32_AVAILABLE = False
        logger.warning("pywin32 no disponible — usando modo compatibilidad")
else:
    WIN32_AVAILABLE = False


def get_permissions_posix(path: str) -> Dict:
    """Obtiene permisos POSIX de un archivo/directorio."""
    p = Path(path)
    s = p.stat()
    mode = s.st_mode
    return {
        "path": str(p),
        "owner": s.st_uid,
        "group": s.st_gid,
        "permissions_octal": oct(mode)[-3:],
        "readable": os.access(path, os.R_OK),
        "writable": os.access(path, os.W_OK),
        "executable": os.access(path, os.X_OK),
        "is_dir": p.is_dir(),
    }


def get_permissions_ntfs(path: str) -> List[Dict]:
    """Obtiene ACL NTFS de un directorio (solo Windows con pywin32)."""
    if not WIN32_AVAILABLE:
        logger.warning("pywin32 no disponible, usando POSIX fallback")
        return [get_permissions_posix(path)]

    results = []
    try:
        sd = win32security.GetFileSecurity(
            path, win32security.DACL_SECURITY_INFORMATION
        )
        dacl = sd.GetSecurityDescriptorDacl()
        if dacl is None:
            return results
        for i in range(dacl.GetAceCount()):
            ace = dacl.GetAce(i)
            ace_type, ace_flags = ace[0]
            mask = ace[1]
            sid = ace[2]
            try:
                name, domain, _ = win32security.LookupAccountSid(None, sid)
                account = f"{domain}\\{name}"
            except Exception:
                account = str(sid)
            results.append({
                "path": path,
                "account": account,
                "mask": mask,
                "ace_type": ace_type,
                "ace_flags": ace_flags,
                "read": bool(mask & con.FILE_GENERIC_READ),
                "write": bool(mask & con.FILE_GENERIC_WRITE),
                "execute": bool(mask & con.FILE_GENERIC_EXECUTE),
                "full_control": bool(mask & con.FILE_ALL_ACCESS),
            })
    except Exception as e:
        logger.error(f"Error leyendo ACL de {path}: {e}")
    return results


def audit_path(
    path: str,
    recursive: bool = False,
    include_files: bool = False,
) -> List[Dict]:
    """Audita permisos de una ruta completa."""
    results = []
    root = Path(path)
    targets = root.rglob("*") if recursive else [root]

    for item in targets:
        if not include_files and not item.is_dir():
            continue
        try:
            if IS_WINDOWS and WIN32_AVAILABLE:
                entries = get_permissions_ntfs(str(item))
            else:
                entries = [get_permissions_posix(str(item))]
            results.extend(entries)
        except (PermissionError, OSError) as e:
            logger.warning(f"Sin acceso a {item}: {e}")

    logger.info(f"Auditoría completada: {path} — {len(results)} entradas")
    return results
