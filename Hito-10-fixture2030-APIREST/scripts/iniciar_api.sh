#!/usr/bin/env bash
# Uso: scripts/iniciar_api.sh            -> API en contenedor (puerto 8000)
#      scripts/iniciar_api.sh --local    -> API en el notebook con el venv (requiere drivers instalados)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
[[ -f .env ]] || { echo "Falta .env (ver .env.example)" >&2; exit 1; }

if [[ "${1:-}" == "--local" ]]; then
  PY=python
  [[ -x .venv/Scripts/python ]] && PY=.venv/Scripts/python
  [[ -x .venv/bin/python ]] && PY=.venv/bin/python
  exec "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
fi

docker compose --profile api up -d --build api
for _ in $(seq 1 30); do
  curl -s -o /dev/null http://127.0.0.1:8000/openapi.json && { echo "API arriba: http://localhost:8000/docs"; exit 0; }
  sleep 2
done
echo "La API no respondió; ver: docker compose logs api" >&2
exit 1
