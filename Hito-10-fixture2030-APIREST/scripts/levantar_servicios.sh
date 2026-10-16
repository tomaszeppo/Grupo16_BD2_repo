#!/usr/bin/env bash
# Levanta las seis bases, crea el token y la base de InfluxDB, compila las clases de IRIS y siembra datos.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Se creó .env desde .env.example. Completá las contraseñas (MONGO, NEO4J, REDIS, IRIS) y volvé a ejecutar." >&2
  exit 1
fi
set -a; source .env; set +a
for v in MONGO_PASSWORD NEO4J_PASSWORD REDIS_PASSWORD IRIS_PASSWORD; do
  [[ -n "${!v:-}" ]] || { echo "Falta $v en .env" >&2; exit 1; }
done

echo "== Levantando contenedores =="
docker compose up -d mongodb neo4j cassandra redis influxdb iris

echo "== Esperando healthchecks (Cassandra e IRIS pueden tardar 1-2 min) =="
for s in mongodb neo4j cassandra redis iris; do
  estado=starting
  for _ in $(seq 1 60); do
    estado="$(docker inspect -f '{{.State.Health.Status}}' "$(docker compose ps -q "$s")" 2>/dev/null || echo starting)"
    [[ "$estado" == "healthy" ]] && break
    sleep 5
  done
  echo "  $s: $estado"
  [[ "$estado" == "healthy" ]] || { echo "  $s no quedó healthy" >&2; exit 1; }
done

echo "== InfluxDB: token y base =="
for _ in $(seq 1 30); do
  codigo="$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8181/health || true)"
  [[ "$codigo" =~ ^(200|401|403)$ ]] && break
  sleep 2
done
if [[ -z "${INFLUX_TOKEN:-}" ]]; then
  INFLUX_TOKEN="$(docker compose exec -T influxdb influxdb3 create token --admin | tr -d '\r' | grep -oE 'apiv3_[A-Za-z0-9_-]+' | head -n1)"
  [[ -n "$INFLUX_TOKEN" ]] || { echo "No se pudo crear el token de InfluxDB (¿ya existía uno? borrá el volumen o cargá INFLUX_TOKEN en .env)" >&2; exit 1; }
  sed -i '/^INFLUX_TOKEN=/d' .env
  printf 'INFLUX_TOKEN=%s\n' "$INFLUX_TOKEN" >> .env
  echo "  token creado y guardado en .env (no se versiona)"
fi
if ! docker compose exec -T influxdb influxdb3 show databases --token "$INFLUX_TOKEN" --format csv | grep -q fixture2030_metrics; then
  docker compose exec -T influxdb influxdb3 create database --retention-period 90d --token "$INFLUX_TOKEN" fixture2030_metrics
fi

echo "== IRIS: usuario de la API y clases del Hito 9 =="
docker compose exec -T iris iris session IRIS -U %SYS < seed/iris/crear_usuario.mac
docker compose exec -T iris iris session IRIS -U USER < seed/iris/cargar_clases.mac

echo "== Sembrando datos (P-01..P-08) =="
docker compose --profile api build api
docker compose --profile api run --rm api python -m seed.run
echo "Listo. Siguiente paso: scripts/iniciar_api.sh"
