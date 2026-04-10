import os
import sys
from config import Config
from core.audit import AuditCore
from core.language import LANG

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLORS = True
except ImportError:
    COLORS = False
    class Fore:
        CYAN = GREEN = YELLOW = RED = MAGENTA = WHITE = ""
    class Style:
        BRIGHT = RESET_ALL = ""


def header(title: str):
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"{Fore.CYAN}{Style.BRIGHT}" + "=" * 60)
    print(f"  {Config.APP_NAME} v{Config.VERSION}  —  {title}")
    print("=" * 60 + Style.RESET_ALL)


def input_path(prompt: str) -> str:
    val = input(f"{Fore.YELLOW}  {prompt}: {Style.RESET_ALL}").strip().strip('"')
    return val


def pause():
    input(f"\n{Fore.WHITE}  Presione ENTER para continuar...{Style.RESET_ALL}")


class MainMenu:
    """Menú principal del CLI de Governance-Suite."""

    def __init__(self):
        self.core = AuditCore()
        self.core.create_session_folder()

    def run(self):
        while True:
            header("Menú Principal")
            print(f"{Fore.GREEN}")
            print("  [1]  Escaneo de Archivos")
            print("  [2]  Migración de Archivos")
            print("  [3]  Auditoría de Permisos NTFS")
            print("  [4]  Análisis y Dashboard Excel")
            print("  [5]  Reportes y Exportación")
            print(f"{Fore.RED}")
            print("  [0]  Salir")
            print(Style.RESET_ALL)
            opt = input(f"{Fore.CYAN}  Opción: {Style.RESET_ALL}").strip()

            if opt == "1":
                from cli.menu_scan import ScanMenu
                ScanMenu(self.core).run()
            elif opt == "2":
                from cli.menu_migration import MigrationMenu
                MigrationMenu(self.core).run()
            elif opt == "3":
                from cli.menu_permissions import PermissionsMenu
                PermissionsMenu(self.core).run()
            elif opt == "4":
                from cli.menu_analysis import AnalysisMenu
                AnalysisMenu(self.core).run()
            elif opt == "5":
                from cli.menu_reports import ReportsMenu
                ReportsMenu(self.core).run()
            elif opt == "0":
                print(f"\n{Fore.CYAN}  Hasta luego.{Style.RESET_ALL}")
                self.core.cleanup_session()
                sys.exit(0)
            else:
                print(f"{Fore.RED}  Opción no válida.{Style.RESET_ALL}")
                pause()
