#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TOKEN_DIR="$ROOT_DIR/.secrets"
TOKEN_FILE="$TOKEN_DIR/influxdb_admin_token"
DB="fixture2030_metrics"
HOST="http://127.0.0.1:8181"

mkdir -p "$TOKEN_DIR"
chmod 700 "$TOKEN_DIR"
mkdir -p "$HOME/docker/data/influxdb"

if ! docker compose ps --status running --services | grep -qx influxdb; then
  echo "=== Iniciando InfluxDB 3 Core ==="
  docker compose up -d
fi

echo "=== Esperando disponibilidad del servidor ==="
for _ in $(seq 1 30); do
  CODE="$(curl -sS -o /dev/null -w "%{http_code}" "$HOST/health" 2>/dev/null || true)"
  if [[ "$CODE" == "200" || "$CODE" == "401" || "$CODE" == "403" ]]; then
    break
  fi
  sleep 2
done

if [[ ! -s "$TOKEN_FILE" ]]; then
  echo "=== Creando token administrativo local (solo se muestra una vez) ==="
  TOKEN="$(docker compose exec -T influxdb influxdb3 create token --admin | tr -d '\r' | tail -n 1)"
  if [[ -z "$TOKEN" ]]; then
    echo "No se pudo obtener el token." >&2
    exit 1
  fi
  printf '%s\n' "$TOKEN" > "$TOKEN_FILE"
  chmod 600 "$TOKEN_FILE"
  echo "Token guardado en $TOKEN_FILE (excluido por .gitignore)."
else
  TOKEN="$(cat "$TOKEN_FILE")"
  echo "=== Reutilizando token local existente ==="
fi

echo "=== Version / ping ==="
curl -fsS "$HOST/ping" -H "Authorization: Bearer $TOKEN"
echo

echo "=== Base de datos ==="
if ! docker compose exec -T influxdb influxdb3 show databases --token "$TOKEN" --format csv | grep -q "${DB}"; then
  docker compose exec -T influxdb influxdb3 create database --retention-period 90d --token "$TOKEN" "$DB"
  echo "Base $DB creada con retención de 90d."
else
  echo "Base $DB ya existe."
fi

echo "=== Tablas ==="
if ! docker compose exec -T influxdb influxdb3 query --database "$DB" --token "$TOKEN" "SHOW TABLES" | grep -q "estadisticas_partido"; then
  docker compose exec -T influxdb influxdb3 create table estadisticas_partido \
    --database "$DB" --token "$TOKEN" \
    --tags partido_id,equipo_id,sede,fuente,fase
fi
if ! docker compose exec -T influxdb influxdb3 query --database "$DB" --token "$TOKEN" "SHOW TABLES" | grep -q "usuarios_conectados"; then
  docker compose exec -T influxdb influxdb3 create table usuarios_conectados \
    --database "$DB" --token "$TOKEN" \
    --tags partido_id,region
fi

echo "=== SHOW TABLES ==="
docker compose exec -T influxdb influxdb3 query --database "$DB" --token "$TOKEN" "SHOW TABLES"

echo "=== Retención ==="
docker compose exec -T influxdb influxdb3 show retention --database "$DB" --token "$TOKEN"

echo "=== Health ==="
curl -fsS "$HOST/health" -H "Authorization: Bearer $TOKEN"
echo

echo "Inicialización OK. No publiques $TOKEN_FILE."
