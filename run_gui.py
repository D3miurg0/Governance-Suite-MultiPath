#!/usr/bin/env python3
"""Entrada directa al modo GUI — equivalente a: python main.py"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.app import GovernanceApp

if __name__ == "__main__":
    app = GovernanceApp()
    app.mainloop()
