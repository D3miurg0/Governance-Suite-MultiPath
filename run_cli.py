#!/usr/bin/env python3
"""Entrada directa al modo CLI — equivalente a: python main.py --cli"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli.menu_main import MainMenu

if __name__ == "__main__":
    try:
        MainMenu().run()
    except KeyboardInterrupt:
        print("\n[!] Saliendo...")
        sys.exit(0)
