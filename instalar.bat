@echo off
echo ============================================
echo  Governance-Suite v2.0.0 - Instalacion
echo ============================================
cd /d "%~dp0"

echo [1/5] Creando entorno virtual...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Python no encontrado. Instala Python 3.10+ y vuelve a intentarlo.
    pause
    exit /b 1
)

echo [2/5] Activando entorno virtual...
call venv\Scripts\activate

echo [3/5] Instalando dependencias...
pip install -r requirements.txt
pip install pywin32 ttkthemes

echo [4/5] Creando carpetas necesarias...
mkdir logs 2>nul
mkdir output 2>nul

echo [5/5] Instalacion completada.
echo.
echo Opciones de ejecucion:
echo   1. Ejecucion local con venv:  run.bat
echo   2. Compilar .exe para server: build.bat
echo   3. Con cuenta de dominio:     runas /user:DOMINIO\usuario "ruta\GovernanceSuite.exe"
echo.
pause
