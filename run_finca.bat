@echo off
setlocal
title Gestio Finca Ametllers - Iniciant...

echo ======================================================
echo    GESTIO DE LA FINCA D'AMETLLERS
echo ======================================================
echo.
echo [1/3] Verificant l'entorn de Python...

:: Comprovar si Python esta instal.lat
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instal.lat en aquest sistema.
    echo Descarrega'l a: https://www.python.org/downloads/
    pause
    exit /b
)

:: Comprovar si hi ha entorn virtual (opcional pero recomanat)
if exist venv\Scripts\activate.bat (
    echo [INFO] Activant entorn virtual local...
    call venv\Scripts\activate.bat
) else (
    echo [WARNING] No s'ha trobat entorn virtual. S'usara el Python global.
)

echo [2/3] Verificant llibreries (requirements.txt)...
python -m pip install -r requirements.txt --quiet

echo [3/3] Iniciant el servidor i obrint el navegador...
echo.
echo L'aplicacio s'obrira en uns segons a: http://127.0.0.1:5000
echo.
echo ======================================================
echo     NO TANQUIS AQUESTA FINESTRA MENTRE USIS EL PROGRAMA
echo ======================================================

:: Obrir el navegador en background
start http://127.0.0.1:5000

:: Executar l'aplicacio
python scripts/app.py

pause
