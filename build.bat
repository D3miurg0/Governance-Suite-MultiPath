@echo off
echo ============================================
echo  Governance-Suite v2.0.0 - Compilar .exe
echo ============================================
cd /d "%~dp0"

echo [1/4] Activando entorno virtual...
call venv\Scripts\activate
if errorlevel 1 (
    echo ERROR: No se encontro el venv. Ejecuta primero instalar.bat
    pause
    exit /b 1
)

echo [2/4] Instalando PyInstaller...
pip install pyinstaller -q

echo [3/4] Compilando ejecutable...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del GovernanceSuite.spec 2>nul
pyinstaller --onefile --windowed --name GovernanceSuite run_gui.py

echo [4/4] Creando carpetas necesarias junto al .exe...
mkdir dist\logs 2>nul
mkdir dist\output 2>nul

echo.
echo ============================================
echo  Build completado!
echo  Archivos listos en: dist\
echo  Llevar al servidor:
echo    - dist\GovernanceSuite.exe
echo    - dist\logs\
echo    - dist\output\
echo ============================================
pause
