"""
Governance-Suite — Comparación entre auditorías
Compara dos snapshots de permisos o escaneos para detectar cambios.
"""
from typing import List, Dict, Tuple
from core.logger import get_logger

logger = get_logger("comparison")


def compare_scans(
    baseline: List[Dict],
    current: List[Dict],
    key_field: str = "path",
) -> Dict:
    """
    Compara dos listas de items (escaneos o auditorías).
    Devuelve: added, removed, modified
    """
    base_map = {item[key_field]: item for item in baseline}
    curr_map = {item[key_field]: item for item in current}

    added = [curr_map[k] for k in curr_map if k not in base_map]
    removed = [base_map[k] for k in base_map if k not in curr_map]
    modified = []

    for k in base_map:
        if k in curr_map:
            old, new = base_map[k], curr_map[k]
            diffs = {
                field: (old.get(field), new.get(field))
                for field in set(old) | set(new)
                if old.get(field) != new.get(field)
            }
            if diffs:
                modified.append({"path": k, "changes": diffs})

    summary = {
        "added": len(added),
        "removed": len(removed),
        "modified": len(modified),
        "total_baseline": len(baseline),
        "total_current": len(current),
    }
    logger.info(f"Comparación: +{len(added)} añadidos, -{len(removed)} eliminados, ~{len(modified)} modificados")
    return {
        "summary": summary,
        "added": added,
        "removed": removed,
        "modified": modified,
    }


def compare_permissions(
    baseline: List[Dict],
    current: List[Dict],
) -> Dict:
    """Especializado para comparar auditorías de permisos."""
    # Clave compuesta: path + account
    def make_key(item):
        return f"{item.get('path')}|{item.get('account', item.get('owner', ''))}"

    base_keyed = [{**i, "_key": make_key(i)} for i in baseline]
    curr_keyed = [{**i, "_key": make_key(i)} for i in current]
    return compare_scans(base_keyed, curr_keyed, key_field="_key")
