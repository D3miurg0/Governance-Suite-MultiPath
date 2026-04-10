@echo off
echo === Governance-Suite Build (Windows) ===
pyinstaller Governance-Suite.spec --clean --noconfirm
echo.
echo Build completado. Ejecutable en dist\Governance-Suite\
pause
