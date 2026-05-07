#!/usr/bin/env bash
set -euo pipefail

if [ ! -d ".venv" ]; then
  echo "No existe .venv. Ejecuta primero ./scripts/install.sh"
  exit 1
fi

. .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload

