#!/usr/bin/env python3
"""
Governance-Suite — Launcher principal.

Uso:
    python main.py          -> lanza GUI (Tkinter)
    python main.py --cli    -> lanza CLI interactivo
    python main.py --help   -> muestra ayuda
"""
import sys
import os


def show_help():
    print("""
Governance-Suite v1.0.0
-----------------------
Uso: python main.py [OPCION]

Opciones:
  (sin args)   Lanza la interfaz gráfica (GUI)
  --cli        Lanza el menú interactivo CLI
  --help       Muestra esta ayuda

Ejemplos:
  python main.py
  python main.py --cli
  python run_gui.py
  python run_cli.py
""")


def launch_gui():
    """Importa y lanza la GUI de Tkinter."""
    try:
        from gui.app import GovernanceApp
        app = GovernanceApp()
        app.mainloop()
    except ImportError as e:
        print(f"[ERROR] No se pudo cargar la GUI: {e}")
        print("Intenta: python main.py --cli")
        sys.exit(1)


def launch_cli():
    """Importa y lanza el menú CLI."""
    try:
        from cli.menu_main import MainMenu
        menu = MainMenu()
        menu.run()
    except ImportError as e:
        print(f"[ERROR] No se pudo cargar el CLI: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n[!] Cancelado por el usuario.")
        sys.exit(0)


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        show_help()
        sys.exit(0)

    if "--cli" in args:
        launch_cli()
    else:
        # Por defecto lanza GUI; si falla por entorno headless, cae a CLI
        try:
            import tkinter  # noqa: F401 — verificación silenciosa
            launch_gui()
        except Exception:
            print("[INFO] Entorno sin display detectado. Cambiando a modo CLI...")
            launch_cli()
