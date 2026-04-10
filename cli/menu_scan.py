"""
Governance-Suite — Menú CLI: Escaneo de servidores
"""
from cli.menu_main import show_menu, prompt, clear, console, RICH
from core.scanner import scan_directory, scan_multiple
from core.exporter import auto_export


class ScanMenu:
    def __init__(self):
        self.last_results = {}

    def run(self):
        while True:
            clear()
            options = [
                ("Escanear una ruta",           self._single_scan),
                ("Escanear múltiples rutas",   self._multi_scan),
                ("Ver últimos resultados",      self._show_last),
                ("Exportar resultados",          self._export),
            ]
            choice = show_menu("Escaneo de servidores", options)
            if choice == "0":
                return
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(options):
                    options[idx][1]()
            except (ValueError, IndexError):
                pass

    def _single_scan(self):
        path = prompt("Ruta a escanear: ")
        recursive = prompt("\u00bfRecursivo? (s/n) [s]: ", "s").lower() == "s"
        ext_input = prompt("Extensiones a filtrar (ej: .pdf .docx) o Enter para todas: ")
        extensions = ext_input.split() if ext_input else None
        if RICH:
            console.print(f"[cyan]Escaneando {path}...[/cyan]")
        else:
            print(f"Escaneando {path}...")
        results = list(scan_directory(path, recursive=recursive, extensions=extensions))
        self.last_results = {path: results}
        msg = f"Encontrados {len(results)} elementos"
        if RICH:
            console.print(f"[green]{msg}[/green]")
        else:
            print(msg)
        prompt("\nPresiona Enter para continuar...")

    def _multi_scan(self):
        raw = prompt("Rutas separadas por coma: ")
        paths = [p.strip() for p in raw.split(",") if p.strip()]
        if not paths:
            return
        results = scan_multiple(paths)
        self.last_results = results
        for p, items in results.items():
            print(f"  {p}: {len(items)} elementos")
        prompt("\nPresiona Enter para continuar...")

    def _show_last(self):
        if not self.last_results:
            print("No hay resultados previos.")
            prompt("Enter para continuar...")
            return
        for path, items in self.last_results.items():
            print(f"\n{path}: {len(items)} elementos")
            dirs = sum(1 for i in items if i["is_dir"])
            files = len(items) - dirs
            total_mb = sum(i["size"] for i in items if not i["is_dir"]) / 1024 / 1024
            print(f"  Directorios: {dirs}  Archivos: {files}  Total: {total_mb:.2f} MB")
        prompt("\nEnter para continuar...")

    def _export(self):
        if not self.last_results:
            print("No hay resultados que exportar.")
            prompt("Enter para continuar...")
            return
        fmt = prompt("Formato (csv/json/excel) [csv]: ", "csv")
        all_items = [item for items in self.last_results.values() for item in items]
        path = auto_export(all_items, "scan", fmt)
        print(f"Exportado: {path}")
        prompt("\nEnter para continuar...")
