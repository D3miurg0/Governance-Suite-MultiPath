import datetime
from cli.menu_main import header, input_path, pause, Fore, Style
from modules.migration import MigrationModule


class MigrationMenu:
    def __init__(self, core):
        self.core = core
        self.migrator = MigrationModule(core)

    def _ask_date(self, prompt: str) -> datetime.datetime:
        raw = input(f"{Fore.YELLOW}  {prompt} (YYYY-MM-DD): {Style.RESET_ALL}").strip()
        try:
            return datetime.datetime.strptime(raw, "%Y-%m-%d")
        except ValueError:
            print(f"{Fore.RED}  Fecha inválida. Usando fecha por defecto.{Style.RESET_ALL}")
            return datetime.datetime(2000, 1, 1)

    def run(self):
        while True:
            header("Migración de Archivos")
            print(f"{Fore.GREEN}")
            print("  [1]  Configurar y ejecutar migración")
            print(f"{Fore.RED}")
            print("  [0]  Volver")
            print(Style.RESET_ALL)
            opt = input(f"{Fore.CYAN}  Opción: {Style.RESET_ALL}").strip()

            if opt == "1":
                src  = input_path("Ruta ORIGEN")
                dst  = input_path("Ruta DESTINO")
                s_dt = self._ask_date("Fecha inicio (filtro)")
                e_dt = self._ask_date("Fecha fin (filtro)")

                perm    = input(f"{Fore.YELLOW}  Copiar permisos NTFS? (s/N): {Style.RESET_ALL}").strip().lower() == 's'
                parallel = input(f"{Fore.YELLOW}  Modo paralelo? (S/n): {Style.RESET_ALL}").strip().lower() != 'n'
                flat    = input(f"{Fore.YELLOW}  Modo plano (sin filtros de fecha/tamaño)? (s/N): {Style.RESET_ALL}").strip().lower() == 's'
                overwrite = input(f"{Fore.YELLOW}  Sobrescribir duplicados? (s/N): {Style.RESET_ALL}").strip().lower() == 's'

                self.migrator.execute_migration(src, dst, s_dt, e_dt, perm, parallel, flat, overwrite)
                pause()
            elif opt == "0":
                break
            else:
                print(f"{Fore.RED}  Opción no válida.{Style.RESET_ALL}")
                pause()
