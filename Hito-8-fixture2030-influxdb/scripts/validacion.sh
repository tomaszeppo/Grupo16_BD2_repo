#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
DB="fixture2030_metrics"
TOKEN_FILE="$ROOT_DIR/.secrets/influxdb_admin_token"
[[ -s "$TOKEN_FILE" ]] || { echo "Falta $TOKEN_FILE. Ejecutá scripts/inicializacion.sh" >&2; exit 1; }
TOKEN="$(cat "$TOKEN_FILE")"

runq() {
  docker compose exec -T influxdb influxdb3 query --database "$DB" --token "$TOKEN" "$1"
}

echo "=== SHOW TABLES ==="
runq "SHOW TABLES"

echo "=== SHOW COLUMNS estadisticas_partido ==="
runq "SHOW COLUMNS IN estadisticas_partido"

echo "=== SHOW COLUMNS usuarios_conectados ==="
runq "SHOW COLUMNS IN usuarios_conectados"

echo "=== Conteo estadisticas ==="
runq "SELECT COUNT(*) AS puntos_estadisticas FROM estadisticas_partido"

echo "=== Conteo usuarios ==="
runq "SELECT COUNT(*) AS puntos_usuarios FROM usuarios_conectados"

echo "=== Distribucion M001 por equipo ==="
runq "SELECT equipo_id, COUNT(*) AS puntos FROM estadisticas_partido WHERE partido_id='M001' GROUP BY equipo_id ORDER BY equipo_id"

echo "=== Distribucion M001 por fuente ==="
runq "SELECT fuente, COUNT(*) AS puntos FROM estadisticas_partido WHERE partido_id='M001' GROUP BY fuente ORDER BY fuente"

echo "=== Retencion ==="
docker compose exec -T influxdb influxdb3 show retention --database "$DB" --token "$TOKEN"
