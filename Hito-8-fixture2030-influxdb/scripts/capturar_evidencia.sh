#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
DB="fixture2030_metrics"
TOKEN_FILE="$ROOT_DIR/.secrets/influxdb_admin_token"
[[ -s "$TOKEN_FILE" ]] || { echo "Falta $TOKEN_FILE. Ejecutá scripts/inicializacion.sh" >&2; exit 1; }
TOKEN="$(cat "$TOKEN_FILE")"
OUT="$ROOT_DIR/docs/evidencia/ejecucion_$(date -u +%Y%m%d_%H%M%S).txt"
mkdir -p "$ROOT_DIR/docs/evidencia"

{
  echo "Hito 8 — Evidencia técnica del laboratorio"
  echo "Fecha UTC: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
  echo "=== Docker ==="
  docker compose ps
  echo
  echo "=== Imagen ==="
  docker image inspect influxdb:3-core --format 'RepoTags={{json .RepoTags}} Id={{.Id}} Created={{.Created}}' || true
  echo
  echo "=== Ping / versión ==="
  curl -fsS "http://127.0.0.1:8181/ping" -H "Authorization: Bearer $TOKEN"
  echo
  echo "=== Bases ==="
  docker compose exec -T influxdb influxdb3 show databases --token "$TOKEN"
  echo
  echo "=== Tablas ==="
  docker compose exec -T influxdb influxdb3 query --database "$DB" --token "$TOKEN" "SHOW TABLES"
  echo
  echo "=== Columnas estadísticas ==="
  docker compose exec -T influxdb influxdb3 query --database "$DB" --token "$TOKEN" "SHOW COLUMNS IN estadisticas_partido"
  echo
  echo "=== Columnas usuarios ==="
  docker compose exec -T influxdb influxdb3 query --database "$DB" --token "$TOKEN" "SHOW COLUMNS IN usuarios_conectados"
  echo
  echo "=== Retención ==="
  docker compose exec -T influxdb influxdb3 show retention --database "$DB" --token "$TOKEN"
  echo
  echo "=== Conteo ==="
  docker compose exec -T influxdb influxdb3 query --database "$DB" --token "$TOKEN" "SELECT COUNT(*) AS puntos_estadisticas FROM estadisticas_partido"
  docker compose exec -T influxdb influxdb3 query --database "$DB" --token "$TOKEN" "SELECT COUNT(*) AS puntos_usuarios FROM usuarios_conectados"
  echo
  echo "=== Distribución P-01 por equipo ==="
  docker compose exec -T influxdb influxdb3 query --database "$DB" --token "$TOKEN" "SELECT equipo_codigo, COUNT(*) AS puntos FROM estadisticas_partido WHERE partido_codigo='P-01' GROUP BY equipo_codigo ORDER BY equipo_codigo"
  echo
  echo "=== Consulta temporal P-01/ARG ==="
  for q in q01_ventana.sql q02_comparacion_equipos.sql q03_comparacion_fuentes.sql q04_pico_usuarios.sql; do
    echo "--- $q ---"
    docker compose exec -T influxdb influxdb3 query --database "$DB" --token "$TOKEN" --file "/scripts/$q" | head -80
  done
  echo
  echo "=== Agregaciones ==="
  for q in ag01_equipo.sql ag02_por_minuto.sql; do
    echo "--- $q ---"
    docker compose exec -T influxdb influxdb3 query --database "$DB" --token "$TOKEN" --file "/scripts/$q" | head -80
  done
  echo
  echo "=== Git status ==="
  git status --short 2>/dev/null || true
  echo
  echo "NOTA: el token no forma parte de esta evidencia."
} > "$OUT"

chmod 600 "$OUT"
echo "Evidencia generada: $OUT"
