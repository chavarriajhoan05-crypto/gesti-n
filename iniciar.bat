@echo off
echo ========================================
echo Sistema de Gestion de Mantenimiento
echo ========================================
echo.

REM Verificar si Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no está instalado o no está en PATH
    pause
    exit /b 1
)

echo [1/3] Instalando dependencias Python...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Fallo al instalar dependencias
    pause
    exit /b 1
)

echo.
echo [2/3] Asegúrate de que MySQL esté ejecutándose
echo Por favor, importa el script database/schema.sql en MySQL Workbench
echo.
pause

echo [3/3] Iniciando la aplicación...
echo.
echo La aplicación estará disponible en: http://localhost:5000
echo.
python app.py

pause
