$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    throw "No existe .venv. Ejecuta primero .\\scripts\\install.ps1"
}

& .\.venv\Scripts\alembic upgrade head
& .\.venv\Scripts\uvicorn app.main:app --reload

