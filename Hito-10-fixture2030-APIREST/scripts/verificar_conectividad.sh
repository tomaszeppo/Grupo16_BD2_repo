#!/usr/bin/env bash
# Verifica puertos de cada base (desde el notebook) y el /health de la API.
cd "$(dirname "${BASH_SOURCE[0]}")/.."
[[ -f .env ]] && { set -a; source .env; set +a; }
rc=0
chequear() {
  if (exec 3<>"/dev/tcp/127.0.0.1/$2") 2>/dev/null; then echo "  $1 (:$2) ... accesible"; else echo "  $1 (:$2) ... NO accesible"; rc=1; fi
}
echo "== Puertos publicados por Docker en el notebook =="
chequear mongodb "${MONGO_HOST_PORT:-27017}"; chequear neo4j "${NEO4J_HOST_PORT:-7687}"; chequear cassandra "${CASSANDRA_HOST_PORT:-9042}"
chequear redis "${REDIS_HOST_PORT:-6379}"; chequear influxdb "${INFLUX_HOST_PORT:-8181}"; chequear iris "${IRIS_HOST_PORT:-1972}"
echo "== GET /health de la API =="
curl -s -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/health || rc=1
exit $rc
