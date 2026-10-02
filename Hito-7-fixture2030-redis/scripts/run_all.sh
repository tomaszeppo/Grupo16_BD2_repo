#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

run_redis_script() {
  local script="$1"
  echo ""
  echo "============================================================"
  echo "Ejecutando ${script}"
  echo "============================================================"
  docker compose exec -T redis redis-cli < "scripts/${script}"
}

run_redis_script "inicializacion.redis"
run_redis_script "carga_muestra.redis"
run_redis_script "sesiones.redis"
run_redis_script "cache.redis"
run_redis_script "concurrencia.redis"
run_redis_script "metricas.redis"

echo ""
echo "Hito 7: secuencia de demostración finalizada."
