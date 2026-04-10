"""
Governance-Suite — Menú principal CLI
"""
import sys
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    RICH = True
except ImportError:
    RICH = False

from config import APP_NAME, VERSION

console = Console() if RICH else None


def clear():
    import os
    os.system("cls" if sys.platform == "win32" else "clear")


def print_header():
    if RICH:
        console.print(Panel(
            f"[bold cyan]{APP_NAME} v{VERSION}[/bold cyan]\n"
            "[dim]Suite unificada para gestión, permisos y análisis de infraestructura[/dim]",
            border_style="cyan",
            expand=False,
        ))
    else:
        print(f"\n{'='*50}")
        print(f"  {APP_NAME} v{VERSION}")
        print(f"{'='*50}\n")


def prompt(msg: str, default: str = "") -> str:
    try:
        val = input(msg).strip()
        return val if val else default
    except (KeyboardInterrupt, EOFError):
        print("\n[Saliendo]")
        sys.exit(0)


def show_menu(title: str, options: list) -> str:
    """Muestra un menú numerado y devuelve la opción elegida."""
    if RICH:
        t = Table(show_header=False, box=None, padding=(0, 2))
        t.add_column("#", style="bold yellow", width=4)
        t.add_column("Opción", style="white")
        for i, (label, _) in enumerate(options, 1):
            t.add_row(str(i), label)
        t.add_row("0", "[dim]Volver / Salir[/dim]")
        console.print(f"\n[bold]{title}[/bold]")
        console.print(t)
    else:
        print(f"\n{title}")
        for i, (label, _) in enumerate(options, 1):
            print(f"  {i}. {label}")
        print("  0. Volver / Salir")

    return prompt("\nElige una opción: ", "0")


class MainMenu:
    def run(self):
        while True:
            clear()
            print_header()
            options = [
                ("Escaneo de servidores",    self._scan),
                ("Migración de archivos",    self._migration),
                ("Auditoría de permisos",   self._permissions),
                ("Análisis y métricas",     self._analysis),
                ("Reportes y exportación",   self._reports),
            ]
            choice = show_menu("Menú principal", options)
            if choice == "0":
                print("\nHasta luego.\n")
                sys.exit(0)
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(options):
                    options[idx][1]()
            except (ValueError, IndexError):
                pass

    def _scan(self):
        from cli.menu_scan import ScanMenu
        ScanMenu().run()

    def _migration(self):
        from cli.menu_migration import MigrationMenu
        MigrationMenu().run()

    def _permissions(self):
        from cli.menu_permissions import PermissionsMenu
        PermissionsMenu().run()

    def _analysis(self):
        from cli.menu_analysis import AnalysisMenu
        AnalysisMenu().run()

    def _reports(self):
        from cli.menu_reports import ReportsMenu
        ReportsMenu().run()
