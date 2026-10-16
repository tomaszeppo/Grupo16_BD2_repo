#!/usr/bin/env bash
# Verifica puertos de cada base (desde el notebook) y el /health de la API.
cd "$(dirname "${BASH_SOURCE[0]}")/.."
rc=0
chequear() {
  if (exec 3<>"/dev/tcp/127.0.0.1/$2") 2>/dev/null; then echo "  $1 (:$2) ... accesible"; else echo "  $1 (:$2) ... NO accesible"; rc=1; fi
}
echo "== Puertos publicados por Docker en el notebook =="
chequear mongodb 27017; chequear neo4j 7687; chequear cassandra 9042
chequear redis 6379; chequear influxdb 8181; chequear iris 1972
echo "== GET /health de la API =="
curl -s -w '\nHTTP %{http_code}\n' http://127.0.0.1:8000/health || rc=1
exit $rc
