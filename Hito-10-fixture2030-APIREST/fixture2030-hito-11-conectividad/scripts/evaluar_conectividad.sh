#!/usr/bin/env bash
# Orquestador: todo | tcp | native | api | fallo-redis
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HITO11_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT="$(cd "$HITO11_DIR/.." && pwd)"
MODE="${1:-todo}"
case "$MODE" in
  todo|tcp|native|api|fallo-redis) ;;
  *) echo "Uso: $0 [todo|tcp|native|api|fallo-redis]" >&2; exit 2 ;;
esac

run_step() {
  local label="$1"; shift
  echo
  echo "===== $label ====="
  (cd "$ROOT" && "$@")
  local rc=$?
  echo "resultado_paso=$label exit_code=$rc"
  return "$rc"
}

if [[ "$MODE" == "tcp" ]]; then run_step TCP bash "$SCRIPT_DIR/prueba_tcp.sh" auto; exit $?; fi
if [[ "$MODE" == "native" ]]; then run_step CLIENTES bash "$SCRIPT_DIR/prueba_clientes_nativos.sh"; exit $?; fi
if [[ "$MODE" == "api" ]]; then run_step API bash "$SCRIPT_DIR/prueba_api.sh"; exit $?; fi
if [[ "$MODE" == "fallo-redis" ]]; then
  OUT="$HITO11_DIR/docs/evidencia/resultados_api.txt"
  mkdir -p "$(dirname "$OUT")"
  touch "$OUT"
  exec > >(tee -a "$OUT") 2>&1
  echo "HITO 11 — FALLA CONTROLADA Y RECUPERACIÓN REDIS"
  echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "sistema=$(uname -srm 2>/dev/null || echo desconocido)"
echo "git_commit=$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo sin-git-en-el-zip)"
  echo "Operación reversible: docker compose stop/start redis; no se eliminan bases ni volúmenes."
  if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
    echo "[SKIP] Docker Compose no disponible; no se detuvo ningún servicio."; exit 2
  fi
  if ! (cd "$ROOT" && docker compose --profile api ps --status running --services 2>/dev/null | grep -qx redis); then
    echo "[SKIP] Redis no está en ejecución en el proyecto Compose esperado; no se detuvo ningún servicio."; exit 2
  fi
  API_URL="${API_URL:-http://127.0.0.1:8000}"
  restored=0
  restore_redis() {
    if [[ "$restored" -eq 0 ]]; then
      echo "RECUPERACIÓN: intentando docker compose start redis"
      (cd "$ROOT" && docker compose start redis >/dev/null 2>&1) || echo "[FAIL] no se pudo restaurar Redis automáticamente; ejecutar: docker compose start redis"
    fi
  }
  trap restore_redis EXIT INT TERM
  (cd "$ROOT" && docker compose stop redis) || { echo "[FAIL] no se pudo detener Redis"; exit 1; }
  echo "[OK] Redis detenido temporalmente (sin eliminar el volumen)."
  sleep 2
  rid="hito11-fallo-redis-$(date +%s)"
  meta=$(curl -sS --max-time 12 -H "X-Request-ID: $rid" -o /tmp/hito11-redis-fallo-body -D /tmp/hito11-redis-fallo-head -w '%{http_code}|%{time_total}' "$API_URL/sesiones/U001" 2>/dev/null) || meta="000|timeout_o_api_inaccesible"
  code="${meta%%|*}"; duration="${meta#*|}"
  errcode=$(python3 - /tmp/hito11-redis-fallo-body <<'PY'
import json,sys
try:
 d=json.load(open(sys.argv[1],encoding="utf-8")); print(d.get("error",{}).get("codigo","respuesta_no_error"))
except Exception: print("respuesta_no_json")
PY
)
  actualrid=$(awk 'tolower($1)=="x-request-id:" {gsub("\r", "", $2); print $2}' /tmp/hito11-redis-fallo-head 2>/dev/null | tail -n1)
  echo "cuerpo_resumido=$errcode"
  fallorc=0
  if [[ "$code" == "503" && "$errcode" == "DEPENDENCIA_NO_DISPONIBLE" && "$actualrid" == "$rid" ]]; then
    echo "[OK] Durante caída: GET /sesiones/U001 HTTP $code error=$errcode duracion_s=$duration request_id=$actualrid correlacion=OK."
  else
    echo "[FAIL] Durante caída: se esperaba HTTP 503/error DEPENDENCIA_NO_DISPONIBLE y request ID correlacionado; status=$code error=$errcode duracion_s=$duration request_id_solicitado=$rid request_id_recibido=${actualrid:-ausente}"
    fallorc=1
  fi
  echo "RECUPERACIÓN: levantando Redis sin tocar volúmenes"
  (cd "$ROOT" && docker compose start redis) || { echo "[FAIL] docker compose start redis falló"; exit 1; }
  ready=0
  for _ in $(seq 1 60); do
    if (cd "$ROOT" && docker compose exec -T redis sh -lc 'redis-cli -a "$REDIS_PASSWORD" --no-auth-warning ping 2>/dev/null | grep -q PONG') >/dev/null 2>&1; then ready=1; break; fi
    sleep 2
  done
  if [[ "$ready" -eq 1 ]]; then
    restored=1
    echo "[OK] Redis volvió a responder PONG."
  else
    echo "[FAIL] Redis no volvió a responder en 120 segundos. Revisar docker compose logs redis; no ejecutar down -v."
    exit 1
  fi
  rid2="hito11-redis-recuperado-$(date +%s)"
  meta2=$(curl -sS --max-time 12 -H "X-Request-ID: $rid2" -o /tmp/hito11-redis-recuperado-body -D /tmp/hito11-redis-recuperado-head -w '%{http_code}|%{time_total}' "$API_URL/health" 2>/dev/null) || meta2="000|timeout_o_api_inaccesible"
  code2="${meta2%%|*}"; dur2="${meta2#*|}"
  actualrid2=$(awk 'tolower($1)=="x-request-id:" {gsub("\r", "", $2); print $2}' /tmp/hito11-redis-recuperado-head 2>/dev/null | tail -n1)
  if [[ "$code2" == "200" && "$actualrid2" == "$rid2" ]]; then
    echo "[OK] Después de recuperar: GET /health HTTP $code2 duracion_s=$dur2 request_id=$actualrid2 correlacion=OK."
  elif [[ "$code2" == "503" ]]; then
    echo "[WARN] Redis se restauró, pero /health continúa degradado (HTTP 503) duracion_s=$dur2 request_id=${actualrid2:-ausente}; revisar otras fuentes."
  else
    echo "[FAIL] Después de recuperar: /health status=$code2 request_id_solicitado=$rid2 request_id_recibido=${actualrid2:-ausente}; revisar API y logs."
    fallorc=1
  fi
  rm -f /tmp/hito11-redis-fallo-body /tmp/hito11-redis-fallo-head /tmp/hito11-redis-recuperado-body /tmp/hito11-redis-recuperado-head
  trap - EXIT INT TERM
  exit "$fallorc"
fi

allrc=0
run_step TCP bash "$SCRIPT_DIR/prueba_tcp.sh" auto || allrc=1
run_step CLIENTES bash "$SCRIPT_DIR/prueba_clientes_nativos.sh" || allrc=1
run_step API bash "$SCRIPT_DIR/prueba_api.sh" || allrc=1

echo
echo "===== RESUMEN DE ARCHIVOS ====="
echo "$HITO11_DIR/docs/evidencia/resultados_tcp.txt"
echo "$HITO11_DIR/docs/evidencia/resultados_clientes.txt"
echo "$HITO11_DIR/docs/evidencia/resultados_api.txt"
echo "Revisar SKIP y UNKNOWN separadamente de FAIL; después actualizar docs/matriz_de_conectividad.md."
exit "$allrc"
