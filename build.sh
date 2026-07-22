#!/bin/bash
echo "=== Governance-Suite Build (Linux/Mac) ==="

if [ -f "venv/bin/activate" ]; then
    echo "Activando entorno virtual..."
    source venv/bin/activate
fi

pip install pillow pyinstaller >/dev/null 2>&1

echo "Generando icon.ico..."
python tools/generate_icon.py || { echo "[ERROR] Fallo al generar el icono."; exit 1; }

echo "Construyendo ejecutable..."
pyinstaller Governance-Suite.spec --clean --noconfirm

echo ""
echo "Build completado. Ejecutable en dist/GovernanceSuite/"
