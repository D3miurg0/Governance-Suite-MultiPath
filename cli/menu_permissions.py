from cli.menu_main import header, input_path, pause, Fore, Style
from modules.permission import PermissionModule


class PermissionsMenu:
    def __init__(self, core):
        self.core = core
        self.perm_mod = PermissionModule(core)

    def run(self):
        while True:
            header("Auditoría de Permisos NTFS")
            print(f"{Fore.GREEN}")
            print("  [1]  Generar matriz de permisos ACL")
            print(f"{Fore.RED}")
            print("  [0]  Volver")
            print(Style.RESET_ALL)
            opt = input(f"{Fore.CYAN}  Opción: {Style.RESET_ALL}").strip()

            if opt == "1":
                path = input_path("Ruta a auditar")
                try:
                    depth = int(input(f"{Fore.YELLOW}  Profundidad máxima (-1 = ilimitado): {Style.RESET_ALL}").strip())
                except ValueError:
                    depth = 2
                if path:
                    self.perm_mod.generate_permission_matrix(path, depth)
                pause()
            elif opt == "0":
                break
            else:
                print(f"{Fore.RED}  Opción no válida.{Style.RESET_ALL}")
                pause()
