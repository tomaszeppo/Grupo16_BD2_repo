#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

STAMP=$(date '+%Y%m%d_%H%M%S')
OUT="docs/evidencia/benchmark_${STAMP}.txt"
mkdir -p docs/evidencia

{
  echo "Hito 7 - Medición Redis"
  echo "Fecha: $(date '+%Y-%m-%d %H:%M:%S %z')"
  echo
  echo "--- Estado del contenedor ---"
  docker compose ps
  echo
  echo "--- Versión Redis ---"
  docker compose exec -T redis redis-cli INFO server | grep -E 'redis_version|redis_mode|uptime_in_seconds'
  echo
  echo "--- Configuración de memoria ---"
  docker compose exec -T redis redis-cli CONFIG GET maxmemory
  docker compose exec -T redis redis-cli CONFIG GET maxmemory-policy
  echo
  echo "--- redis-benchmark (GET/SET/INCR) ---"
  echo "Método: 5000 requests por comando, 20 clientes, sobre el nodo local del contenedor."
  docker compose exec -T redis redis-benchmark -n 5000 -c 20 -q -t get,set,incr
  echo
  echo "--- Microprueba de hit/miss ---"
  docker compose exec -T redis redis-cli SET f2030:cache:medicion "ok" EX 60 >/dev/null

  BEFORE_HITS=$(docker compose exec -T redis redis-cli INFO stats | awk -F: '/^keyspace_hits:/{gsub(/\r/,"",$2); print $2}')
  BEFORE_MISSES=$(docker compose exec -T redis redis-cli INFO stats | awk -F: '/^keyspace_misses:/{gsub(/\r/,"",$2); print $2}')

  for i in $(seq 1 20); do
    docker compose exec -T redis redis-cli GET f2030:cache:medicion >/dev/null
  done
  for i in $(seq 1 5); do
    docker compose exec -T redis redis-cli GET f2030:cache:no-existe-${i} >/dev/null
  done

  AFTER_HITS=$(docker compose exec -T redis redis-cli INFO stats | awk -F: '/^keyspace_hits:/{gsub(/\r/,"",$2); print $2}')
  AFTER_MISSES=$(docker compose exec -T redis redis-cli INFO stats | awk -F: '/^keyspace_misses:/{gsub(/\r/,"",$2); print $2}')

  DELTA_HITS=$((AFTER_HITS-BEFORE_HITS))
  DELTA_MISSES=$((AFTER_MISSES-BEFORE_MISSES))
  TOTAL=$((DELTA_HITS+DELTA_MISSES))
  if (( TOTAL > 0 )); then
    HIT_RATE=$(awk -v h="$DELTA_HITS" -v t="$TOTAL" 'BEGIN { printf "%.2f", (h/t)*100 }')
  else
    HIT_RATE="0.00"
  fi

  echo "Hits de la microprueba: ${DELTA_HITS}"
  echo "Misses de la microprueba: ${DELTA_MISSES}"
  echo "Tasa hit observada: ${HIT_RATE}%"
  echo
  echo "--- Memoria observada ---"
  docker compose exec -T redis redis-cli INFO memory | grep -E 'used_memory_human|used_memory_peak_human|maxmemory_human'
  echo
  echo "--- Métricas completas de stats relevantes ---"
  docker compose exec -T redis redis-cli INFO stats | grep -E 'keyspace_hits|keyspace_misses|expired_keys|evicted_keys'

  docker compose exec -T redis redis-cli DEL f2030:cache:medicion >/dev/null
} | tee "$OUT"

echo
echo "Medición guardada en: $OUT"
