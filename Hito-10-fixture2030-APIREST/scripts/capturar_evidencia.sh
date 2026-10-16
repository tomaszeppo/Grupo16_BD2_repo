#!/usr/bin/env bash
# Genera docs/evidencia/<fecha>_endpoints.txt con la respuesta real de cada endpoint y escenario de error.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
BASE="${BASE:-http://127.0.0.1:8000}"
V="2030-06-15T18:30:00Z"
SALIDA="docs/evidencia/$(date +%Y%m%d_%H%M%S)_endpoints.txt"
mkdir -p docs/evidencia
{
  echo "# Evidencia de endpoints — $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "# Obtenida con: bash scripts/capturar_evidencia.sh contra $BASE (stack levantado con scripts/levantar_servicios.sh)"
  caso() {
    local titulo="$1"; shift
    echo; echo "## $titulo"; echo "\$ curl -s -i $*"
    curl -s -i "$@" | tr -d '\r' | grep -v -i -E '^(set-cookie|server|date):' | head -n 40
    echo
  }
  caso "Salud de las seis dependencias" "$BASE/health"
  caso "MongoDB · equipo (200)" "$BASE/equipos/ARG"
  caso "MongoDB · equipo inexistente (404)" "$BASE/equipos/ZZZ"
  caso "MongoDB · validación (422)" "$BASE/equipos/arg"
  caso "MongoDB · jugadores paginados (200)" "$BASE/equipos/ARG/jugadores?limit=2&offset=1"
  caso "Neo4j · partido (200)" "$BASE/partidos/P-01"
  caso "Neo4j · eventos (200)" "$BASE/partidos/P-01/eventos"
  caso "Neo4j · partido sin eventos (200 vacío)" "$BASE/partidos/P-03/eventos"
  caso "Neo4j · partido inexistente (404)" "$BASE/partidos/P-99"
  caso "Cassandra · comentarios (200)" "$BASE/partidos/P-01/comentarios?pais=ARG&ventana=$V&limit=2"
  KEY="evidencia-$(date +%s)"
  caso "Cassandra · alta (201)" -X POST "$BASE/partidos/P-01/comentarios" -H "Idempotency-Key: $KEY" -H 'Content-Type: application/json' -d '{"pais":"ARG","usuario_id":"U001","usuario_nombre":"Facundo","contenido":"Comentario de evidencia"}'
  caso "Cassandra · repetición idempotente (200)" -X POST "$BASE/partidos/P-01/comentarios" -H "Idempotency-Key: $KEY" -H 'Content-Type: application/json' -d '{"pais":"ARG","usuario_id":"U001","usuario_nombre":"Facundo","contenido":"Comentario de evidencia"}'
  caso "Cassandra · misma clave, otro partido (409)" -X POST "$BASE/partidos/P-02/comentarios" -H "Idempotency-Key: $KEY" -H 'Content-Type: application/json' -d '{"pais":"ARG","usuario_id":"U001","usuario_nombre":"Facundo","contenido":"Comentario de evidencia"}'
  caso "Redis · sesión vigente (200)" "$BASE/sesiones/U001"
  caso "Redis · sesión inexistente o expirada (404)" "$BASE/sesiones/U999"
  caso "InfluxDB · ventana agregada (200)" "$BASE/partidos/P-01/estadisticas?desde=$V&hasta=2030-06-15T18:33:00Z&agregacion=1m&equipo=ARG"
  caso "InfluxDB · fechas invertidas (422)" "$BASE/partidos/P-01/estadisticas?desde=2030-06-15T18:35:00Z&hasta=$V"
  caso "IRIS · detalle (200)" "$BASE/partidos/P-01/detalle"
  caso "IRIS · transición inválida (409)" -X POST "$BASE/partidos/P-03/estado" -H 'Content-Type: application/json' -d '{"estado":"Finalizado"}'
} > "$SALIDA"
echo "Evidencia escrita en $SALIDA"
