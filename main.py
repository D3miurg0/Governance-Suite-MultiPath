#!/usr/bin/env python3
"""Governance-Suite — Punto de entrada principal."""
import sys
import os

# Asegurar que el directorio raíz esté en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli.menu_main import MainMenu


def main():
    try:
        MainMenu().run()
    except KeyboardInterrupt:
        print("\n\n  Operación cancelada por el usuario.")
        sys.exit(0)


if __name__ == "__main__":
    main()
