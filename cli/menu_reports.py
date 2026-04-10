import os
from cli.menu_main import header, input_path, pause, Fore, Style
from config import Config


class ReportsMenu:
    def __init__(self, core):
        self.core = core

    def run(self):
        while True:
            header("Reportes y Exportación")
            print(f"{Fore.GREEN}")
            print("  [1]  Ver sesión actual")
            print("  [2]  Listar reportes generados")
            print("  [3]  Abrir carpeta de salida")
            print(f"{Fore.RED}")
            print("  [0]  Volver")
            print(Style.RESET_ALL)
            opt = input(f"{Fore.CYAN}  Opción: {Style.RESET_ALL}").strip()

            if opt == "1":
                print(f"\n  Sesión: {self.core.current_audit_dir or 'Sin carpeta asignada'}")
                print(f"  Errores registrados: {len(self.core.access_errors)}")
                pause()
            elif opt == "2":
                path = self.core.current_audit_dir or Config.OUTPUT_DIR
                if os.path.exists(path):
                    files = [f for f in os.listdir(path) if f.endswith(('.csv', '.xlsx', '.json'))]
                    if files:
                        print()
                        for f in files:
                            fp = os.path.join(path, f)
                            size = os.path.getsize(fp) / 1024
                            print(f"  {Fore.GREEN}{f}{Style.RESET_ALL}  ({size:.1f} KB)")
                    else:
                        print(f"{Fore.YELLOW}  No hay reportes generados aún.{Style.RESET_ALL}")
                pause()
            elif opt == "3":
                path = self.core.current_audit_dir or Config.OUTPUT_DIR
                if os.name == 'nt':
                    os.startfile(path)
                else:
                    os.system(f'xdg-open "{path}"')
            elif opt == "0":
                break
            else:
                print(f"{Fore.RED}  Opción no válida.{Style.RESET_ALL}")
                pause()
