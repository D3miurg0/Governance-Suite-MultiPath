"""generate_icon.py — Genera assets/icon.ico multi-resolución para PyInstaller.

Diseño: escudo hexagonal Governance Suite (paleta Catppuccin Mocha)
  - Fondo: #1e1e2e (azul marino oscuro)
  - Escudo: #89b4fa (azul accent)
  - Símbolo: carpeta/archivo en #cdd6f4 (blanco azulado)

Uso:
    python tools\generate_icon.py

Requisitos: pillow  (incluido en requirements.txt)
"""
import sys
import math
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
DST_ICO = ROOT / 'assets' / 'icon.ico'
SIZES   = [16, 24, 32, 48, 64, 128, 256]

COLOR_BG     = (30,  30,  46,  255)   # #1e1e2e
COLOR_SHIELD = (137, 180, 250, 255)   # #89b4fa
COLOR_SYMBOL = (205, 214, 244, 255)   # #cdd6f4
COLOR_DARK   = (30,  30,  46,  255)   # #1e1e2e (detalle interior)


def draw_icon(size: int):
    from PIL import Image, ImageDraw

    img  = Image.new('RGBA', (size, size), COLOR_BG)
    draw = ImageDraw.Draw(img)
    cx, cy = size / 2, size / 2

    # --- Escudo hexagonal ---
    r_outer = size * 0.42
    shield_pts = []
    for i in range(6):
        angle = math.radians(60 * i - 90)
        shield_pts.append((
            cx + r_outer * math.cos(angle),
            cy + r_outer * math.sin(angle),
        ))
    # Estirar ligeramente hacia abajo para forma de escudo
    shield_pts[3] = (cx, cy + r_outer * 1.15)
    draw.polygon(shield_pts, fill=COLOR_SHIELD)

    # --- Símbolo: carpeta simplificada ---
    m  = size * 0.18
    fw = size * 0.50
    fh = size * 0.34
    fx = cx - fw / 2
    fy = cy - fh / 2 + size * 0.03

    # Cuerpo de la carpeta
    draw.rounded_rectangle(
        [fx, fy + fh * 0.18, fx + fw, fy + fh],
        radius=max(1, int(size * 0.04)),
        fill=COLOR_DARK,
    )
    # Pestaña superior
    tab_w = fw * 0.45
    tab_h = fh * 0.22
    draw.rounded_rectangle(
        [fx, fy, fx + tab_w, fy + tab_h + size * 0.03],
        radius=max(1, int(size * 0.03)),
        fill=COLOR_DARK,
    )
    # Líneas de archivos dentro de la carpeta
    if size >= 32:
        line_x0 = fx + fw * 0.18
        line_x1 = fx + fw * 0.82
        for k in range(3):
            ly = fy + fh * 0.38 + k * fh * 0.18
            lw = max(1, int(size * 0.025))
            draw.line([(line_x0, ly), (line_x1, ly)], fill=COLOR_SYMBOL, width=lw)

    return img


def build_ico():
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        sys.exit('[ERROR] Pillow no instalado. Ejecuta: pip install pillow')

    DST_ICO.parent.mkdir(parents=True, exist_ok=True)

    frames = [draw_icon(s) for s in SIZES]
    frames[0].save(
        DST_ICO,
        format='ICO',
        sizes=[(s, s) for s in SIZES],
        append_images=frames[1:],
    )
    print(f'[OK]   ICO generado en: {DST_ICO}')
    print(f'       Resoluciones incluidas: {SIZES}')


if __name__ == '__main__':
    build_ico()
