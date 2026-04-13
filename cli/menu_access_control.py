"""
cli/menu_access_control.py
─────────────────────────────────────────────────────────────────────────────
Menú CLI — Gestión de Derechos de Acceso ISO 27001:2022 (5.15 / 5.18)
─────────────────────────────────────────────────────────────────────────────
"""
from cli.menu_main import header, input_path, pause, Fore, Style
from modules.access_control import AccessControlModule, PERMISSION_LEVELS


class AccessControlMenu:
    def __init__(self, core):
        self.core = core
        self.ac   = AccessControlModule(core)

    # ── helpers locales ───────────────────────────────────────────────────
    def _pick_level(self) -> str:
        levels = list(PERMISSION_LEVELS.keys())
        print(f"\n{Fore.CYAN}  Niveles disponibles:{Style.RESET_ALL}")
        for i, lvl in enumerate(levels, 1):
            print(f"    [{i}] {lvl}")
        raw = input(f"{Fore.YELLOW}  Opción (1-{len(levels)}): {Style.RESET_ALL}").strip()
        try:
            return levels[int(raw) - 1]
        except (ValueError, IndexError):
            return "Read"

    # ── submenú 5.15 — consulta ───────────────────────────────────────────
    def _menu_list(self):
        header("5.15 — Listar accesos de una ruta")
        path = input_path("Ruta a consultar")
        if not path:
            return
        aces = self.ac.list_access(path)
        if not aces:
            print(f"{Fore.YELLOW}  Sin ACEs o ruta inaccesible.{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.CYAN}  {'Cuenta':<40} {'Tipo':<8} {'Heredado':<10} Permisos{Style.RESET_ALL}")
            print("  " + "-" * 90)
            for a in aces:
                heredado = "Sí" if a["inherited"] else "No"
                print(f"  {a['account']:<40} {a['type']:<8} {heredado:<10} {a['permissions']}")
        pause()

    def _menu_effective(self):
        header("5.15 — Acceso efectivo de un usuario")
        path    = input_path("Ruta")
        account = input(f"{Fore.YELLOW}  Cuenta (DOMINIO\\\\usuario): {Style.RESET_ALL}").strip()
        if not path or not account:
            return
        result = self.ac.effective_access(path, account)
        print(f"\n{Fore.GREEN}  Acceso efectivo para '{account}':")
        print(f"  Allow mask : 0x{result.get('allow_mask', 0):08X}")
        print(f"  Deny  mask : 0x{result.get('deny_mask',  0):08X}")
        print(f"  Efectivo   : {result.get('summary', 'N/A')}{Style.RESET_ALL}")
        pause()

    # ── submenú 5.15 — asignación ─────────────────────────────────────────
    def _menu_grant(self):
        header("5.15 — Otorgar acceso (Grant Allow)")
        path    = input_path("Ruta")
        account = input(f"{Fore.YELLOW}  Cuenta (DOMINIO\\\\usuario o grupo): {Style.RESET_ALL}").strip()
        if not path or not account:
            return
        level   = self._pick_level()
        inherit_raw = input(f"{Fore.YELLOW}  ¿Propagar a subcarpetas y archivos? (s/n) [s]: {Style.RESET_ALL}").strip().lower()
        inherit = inherit_raw != "n"
        confirm = input(
            f"{Fore.RED}  ⚠  Confirmar: otorgar '{level}' a '{account}' en '{path}' (s/n): {Style.RESET_ALL}"
        ).strip().lower()
        if confirm == "s":
            self.ac.grant_access(path, account, level, inherit)
        else:
            print("  Operación cancelada.")
        pause()

    def _menu_deny(self):
        header("5.15 — Denegar acceso (Grant Deny)")
        path    = input_path("Ruta")
        account = input(f"{Fore.YELLOW}  Cuenta: {Style.RESET_ALL}").strip()
        if not path or not account:
            return
        level   = self._pick_level()
        confirm = input(
            f"{Fore.RED}  ⚠  Confirmar Deny '{level}' a '{account}' en '{path}' (s/n): {Style.RESET_ALL}"
        ).strip().lower()
        if confirm == "s":
            self.ac.deny_access(path, account, level)
        else:
            print("  Operación cancelada.")
        pause()

    # ── submenú 5.18 — revocación ─────────────────────────────────────────
    def _menu_revoke(self):
        header("5.18 — Revocar acceso de una cuenta")
        path    = input_path("Ruta")
        account = input(f"{Fore.YELLOW}  Cuenta a revocar: {Style.RESET_ALL}").strip()
        if not path or not account:
            return
        confirm = input(
            f"{Fore.RED}  ⚠  Esto eliminará TODOS los ACEs explícitos de '{account}'. Confirmar (s/n): {Style.RESET_ALL}"
        ).strip().lower()
        if confirm == "s":
            self.ac.revoke_access(path, account)
        else:
            print("  Operación cancelada.")
        pause()

    def _menu_orphans(self):
        header("5.18 — Revisar accesos sobrantes (SIDs no resolvibles)")
        path = input_path("Ruta raíz")
        try:
            depth = int(input(f"{Fore.YELLOW}  Profundidad (-1 = ilimitado) [2]: {Style.RESET_ALL}").strip() or "2")
        except ValueError:
            depth = 2
        if not path:
            return
        orphans = self.ac.review_orphan_access(path, depth)
        if not orphans:
            print(f"{Fore.GREEN}  ✅  No se encontraron SIDs sin resolver.{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.RED}  ⚠  {len(orphans)} acceso(s) sobrante(s) detectado(s):{Style.RESET_ALL}")
            print(f"  {'Ruta':<50} {'SID':<30} {'Tipo':<8} Permisos")
            print("  " + "-" * 110)
            for o in orphans:
                print(f"  {o['path']:<50} {o['sid']:<30} {o['type']:<8} {o['permissions']}")
        pause()

    def _menu_cleanup(self):
        header("5.18 — Limpiar ACEs explícitos redundantes con herencia")
        path    = input_path("Ruta")
        if not path:
            return
        confirm = input(
            f"{Fore.RED}  ⚠  Eliminará ACEs explícitos que duplican herencia en '{path}'. Confirmar (s/n): {Style.RESET_ALL}"
        ).strip().lower()
        if confirm == "s":
            removed = self.ac.revoke_inherited_overrides(path)
            print(f"{Fore.GREEN}  ✅  {removed} ACE(s) redundante(s) eliminado(s).{Style.RESET_ALL}")
        else:
            print("  Operación cancelada.")
        pause()

    def _menu_report(self):
        header("5.15 / 5.18 — Exportar reporte completo CSV")
        path = input_path("Ruta raíz")
        try:
            depth = int(input(f"{Fore.YELLOW}  Profundidad (-1 = ilimitado) [2]: {Style.RESET_ALL}").strip() or "2")
        except ValueError:
            depth = 2
        if not path:
            return
        self.ac.export_access_report(path, depth)
        pause()

    # ── menú principal ────────────────────────────────────────────────────
    def run(self):
        while True:
            header("Gestión de Derechos de Acceso — ISO 27001:2022")
            print(f"{Fore.CYAN}  Control 5.15 — Control de Acceso{Style.RESET_ALL}")
            print("  [1]  Listar ACEs de una ruta")
            print("  [2]  Consultar acceso efectivo de un usuario")
            print("  [3]  Otorgar acceso (Grant Allow)")
            print("  [4]  Denegar acceso (Grant Deny)")
            print(f"\n{Fore.CYAN}  Control 5.18 — Derechos de Acceso{Style.RESET_ALL}")
            print("  [5]  Revocar acceso de una cuenta")
            print("  [6]  Revisar accesos sobrantes (SIDs no resolvibles)")
            print("  [7]  Limpiar ACEs redundantes con herencia")
            print(f"\n{Fore.CYAN}  Reportes{Style.RESET_ALL}")
            print("  [8]  Exportar reporte completo CSV (5.15 + 5.18)")
            print(f"{Fore.RED}\n  [0]  Volver{Style.RESET_ALL}")

            opt = input(f"\n{Fore.CYAN}  Opción: {Style.RESET_ALL}").strip()
            actions = {
                "1": self._menu_list,
                "2": self._menu_effective,
                "3": self._menu_grant,
                "4": self._menu_deny,
                "5": self._menu_revoke,
                "6": self._menu_orphans,
                "7": self._menu_cleanup,
                "8": self._menu_report,
            }
            if opt == "0":
                break
            elif opt in actions:
                actions[opt]()
            else:
                print(f"{Fore.RED}  Opción no válida.{Style.RESET_ALL}")
                pause()
