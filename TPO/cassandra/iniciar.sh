#!/usr/bin/env bash
# Deja el esquema de Cassandra como lo espera la API. Se puede correr las veces que haga falta.
#  1. Crea keyspace y tabla si no existen.
#  2. Si el keyspace venía de antes con SimpleStrategy (un solo nodo), lo pasa a una copia por región.
#     Con datos ya cargados, después de este cambio hay que correr `nodetool repair fixture2030` en cada nodo
#     para que el datacenter nuevo reciba lo que ya existía.
#  3. Agrega la columna `origen` si la tabla es anterior a ella.
set -euo pipefail
NODO=cassandra_america

cqlsh "$NODO" -f /esquema/esquema.cql

cqlsh "$NODO" -e "ALTER KEYSPACE fixture2030 WITH replication = {'class': 'NetworkTopologyStrategy', 'america': 1, 'europa': 1};"

if ! cqlsh "$NODO" -e "SELECT column_name FROM system_schema.columns WHERE keyspace_name='fixture2030' AND table_name='comentarios_por_partido_pais' AND column_name='origen';" | grep -q origen; then
  cqlsh "$NODO" -e "ALTER TABLE fixture2030.comentarios_por_partido_pais ADD origen text;"
fi

echo "Esquema de Cassandra listo: $(cqlsh "$NODO" -e "SELECT replication FROM system_schema.keyspaces WHERE keyspace_name='fixture2030';" | sed -n 4p)"
