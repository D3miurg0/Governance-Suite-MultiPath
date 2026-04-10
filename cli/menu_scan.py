from cli.menu_main import header, input_path, pause, Fore, Style
from modules.scan import ScanModule


class ScanMenu:
    def __init__(self, core):
        self.core = core
        self.scanner = ScanModule(core)

    def run(self):
        while True:
            header("Escaneo de Archivos")
            print(f"{Fore.GREEN}")
            print("  [1]  Escanear una ruta")
            print("  [2]  Escanear múltiples rutas (separadas por comas)")
            print(f"{Fore.RED}")
            print("  [0]  Volver")
            print(Style.RESET_ALL)
            opt = input(f"{Fore.CYAN}  Opción: {Style.RESET_ALL}").strip()

            if opt == "1":
                path = input_path("Ruta a escanear")
                if path:
                    self.scanner.run_scan(path)
                    pause()
            elif opt == "2":
                raw = input_path("Rutas separadas por coma")
                paths = [p.strip() for p in raw.split(',') if p.strip()]
                for p in paths:
                    self.scanner.run_scan(p)
                pause()
            elif opt == "0":
                break
            else:
                print(f"{Fore.RED}  Opción no válida.{Style.RESET_ALL}")
                pause()
