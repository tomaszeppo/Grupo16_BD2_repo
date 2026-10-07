#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
DB="fixture2030_metrics"
TOKEN_FILE="$ROOT_DIR/.secrets/influxdb_admin_token"
[[ -s "$TOKEN_FILE" ]] || { echo "Falta $TOKEN_FILE. Ejecutá scripts/inicializacion.sh" >&2; exit 1; }
TOKEN="$(cat "$TOKEN_FILE")"

for q in q01_ventana.sql q02_comparacion_equipos.sql q03_comparacion_fuentes.sql q04_pico_usuarios.sql; do
  echo "=== $q ==="
  docker compose exec -T influxdb influxdb3 query --database "$DB" --token "$TOKEN" --file "/scripts/$q"
done
