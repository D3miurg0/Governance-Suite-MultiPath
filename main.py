"""
Governance-Suite — Launcher principal
Uso:
    python main.py          → lanza GUI
    python main.py --cli    → lanza CLI interactiva
    python main.py --help   → muestra ayuda
"""
import sys
import argparse


def parse_args():
    parser = argparse.ArgumentParser(
        prog="Governance-Suite",
        description="Suite unificada CLI + GUI para gestión de archivos, permisos y análisis",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Ejecutar en modo CLI interactivo",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Mostrar versión y salir",
    )
    parser.add_argument(
        "--lang",
        choices=["es", "en"],
        default=None,
        help="Idioma de la interfaz (es|en)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Mostrar versión
    if args.version:
        from config import VERSION, APP_NAME
        print(f"{APP_NAME} v{VERSION}")
        sys.exit(0)

    # Sobrescribir idioma si se especificó
    if args.lang:
        import os
        os.environ["GSUITE_LANG"] = args.lang

    if args.cli:
        # Modo CLI
        from cli.menu_main import MainMenu
        menu = MainMenu()
        menu.run()
    else:
        # Modo GUI (por defecto)
        try:
            from gui.app import GovernanceApp
            app = GovernanceApp()
            app.run()
        except ImportError as e:
            print(f"[Error] No se pudo cargar la GUI: {e}")
            print("Intenta ejecutar con --cli para modo consola.")
            sys.exit(1)


if __name__ == "__main__":
    main()
