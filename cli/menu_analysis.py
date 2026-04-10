"""
Governance-Suite — Menú CLI: Análisis y métricas
"""
from cli.menu_main import show_menu, prompt, clear, console, RICH
from core.analysis import summarize_scan, detect_large_files, detect_old_files, detect_duplicates
from core.metrics import governance_score
from core.scanner import scan_directory
from core.exporter import auto_export


class AnalysisMenu:
    def __init__(self):
        self.last_items = []

    def run(self):
        while True:
            clear()
            options = [
                ("Escanear y analizar ruta",    self._scan_and_analyze),
                ("Detectar archivos grandes",   self._large_files),
                ("Detectar archivos antiguos",  self._old_files),
                ("Detectar posibles duplicados",self._duplicates),
                ("Governance Score",             self._score),
                ("Exportar análisis",            self._export),
            ]
            choice = show_menu("Análisis y métricas", options)
            if choice == "0":
                return
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(options):
                    options[idx][1]()
            except (ValueError, IndexError):
                pass

    def _scan_and_analyze(self):
        path = prompt("Ruta a analizar: ")
        self.last_items = list(scan_directory(path))
        summary = summarize_scan(self.last_items)
        print(f"\nResumen de {path}:")
        for k, v in summary.items():
            print(f"  {k}: {v}")
        prompt("\nEnter para continuar...")

    def _large_files(self):
        if not self.last_items:
            print("Primero escanea una ruta (opción 1).")
            prompt("Enter...")
            return
        threshold = float(prompt("Umbral en MB [100]: ", "100"))
        large = detect_large_files(self.last_items, threshold)
        print(f"\nArchivos > {threshold} MB: {len(large)}")
        for f in large[:15]:
            print(f"  {f['path']} — {round(f['size']/1024/1024, 1)} MB")
        prompt("\nEnter para continuar...")

    def _old_files(self):
        if not self.last_items:
            print("Primero escanea una ruta (opción 1).")
            prompt("Enter...")
            return
        days = int(prompt("Archivos no modificados en días [365]: ", "365"))
        old = detect_old_files(self.last_items, days)
        print(f"\nArchivos con más de {days} días sin modificar: {len(old)}")
        for f in old[:10]:
            print(f"  {f['path']} — {f['modified']}")
        prompt("\nEnter para continuar...")

    def _duplicates(self):
        if not self.last_items:
            print("Primero escanea una ruta (opción 1).")
            prompt("Enter...")
            return
        dupes = detect_duplicates(self.last_items)
        print(f"\nPosibles duplicados (mismo nombre): {len(dupes)} grupos")
        for name, files in list(dupes.items())[:10]:
            print(f"  {name}: {len(files)} copias")
        prompt("\nEnter para continuar...")

    def _score(self):
        if not self.last_items:
            print("Primero escanea una ruta (opción 1).")
            prompt("Enter...")
            return
        result = governance_score(self.last_items)
        score = result["score"]
        if RICH:
            color = "green" if score >= 70 else ("yellow" if score >= 40 else "red")
            console.print(f"\n[bold {color}]Governance Score: {score}/100[/bold {color}]")
        else:
            print(f"\nGovernance Score: {score}/100")
        for k, v in result["details"].items():
            print(f"  {k}: {v}")
        prompt("\nEnter para continuar...")

    def _export(self):
        if not self.last_items:
            print("Sin datos que exportar.")
            prompt("Enter...")
            return
        fmt = prompt("Formato (csv/json/excel) [csv]: ", "csv")
        path = auto_export(self.last_items, "analysis", fmt)
        print(f"Exportado: {path}")
        prompt("\nEnter para continuar...")
