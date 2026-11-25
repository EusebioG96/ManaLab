@echo off
rem Vista previa de la web de ManaLab sin desplegarla (ML-329). Doble clic para abrirla en el navegador.
chcp 65001 >nul
rem Nos situamos en la raiz del repositorio (la carpeta de arriba de tools\).
cd /d "%~dp0.."

set "PYTHON="
py -3 --version >nul 2>&1 && set "PYTHON=py -3"
if not defined PYTHON (
    python --version >nul 2>&1 && set "PYTHON=python"
)
if not defined PYTHON goto sin_python

%PYTHON% tools\vista_previa.py %*
if errorlevel 1 (
    echo.
    echo La vista previa se ha cerrado con un error. Pulsa una tecla para salir.
    pause >nul
)
exit /b

:sin_python
echo No encuentro Python en este equipo, y la vista previa lo necesita.
echo.
echo Para instalarlo:
echo   1. Entra en https://www.python.org/downloads/ y descarga la version 3.10 o posterior.
echo   2. Al instalar, marca la casilla "Add python.exe to PATH" y pulsa "Install Now".
echo   3. Cuando termine, vuelve a hacer doble clic en este archivo.
echo.
echo Pulsa una tecla para salir.
pause >nul
exit /b 1
