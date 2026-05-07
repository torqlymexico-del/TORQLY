@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Torqly Launcher

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

if not exist ".env" (
    echo [Torqly] Creando .env desde .env.example...
    copy /Y ".env.example" ".env" >nul
)

if not exist ".venv\Scripts\python.exe" (
    echo [Torqly] No existe .venv. Preparando entorno...
    call :find_python
    if errorlevel 1 goto :fail

    call %PYTHON_BOOTSTRAP% -m venv .venv
    if errorlevel 1 goto :fail

    echo [Torqly] Instalando dependencias...
    call ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 goto :fail
    call ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto :fail
)

echo [Torqly] Aplicando migraciones...
call ".\.venv\Scripts\python.exe" -m alembic upgrade head
if errorlevel 1 goto :fail

call :server_ready
if errorlevel 1 (
    echo [Torqly] Iniciando servidor...
    start "Torqly Server" cmd /k "cd /d ""%PROJECT_ROOT%"" && call scripts\run.bat"
    call :wait_for_server
    if errorlevel 1 goto :startup_error
) else (
    echo [Torqly] El servidor ya esta en ejecucion.
)

if /I not "%TORQLY_NO_BROWSER%"=="1" (
    start "" "http://127.0.0.1:8000/login"
)

echo [Torqly] Listo. Puedes usar http://127.0.0.1:8000/login
exit /b 0

:find_python
set "PYTHON_BOOTSTRAP="
where py >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_BOOTSTRAP=py -3"
    exit /b 0
)
where python >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_BOOTSTRAP=python"
    exit /b 0
)
echo [Torqly] No se encontro Python instalado para crear .venv.
exit /b 1

:server_ready
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $resp = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health -TimeoutSec 2; if ($resp.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"
exit /b %errorlevel%

:wait_for_server
set /a TORQLY_TRIES=0
:wait_loop
call :server_ready
if not errorlevel 1 exit /b 0
set /a TORQLY_TRIES+=1
if !TORQLY_TRIES! GEQ 25 exit /b 1
timeout /t 1 >nul
goto :wait_loop

:startup_error
echo [Torqly] El servidor no respondio a tiempo.
echo [Torqly] Revisa la ventana "Torqly Server" para ver el error.
pause
exit /b 1

:fail
echo [Torqly] No fue posible completar el arranque.
pause
exit /b 1
