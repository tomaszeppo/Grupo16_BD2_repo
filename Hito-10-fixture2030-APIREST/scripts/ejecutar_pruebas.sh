#!/usr/bin/env bash
# Uso: scripts/ejecutar_pruebas.sh [unit|drivers|integration|todo]   (por defecto: unit)
#   unit        -> pytest local con el venv (sin bases)
#   drivers     -> pruebas de dependencia caída, dentro del contenedor api (necesita los drivers)
#   integration -> pruebas black-box contra la API levantada (restaura la sesión demo antes de correr)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
PY=python
[[ -x .venv/Scripts/python ]] && PY=.venv/Scripts/python
[[ -x .venv/bin/python ]] && PY=.venv/bin/python
modo="${1:-unit}"
case "$modo" in
  unit) "$PY" -m pytest tests/unit -q ;;
  drivers) docker compose --profile api run --rm api python -m pytest tests/integration/test_dependencia_caida.py -q ;;
  integration)
    docker compose --profile api run --rm api python -m seed.run --solo redis
    API_URL="${API_URL:-http://127.0.0.1:8000}" "$PY" -m pytest tests/integration -m integration -q ;;
  todo) "$0" unit && "$0" drivers && "$0" integration ;;
  *) echo "Modo desconocido: $modo" >&2; exit 2 ;;
esac
