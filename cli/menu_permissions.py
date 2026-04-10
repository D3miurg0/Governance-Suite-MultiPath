"""
Governance-Suite — Menú CLI: Auditoría de permisos
"""
from cli.menu_main import show_menu, prompt, clear
from core.permission import audit_path
from core.exporter import auto_export


class PermissionsMenu:
    def __init__(self):
        self.last_results = []

    def run(self):
        while True:
            clear()
            options = [
                ("Auditar ruta",                self._audit),
                ("Ver últimos resultados",      self._show_last),
                ("Exportar resultados",          self._export),
            ]
            choice = show_menu("Auditoría de permisos", options)
            if choice == "0":
                return
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(options):
                    options[idx][1]()
            except (ValueError, IndexError):
                pass

    def _audit(self):
        path = prompt("Ruta a auditar: ")
        recursive = prompt("\u00bfRecursivo? (s/n) [s]: ", "s").lower() == "s"
        include_files = prompt("\u00bfIncluir archivos? (s/n) [n]: ", "n").lower() == "s"
        print(f"Auditando {path}...")
        results = audit_path(path, recursive=recursive, include_files=include_files)
        self.last_results = results
        print(f"Auditados {len(results)} entradas de permisos.")
        prompt("\nEnter para continuar...")

    def _show_last(self):
        if not self.last_results:
            print("Sin resultados previos.")
            prompt("Enter para continuar...")
            return
        for r in self.last_results[:20]:
            account = r.get("account", r.get("owner", "N/A"))
            path = r.get("path", "")
            print(f"  {path} — {account}")
        prompt("\nEnter para continuar...")

    def _export(self):
        if not self.last_results:
            print("Sin resultados que exportar.")
            prompt("Enter para continuar...")
            return
        fmt = prompt("Formato (csv/json/excel) [csv]: ", "csv")
        path = auto_export(self.last_results, "permissions", fmt)
        print(f"Exportado: {path}")
        prompt("\nEnter para continuar...")
