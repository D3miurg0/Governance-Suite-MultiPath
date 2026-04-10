#!/bin/bash
echo "=== Governance-Suite Build (Linux/Mac) ==="
pyinstaller Governance-Suite.spec --clean --noconfirm
echo ""
echo "Build completado. Ejecutable en dist/Governance-Suite/"
