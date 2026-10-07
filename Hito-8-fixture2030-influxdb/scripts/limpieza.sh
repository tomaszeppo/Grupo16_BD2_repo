#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
DB="fixture2030_metrics"
TOKEN_FILE="$ROOT_DIR/.secrets/influxdb_admin_token"

cat <<'MSG'
ATENCIÓN: esta limpieza elimina la base del laboratorio y sus puntos.
La retención en InfluxDB 3 Core queda definida al crear la base; para empezar
con otra política de retención también corresponde recrear la base.
MSG
read -r -p "Escribí BORRAR para continuar: " CONFIRM
[[ "$CONFIRM" == "BORRAR" ]] || { echo "Cancelado."; exit 0; }

[[ -s "$TOKEN_FILE" ]] || { echo "Falta $TOKEN_FILE" >&2; exit 1; }
TOKEN="$(cat "$TOKEN_FILE")"
docker compose exec -T influxdb influxdb3 delete database --token "$TOKEN" "$DB"
echo "Base eliminada. Para recrearla ejecutá scripts/inicializacion.sh"
