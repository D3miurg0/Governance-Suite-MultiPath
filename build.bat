@echo off
echo ========================================
echo  GovernanceSuite ^| Build
echo ========================================

pip install pillow pyinstaller >nul 2>&1

echo Generando icon.ico...
python tools\generate_icon.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Fallo al generar el icono. Revisa tools\generate_icon.py
    pause & exit /b 1
)

echo Construyendo ejecutable...
pyinstaller --clean -y "Governance-Suite.spec"

if %ERRORLEVEL% == 0 (
    echo.
    echo [OK] Build exitoso. Ejecutable en: dist\GovernanceSuite\
) else (
    echo.
    echo [ERROR] Fallo en el build. Revisa los mensajes anteriores.
)
pause
