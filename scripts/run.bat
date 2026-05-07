@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"
cd /d "%PROJECT_ROOT%"

if not exist ".venv" (
    echo No existe .venv. Ejecuta primero .\scripts\install.ps1
    exit /b 1
)

if not exist ".\.venv\Scripts\python.exe" (
    echo No se encontro Python dentro de .\.venv\Scripts
    exit /b 1
)

call ".\.venv\Scripts\python.exe" -m alembic upgrade head
if errorlevel 1 exit /b %errorlevel%

call ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 0.0.0.0
exit /b %errorlevel%
