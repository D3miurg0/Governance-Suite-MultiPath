"""generate_icon.py — Descarga icon_source.png desde Canva (o usa el local)
y genera assets/icon.ico multi-resolución listo para PyInstaller.

Uso:
    python tools/generate_icon.py

Requisitos: pillow  (ya incluido en requirements.txt)
"""
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_PNG = ROOT / 'assets' / 'icon_source.png'
DST_ICO = ROOT / 'assets' / 'icon.ico'
SIZES   = [16, 24, 32, 48, 64, 128, 256]


def build_ico():
    try:
        from PIL import Image
    except ImportError:
        sys.exit('[ERROR] Pillow no instalado. Ejecuta: pip install pillow')

    if not SRC_PNG.exists():
        sys.exit(f'[ERROR] No se encontró {SRC_PNG}')

    print(f'[INFO] Leyendo fuente: {SRC_PNG}')
    with Image.open(SRC_PNG) as img:
        img = img.convert('RGBA')
        frames = [img.resize((s, s), Image.LANCZOS) for s in SIZES]

    DST_ICO.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        DST_ICO,
        format='ICO',
        sizes=[(s, s) for s in SIZES],
        append_images=frames[1:],
    )
    print(f'[OK]   ICO generado en: {DST_ICO}')
    print(f'       Resoluciones: {SIZES}')


if __name__ == '__main__':
    build_ico()
