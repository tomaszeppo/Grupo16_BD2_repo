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

echo "=== Distribucion P-01 por equipo ==="
runq "SELECT equipo_codigo, COUNT(*) AS puntos FROM estadisticas_partido WHERE partido_codigo='P-01' GROUP BY equipo_codigo ORDER BY equipo_codigo"

echo "=== Distribucion P-01 por fuente ==="
runq "SELECT fuente, COUNT(*) AS puntos FROM estadisticas_partido WHERE partido_codigo='P-01' GROUP BY fuente ORDER BY fuente"

echo "=== Retencion ==="
docker compose exec -T influxdb influxdb3 show retention --database "$DB" --token "$TOKEN"
