"""
Governance-Suite — Menú CLI: Reportes y exportación
"""
import os
from cli.menu_main import show_menu, prompt, clear
from config import OUTPUT_DIR, LOGS_DIR


class ReportsMenu:
    def run(self):
        while True:
            clear()
            options = [
                ("Ver archivos exportados",     self._list_output),
                ("Ver logs de sesión",          self._list_logs),
                ("Abrir carpeta de salida",     self._open_output),
            ]
            choice = show_menu("Reportes y exportación", options)
            if choice == "0":
                return
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(options):
                    options[idx][1]()
            except (ValueError, IndexError):
                pass

    def _list_output(self):
        files = sorted(OUTPUT_DIR.glob("*")) if OUTPUT_DIR.exists() else []
        if not files:
            print("No hay archivos exportados aún.")
        else:
            print(f"\nArchivos en {OUTPUT_DIR}:")
            for f in files:
                size = f.stat().st_size / 1024
                print(f"  {f.name} ({size:.1f} KB)")
        prompt("\nEnter para continuar...")

    def _list_logs(self):
        files = sorted(LOGS_DIR.glob("*.log"), reverse=True) if LOGS_DIR.exists() else []
        if not files:
            print("No hay logs de sesión aún.")
        else:
            print(f"\nLogs en {LOGS_DIR}:")
            for f in files[:10]:
                print(f"  {f.name}")
        prompt("\nEnter para continuar...")

    def _open_output(self):
        import sys
        if sys.platform == "win32":
            os.startfile(str(OUTPUT_DIR))
        elif sys.platform == "darwin":
            os.system(f"open {OUTPUT_DIR}")
        else:
            os.system(f"xdg-open {OUTPUT_DIR}")
        prompt("\nEnter para continuar...")
