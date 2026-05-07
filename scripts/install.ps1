$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& .\.venv\Scripts\python -m pip install --upgrade pip
& .\.venv\Scripts\python -m pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

Write-Host "Dependencias instaladas."
Write-Host "Edita .env con tu MySQL y credenciales externas."
Write-Host "Después ejecuta: .\\scripts\\run.ps1"

