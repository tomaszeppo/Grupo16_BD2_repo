#!/usr/bin/env bash
# Ejemplos cURL. Requiere la API en $BASE (por defecto http://localhost:8000). No usa secretos.
BASE="${BASE:-http://localhost:8000}"
V="2030-06-15T18:30:00Z"
c() { echo; echo "\$ curl $*"; curl -s -i "$@" | tr -d '\r' | sed -n '1p;/^[Xx]-[Rr]equest-[Ii][Dd]/p;$p'; }

c "$BASE/health"
c "$BASE/equipos/ARG"                                   # 200
c "$BASE/equipos/ZZZ"                                   # 404
c "$BASE/equipos/arg"                                   # 422
c "$BASE/equipos/ARG/jugadores?limit=2&offset=1"        # 200 paginado
c "$BASE/partidos/P-01"                                 # 200 (Neo4j)
c "$BASE/partidos/P-99"                                 # 404
c "$BASE/partidos/P-01/eventos"                         # 200
c "$BASE/partidos/P-01/comentarios?pais=ARG&ventana=$V&limit=2"   # 200 (Cassandra)
KEY="curl-$(date +%s)"
c -X POST "$BASE/partidos/P-01/comentarios" -H "Idempotency-Key: $KEY" -H 'Content-Type: application/json' \
  -d '{"pais":"ARG","usuario_id":"U001","usuario_nombre":"Facundo","contenido":"Hola desde cURL"}'   # 201
c -X POST "$BASE/partidos/P-01/comentarios" -H "Idempotency-Key: $KEY" -H 'Content-Type: application/json' \
  -d '{"pais":"ARG","usuario_id":"U001","usuario_nombre":"Facundo","contenido":"Hola desde cURL"}'   # 200 repetición
c "$BASE/sesiones/U001"                                 # 200 (Redis)
c "$BASE/sesiones/U999"                                 # 404
c "$BASE/partidos/P-01/estadisticas?desde=$V&hasta=2030-06-15T18:35:00Z&agregacion=1m"   # 200 (InfluxDB)
c "$BASE/partidos/P-01/estadisticas?desde=2030-06-15T18:35:00Z&hasta=$V"                 # 422
c "$BASE/partidos/P-01/detalle"                         # 200 (IRIS)
c -X POST "$BASE/partidos/P-03/estado" -H 'Content-Type: application/json' -d '{"estado":"Finalizado"}'   # 409
