@echo off
chcp 65001 >nul
title CineJoy Downloader Pro - Application Complete

set "ROOT_DIR=%~dp0"
set "APP_DIR=%ROOT_DIR%cinejoy_app"
set "BIN_DIR=%ROOT_DIR%bin"
set "PYTHON_EXE=%ROOT_DIR%python\python.exe"

echo ========================================================
echo       CineJoy ^& Video Downloader Pro - Web UI
echo ========================================================
echo.

if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

REM Verification et telechargement automatique des outils
if not exist "%BIN_DIR%\ffmpeg.exe" (
    echo [INFO] Premier lancement detecte : preparation automatique des composants...
    "%PYTHON_EXE%" "%ROOT_DIR%setup_tools.py"
)

echo.
echo Demarrage de l'application autonome...
echo Serveur en cours d'initialisation sur http://localhost:5000
echo Ouverture automatique de votre navigateur Web...
start "" http://localhost:5000

echo.
echo ========================================================
echo  L'application est prete et en ligne !
echo.
echo  1. Votre navigateur s'ouvre sur : http://localhost:5000
echo  2. Collez votre lien et cliquez sur "Analyser le flux"
echo  3. Choisissez la qualite et lancez le telechargement
echo  4. Vos fichiers arrivent dans : _VIDEOS_TELECHARGEES
echo.
echo  (Laissez cette fenetre ouverte pendant vos telechargements)
echo ========================================================
echo.

if exist "%ROOT_DIR%app.py" (
    "%PYTHON_EXE%" "%ROOT_DIR%app.py"
) else (
    cd /d "%APP_DIR%"
    "%PYTHON_EXE%" app.py
)

pause
