#!/usr/bin/env bash
set -euo pipefail

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
fi

echo "Dependencias instaladas."
echo "Edita .env con tu MySQL y credenciales externas."
echo "Luego ejecuta: ./scripts/run.sh"

