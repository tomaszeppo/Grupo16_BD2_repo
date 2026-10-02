#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

STAMP=$(date '+%Y%m%d_%H%M%S')
OUT="docs/evidencia/ejecucion_${STAMP}.txt"
mkdir -p docs/evidencia

{
  echo "Hito 7 - Evidencia técnica Redis"
  echo "Fecha de ejecución: $(date '+%Y-%m-%d %H:%M:%S %z')"
  echo
  echo "===== RF1 / RNF1 / RNF2: ambiente ====="
  docker compose ps
  docker compose exec -T redis redis-cli PING
  docker compose exec -T redis redis-cli INFO server | grep -E 'redis_version|redis_mode|uptime_in_seconds'
  docker compose exec -T redis redis-cli INFO persistence | grep -E 'aof_enabled|aof_rewrite_in_progress|rdb_last_save_time'
  docker compose exec -T redis redis-cli CONFIG GET maxmemory
  docker compose exec -T redis redis-cli CONFIG GET maxmemory-policy
  echo

  echo "===== Scripts de demostración ====="
  for script in inicializacion carga_muestra sesiones cache concurrencia metricas; do
    echo
    echo "--- scripts/${script}.redis ---"
    docker compose exec -T redis redis-cli < "scripts/${script}.redis"
  done

  echo
  echo "===== Prueba concurrente ====="
  bash scripts/prueba_concurrencia.sh

  echo
  echo "===== Métricas finales ====="
  docker compose exec -T redis redis-cli INFO stats | grep -E 'keyspace_hits|keyspace_misses|expired_keys|evicted_keys'
  docker compose exec -T redis redis-cli INFO memory | grep -E 'used_memory_human|used_memory_peak_human|maxmemory_human'
} | tee "$OUT"

echo
echo "Evidencia guardada en: $OUT"
