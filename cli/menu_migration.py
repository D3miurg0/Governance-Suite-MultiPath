"""
Governance-Suite — Menú CLI: Migración de archivos
"""
from cli.menu_main import show_menu, prompt, clear, console, RICH
from core.migration import migrate_directory
from core.exporter import auto_export


class MigrationMenu:
    def __init__(self):
        self.last_results = []

    def run(self):
        while True:
            clear()
            options = [
                ("Migrar directorio",           self._migrate),
                ("Ver último reporte",          self._show_last),
                ("Exportar reporte",             self._export),
            ]
            choice = show_menu("Migración de archivos", options)
            if choice == "0":
                return
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(options):
                    options[idx][1]()
            except (ValueError, IndexError):
                pass

    def _migrate(self):
        src = prompt("Directorio origen: ")
        dst = prompt("Directorio destino: ")
        verify = prompt("\u00bfVerificar integridad (checksum)? (s/n) [s]: ", "s").lower() == "s"
        overwrite = prompt("\u00bfSobrescribir existentes? (s/n) [n]: ", "n").lower() == "s"
        ext_input = prompt("Extensiones a migrar (ej: .pdf .docx) o Enter para todas: ")
        extensions = ext_input.split() if ext_input else None

        completed = [0]

        def progress(done, total, r):
            completed[0] = done
            status = r.get("status", "?")
            if RICH:
                console.print(f"[dim]{done}/{total}[/dim] {r.get('src', '')} — [{status}]")
            else:
                print(f"{done}/{total}: {r.get('src', '')} [{status}]")

        results = migrate_directory(
            src, dst,
            extensions=extensions,
            verify=verify,
            overwrite=overwrite,
            progress_callback=progress,
        )
        self.last_results = results
        ok = sum(1 for r in results if r["status"] == "ok")
        print(f"\nMigración completa: {ok}/{len(results)} archivos procesados.")
        prompt("\nEnter para continuar...")

    def _show_last(self):
        if not self.last_results:
            print("Sin resultados previos.")
            prompt("Enter para continuar...")
            return
        for r in self.last_results[:20]:
            print(f"  [{r['status']}] {r['src']}")
        if len(self.last_results) > 20:
            print(f"  ... y {len(self.last_results) - 20} más")
        prompt("\nEnter para continuar...")

    def _export(self):
        if not self.last_results:
            print("Sin resultados que exportar.")
            prompt("Enter para continuar...")
            return
        fmt = prompt("Formato (csv/json/excel) [csv]: ", "csv")
        path = auto_export(self.last_results, "migration", fmt)
        print(f"Exportado: {path}")
        prompt("\nEnter para continuar...")
