@echo off
echo ========================================
echo  GovernanceSuite ^| Build
echo ========================================

pip install pyinstaller >nul 2>&1

echo Construyendo ejecutable...
pyinstaller --clean "Governance-Suite.spec"

if %ERRORLEVEL% == 0 (
    echo.
    echo [OK] Build exitoso. Ejecutable en: dist\GovernanceSuite\
) else (
    echo.
    echo [ERROR] Fallo en el build. Revisa los mensajes anteriores.
)
pause
