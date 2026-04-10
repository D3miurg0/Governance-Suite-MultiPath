"""
Governance-Suite — Análisis global multi-servidor
Agrega y correlaciona resultados de múltiples escaneos.
"""
from typing import Dict, List
from core.analysis import summarize_scan, detect_large_files
from core.logger import get_logger

logger = get_logger("global_analysis")


def aggregate_scans(scan_results: Dict[str, List[Dict]]) -> Dict:
    """
    Recibe un dict {server_path: [items]} y genera un resumen global.
    """
    global_summary = {
        "servers": {},
        "totals": {
            "files": 0,
            "dirs": 0,
            "size_mb": 0.0,
        },
        "top_large_files": [],
    }

    all_large = []

    for server, items in scan_results.items():
        summary = summarize_scan(items)
        global_summary["servers"][server] = summary
        global_summary["totals"]["files"] += summary["total_files"]
        global_summary["totals"]["dirs"] += summary["total_dirs"]
        global_summary["totals"]["size_mb"] += summary["total_size_mb"]
        large = detect_large_files(items)
        for f in large:
            f["_server"] = server
        all_large.extend(large)

    all_large.sort(key=lambda x: x.get("size", 0), reverse=True)
    global_summary["top_large_files"] = all_large[:20]

    logger.info(
        f"Análisis global: {len(scan_results)} servidores, "
        f"{global_summary['totals']['files']} archivos totales"
    )
    return global_summary


def rank_servers_by_size(scan_results: Dict[str, List[Dict]]) -> List[Dict]:
    """Clasifica servidores por tamaño total de datos."""
    ranking = []
    for server, items in scan_results.items():
        s = summarize_scan(items)
        ranking.append({"server": server, **s})
    return sorted(ranking, key=lambda x: x["total_size_mb"], reverse=True)
