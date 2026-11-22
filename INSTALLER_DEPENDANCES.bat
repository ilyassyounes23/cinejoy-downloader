@echo off
chcp 65001 >nul
title CineJoy Downloader - Installation des dépendances

set "ROOT_DIR=%~dp0"
set "PYTHON_EXE=%ROOT_DIR%python\python.exe"

if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

echo ========================================================
echo   CineJoy Downloader - Configuration des composants
echo ========================================================
echo.
"%PYTHON_EXE%" "%ROOT_DIR%setup_tools.py"
echo.
pause
