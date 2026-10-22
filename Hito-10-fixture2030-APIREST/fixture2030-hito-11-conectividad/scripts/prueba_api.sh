#!/usr/bin/env bash
# Evalúa rutas REST sin escritura/borrado de dominio; guarda status, duración y request ID.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HITO11_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT="$(cd "$HITO11_DIR/.." && pwd)"
OUT="$HITO11_DIR/docs/evidencia/resultados_api.txt"
API_URL="${API_URL:-http://127.0.0.1:8000}"
mkdir -p "$(dirname "$OUT")"
: > "$OUT"
exec > >(tee -a "$OUT") 2>&1

echo "HITO 11 — PRUEBAS DE API"
echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "sistema=$(uname -srm 2>/dev/null || echo desconocido)"
echo "git_commit=$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo sin-git-en-el-zip)"
echo "base_url_configurada=SI (valor omitido para evitar filtrar una URI sensible)"
echo "métodos=GET solamente en este modo; no modifica el dominio."
if ! command -v curl >/dev/null 2>&1; then echo "[SKIP] curl no instalado"; exit 0; fi

count=0; fail=0
declare -a request_ids=()
case_get() {
  local name="$1" path="$2" expected="$3" policy="${4:-exact}"
  count=$((count+1))
  local rid="hito11-$(date +%s)-$count" meta code duration headerfile bodyfile foundrid summary
  request_ids+=("$rid")
  headerfile="$(mktemp)"; bodyfile="$(mktemp)"
  meta=$(curl --silent --show-error --max-time 12 -H "X-Request-ID: $rid" -D "$headerfile" -o "$bodyfile" -w '%{http_code}|%{time_total}' "$API_URL$path" 2>/dev/null) || meta="000|timeout_o_api_inaccesible"
  code="${meta%%|*}"; duration="${meta#*|}"
  foundrid=$(awk 'tolower($1)=="x-request-id:" {gsub("\r", "", $2); print $2}' "$headerfile" | tail -n1)
  summary=$(python3 - "$bodyfile" <<'PY'
import json, sys
try:
    obj=json.load(open(sys.argv[1], encoding='utf-8'))
    if isinstance(obj, dict) and 'error' in obj:
        e=obj['error']; print(f"error={e.get('codigo','sin_codigo')}")
    elif isinstance(obj, dict) and isinstance(obj.get('fuentes'), dict):
        fs=obj['fuentes']; print("health="+str(obj.get('estado'))+" dependencias="+",".join(f"{k}:{v.get('estado')}" for k,v in fs.items()))
    elif isinstance(obj, dict) and isinstance(obj.get('items'), list): print(f"items={len(obj['items'])}")
    elif isinstance(obj, dict) and isinstance(obj.get('puntos'), list): print(f"puntos={len(obj['puntos'])} truncado={obj.get('truncado')}")
    elif isinstance(obj, dict) and 'nombre' in obj: print("recurso=presente")
    elif isinstance(obj, dict) and 'estado' in obj: print(f"estado={obj.get('estado')}")
    else: print("json=valido")
except Exception: print("respuesta=no_json_o_vacia")
PY
)
  local ok=0
  if [[ "$policy" == "health" ]]; then [[ "$code" == "200" ]] && ok=1
  elif [[ "$policy" == "either200404" ]]; then [[ "$code" == "200" || "$code" == "404" ]] && ok=1
  else [[ "$code" == "$expected" ]] && ok=1; fi
  if [[ "$foundrid" != "$rid" ]]; then ok=0; fi
  if [[ "$ok" -eq 1 ]]; then
    echo "[OK] caso=\"$name\" method=GET path=$path status=$code esperado=$expected politica=$policy duracion_s=$duration request_id=${foundrid:-ausente} correlacion=OK resumen=\"$summary\""
  else
    echo "[FAIL] caso=\"$name\" method=GET path=$path status=$code esperado=$expected duracion_s=$duration request_id=${foundrid:-ausente} resumen=\"$summary\" siguiente=verificar_api_dependencia_contexto_y_log"
    fail=$((fail+1))
  fi
  rm -f "$headerfile" "$bodyfile"
}

case_get "Health profundo de seis fuentes" "/health" "200" health
case_get "MongoDB equipo conocido" "/equipos/ARG" "200"
case_get "MongoDB jugadores paginados" "/equipos/ARG/jugadores?limit=2&offset=0" "200"
case_get "Neo4j partido" "/partidos/P-01" "200"
case_get "Neo4j eventos limitados" "/partidos/P-01/eventos?limit=5" "200"
case_get "Cassandra comentarios por partición completa" "/partidos/P-01/comentarios?pais=ARG&ventana=2030-06-15T18:30:00Z&limit=2" "200"
case_get "Redis clave ausente: operación válida y diagnóstico 404" "/sesiones/U999" "404"
case_get "InfluxDB consulta temporal acotada" "/partidos/P-01/estadisticas?desde=2030-06-15T18:30:00Z&hasta=2030-06-15T18:31:00Z&agregacion=1m&equipo=ARG" "200"
case_get "IRIS detalle de partido" "/partidos/P-01/detalle" "200"
case_get "Recurso Mongo inexistente" "/equipos/ZZZ" "404"
case_get "Validación de código de equipo" "/equipos/arg" "422"
case_get "Partido inexistente en grafo" "/partidos/P-99" "404"
case_get "Partido existente sin eventos: vacío válido" "/partidos/P-03/eventos" "200"
case_get "Ventana Influx sin puntos: vacío válido" "/partidos/P-05/estadisticas?desde=2030-06-15T18:30:00Z&hasta=2030-06-15T18:35:00Z&agregacion=1m" "200"
case_get "Sesión U001 (puede haber expirado naturalmente)" "/sesiones/U001" "200 o 404" either200404

echo "--- Logs correlacionados por request ID (si API corre en Compose) ---"
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1    && (cd "$ROOT" && docker compose --profile api ps --status running --services 2>/dev/null | grep -qx api); then
  logs="$(cd "$ROOT" && docker compose --profile api logs --no-color --since 10m api 2>/dev/null || true)"
  for request_id in "${request_ids[@]}"; do
    matches="$(printf '%s\n' "$logs" | grep -F "request_id=$request_id" || true)"
    if [[ -n "$matches" ]]; then printf '%s\n' "$matches"; else echo "[INFO] request_id=$request_id no apareció en el buffer de logs de los últimos 10 minutos"; fi
  done
else
  echo "[INFO] Si la API corre localmente, buscar los request_id listados arriba en la salida del proceso Uvicorn."
fi
echo "RESUMEN total=$count fail=$fail"
echo "Interpretación general: 404/422 esperados son casos de contrato aprobados; Redis U999 404 prueba clave ausente, no caída. Si /health devuelve 503, revisar el cuerpo de la respuesta y los logs para identificar la dependencia afectada."
[[ "$fail" -eq 0 ]]
