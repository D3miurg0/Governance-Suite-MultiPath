"""
Governance-Suite — Análisis de datos y métricas por servidor/ruta
"""
from typing import List, Dict, Optional
from collections import Counter
from datetime import datetime, timedelta
from core.logger import get_logger

logger = get_logger("analysis")


def summarize_scan(items: List[Dict]) -> Dict:
    """Genera resumen estadístico de un escaneo."""
    files = [i for i in items if not i.get("is_dir")]
    dirs = [i for i in items if i.get("is_dir")]
    total_size = sum(f.get("size", 0) for f in files)
    extensions = Counter(f.get("extension", "") for f in files)
    return {
        "total_files": len(files),
        "total_dirs": len(dirs),
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "extensions": dict(extensions.most_common(20)),
        "avg_file_size_kb": round((total_size / len(files) / 1024), 2) if files else 0,
    }


def detect_large_files(items: List[Dict], threshold_mb: float = 100.0) -> List[Dict]:
    """Detecta archivos que superan el umbral de tamaño."""
    threshold = threshold_mb * 1024 * 1024
    large = [
        i for i in items
        if not i.get("is_dir") and i.get("size", 0) >= threshold
    ]
    return sorted(large, key=lambda x: x["size"], reverse=True)


def detect_old_files(items: List[Dict], days: int = 365) -> List[Dict]:
    """Detecta archivos no modificados en más de N días."""
    cutoff = datetime.now() - timedelta(days=days)
    old = []
    for i in items:
        if i.get("is_dir"):
            continue
        try:
            mod = datetime.fromisoformat(i["modified"])
            if mod < cutoff:
                old.append(i)
        except (KeyError, ValueError):
            pass
    return sorted(old, key=lambda x: x["modified"])


def detect_duplicates(items: List[Dict]) -> Dict[str, List[Dict]]:
    """Agrupa archivos con el mismo nombre (posibles duplicados)."""
    from collections import defaultdict
    groups = defaultdict(list)
    for i in items:
        if not i.get("is_dir"):
            groups[i["name"]].append(i)
    return {k: v for k, v in groups.items() if len(v) > 1}


def top_directories_by_size(items: List[Dict], top_n: int = 10) -> List[Dict]:
    """Calcula el tamaño acumulado por directorio padre."""
    from collections import defaultdict
    from pathlib import Path
    sizes = defaultdict(int)
    for i in items:
        if not i.get("is_dir"):
            parent = str(Path(i["path"]).parent)
            sizes[parent] += i.get("size", 0)
    sorted_dirs = sorted(sizes.items(), key=lambda x: x[1], reverse=True)
    return [
        {"directory": d, "size_mb": round(s / 1024 / 1024, 2)}
        for d, s in sorted_dirs[:top_n]
    ]
