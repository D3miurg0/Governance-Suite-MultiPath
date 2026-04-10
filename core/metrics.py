"""
Governance-Suite — Métricas de gobernanza
Calcula indicadores de salud y cumplimiento sobre los datos escaneados.
"""
from typing import List, Dict
from datetime import datetime, timedelta
from core.logger import get_logger

logger = get_logger("metrics")


def governance_score(items: List[Dict], permissions: List[Dict] = None) -> Dict:
    """
    Calcula un score de gobernanza (0-100) basado en:
    - Archivos muy antiguos (>3 años)
    - Archivos muy grandes (>500 MB)
    - Carpetas sin restricción de permisos (si se proveen)
    """
    if not items:
        return {"score": 0, "details": {}}

    total_files = sum(1 for i in items if not i.get("is_dir"))
    if total_files == 0:
        return {"score": 100, "details": {"message": "Sin archivos que evaluar"}}

    cutoff_old = datetime.now() - timedelta(days=1095)  # 3 años
    old_count = 0
    large_count = 0
    threshold_large = 500 * 1024 * 1024  # 500 MB

    for i in items:
        if i.get("is_dir"):
            continue
        try:
            mod = datetime.fromisoformat(i["modified"])
            if mod < cutoff_old:
                old_count += 1
        except (KeyError, ValueError):
            pass
        if i.get("size", 0) >= threshold_large:
            large_count += 1

    penalty_old = min((old_count / total_files) * 40, 40)
    penalty_large = min((large_count / total_files) * 20, 20)
    penalty_perms = 0

    if permissions:
        open_perms = sum(
            1 for p in permissions
            if p.get("account", "").lower() in ("everyone", "todos", "authenticated users")
        )
        penalty_perms = min((open_perms / max(len(permissions), 1)) * 40, 40)

    score = max(0, round(100 - penalty_old - penalty_large - penalty_perms))

    details = {
        "total_files": total_files,
        "old_files": old_count,
        "large_files": large_count,
        "open_permission_entries": open_perms if permissions else "N/A",
        "penalty_old": round(penalty_old, 1),
        "penalty_large": round(penalty_large, 1),
        "penalty_permissions": round(penalty_perms, 1),
    }

    logger.info(f"Governance score: {score}/100")
    return {"score": score, "details": details}
