#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

KEY="f2030:contador:partido:P001:visitas"
WORKERS="10"
INCREMENTS_PER_WORKER="100"
EXPECTED=$((WORKERS * INCREMENTS_PER_WORKER))

docker compose exec -T redis redis-cli SET "$KEY" 0 EX 3600 >/dev/null

worker() {
  # Un proceso de worker dentro del contenedor ejecuta 100 INCRBY seguidos.
  # Los 10 workers del host se lanzan en paralelo, por lo que Redis recibe
  # actualizaciones intercaladas de distintos clientes.
  docker compose exec -T redis sh -c "i=0; while [ \$i -lt ${INCREMENTS_PER_WORKER} ]; do redis-cli INCRBY '${KEY}' 1 >/dev/null; i=\$((i+1)); done"
}

start_ms=$(python3 - <<'PYWORKER'
import time
print(int(time.time()*1000))
PYWORKER
)

pids=()
for ((w=1; w<=WORKERS; w++)); do
  worker &
  pids+=("$!")
done

for pid in "${pids[@]}"; do
  wait "$pid"
done

end_ms=$(python3 - <<'PYWORKER'
import time
print(int(time.time()*1000))
PYWORKER
)

OBSERVED=$(docker compose exec -T redis redis-cli GET "$KEY" | tr -d '\r\n')
TTL=$(docker compose exec -T redis redis-cli TTL "$KEY" | tr -d '\r\n')
DURATION=$((end_ms-start_ms))

cat <<EOF_OUT
=== Prueba concurrente RF8 ===
Workers: ${WORKERS}
Incrementos por worker: ${INCREMENTS_PER_WORKER}
Esperado: ${EXPECTED}
Observado: ${OBSERVED}
TTL restante: ${TTL}s
Duración observada: ${DURATION} ms
Resultado: $( [[ "$OBSERVED" == "$EXPECTED" ]] && echo "OK - no se perdieron incrementos" || echo "ERROR - revisar entorno" )

Interpretación:
Los 10 workers ejecutan INCRBY sobre la misma clave en paralelo. INCRBY es una operación atómica dentro de Redis y evita el patrón GET-modificar-SET.
EOF_OUT
