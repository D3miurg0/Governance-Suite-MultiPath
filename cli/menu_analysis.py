import os
from cli.menu_main import header, input_path, pause, Fore, Style
from modules.analysis import AnalysisModule
from config import Config


class AnalysisMenu:
    def __init__(self, core):
        self.core = core
        self.analyzer = AnalysisModule(core)

    def run(self):
        while True:
            header("Análisis y Dashboard Excel")
            print(f"{Fore.GREEN}")
            print("  [1]  Analizar sesión actual")
            print("  [2]  Analizar carpeta personalizada")
            print(f"{Fore.RED}")
            print("  [0]  Volver")
            print(Style.RESET_ALL)
            opt = input(f"{Fore.CYAN}  Opción: {Style.RESET_ALL}").strip()

            if opt == "1":
                if self.core.current_audit_dir:
                    self.analyzer.generate_analysis_dashboard(self.core.current_audit_dir)
                else:
                    print(f"{Fore.RED}  No hay sesión activa.{Style.RESET_ALL}")
                pause()
            elif opt == "2":
                path = input_path("Carpeta con reportes CSV")
                if path and os.path.exists(path):
                    self.analyzer.generate_analysis_dashboard(path)
                else:
                    print(f"{Fore.RED}  Ruta no válida.{Style.RESET_ALL}")
                pause()
            elif opt == "0":
                break
            else:
                print(f"{Fore.RED}  Opción no válida.{Style.RESET_ALL}")
                pause()
