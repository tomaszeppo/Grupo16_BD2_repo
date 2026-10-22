#!/usr/bin/env bash
# Usa los drivers de la API y hace ping + lectura corta, sin escribir datos.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HITO11_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT="$(cd "$HITO11_DIR/.." && pwd)"
OUT="$HITO11_DIR/docs/evidencia/resultados_clientes.txt"
mkdir -p "$(dirname "$OUT")"
: > "$OUT"
exec > >(tee -a "$OUT") 2>&1
# Los Settings del Hito 10 leen .env mediante Pydantic; nunca se ejecuta .env como shell.

echo "HITO 11 — PRUEBAS DRIVER/PROTOCOLO Y LECTURAS MÍNIMAS"
echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "sistema=$(uname -srm 2>/dev/null || echo desconocido)"
echo "git_commit=$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo sin-git-en-el-zip)"
echo "Las salidas contienen status, duración y tipo de excepción solamente; no muestran mensajes con posibles secretos."

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1 \
   && (cd "$ROOT" && docker compose --profile api ps --status running --services 2>/dev/null | grep -qx api); then
  echo "origen=api-container (se usan los drivers y variables efectivos del servicio API)"
  (cd "$ROOT" && docker compose --profile api exec -T api python - <<'PY'
import importlib.util, time
from datetime import datetime, timezone
from app.config.settings import get_settings
from app.adapters.mongo import MongoAdapter
from app.adapters.neo4j import Neo4jAdapter
from app.adapters.cassandra import CassandraAdapter
from app.adapters.redis import RedisAdapter, clave_sesion
from app.adapters.influx import InfluxAdapter
from app.adapters.iris import IrisAdapter
s = get_settings()
def mongo_check():
    adapter = MongoAdapter(s)
    adapter.ping()
    db_exists = s.mongo_db in adapter._client.list_database_names()
    if not db_exists:
        return {"diagnostico_mongo": True, "database_exists": False, "collection_exists": False, "document_exists": False}
    collections = adapter._db().list_collection_names()
    collection_exists = "equipos" in collections
    team = adapter.obtener_equipo("ARG") if collection_exists else None
    return {"diagnostico_mongo": True, "database_exists": True, "collection_exists": collection_exists, "document_exists": team is not None}
def redis_check():
    adapter = RedisAdapter(s)
    adapter.ping()
    sesion = adapter.obtener_sesion("U001")
    clave = clave_sesion("U001")
    pipe = adapter._cli().pipeline()
    pipe.exists(clave)
    pipe.ttl(clave)
    existe, ttl = pipe.execute()
    return {"diagnostico_redis": True, "sesion_presente": sesion is not None, "clave_presente": bool(existe), "ttl_raw": int(ttl)}
checks = [
    ("mongodb", "pymongo", mongo_check, "database/colección equipos/documento codigo=ARG"),
    ("neo4j", "neo4j", lambda: (lambda a: (a.ping(), a.obtener_partido("P-01"))[1])(Neo4jAdapter(s)), "lectura parametrizada de partido P-01"),
    ("cassandra", "cassandra", lambda: (lambda a: (a.ping(), a.listar("P-01", "ARG", datetime(2030,6,15,18,30), 2, None))[1])(CassandraAdapter(s)), "SELECT limitado por partición P-01/ARG/18:30"),
    ("redis", "redis", redis_check, "PING + lectura U001 + EXISTS/TTL de la clave de demostración"),
    ("influxdb", "httpx", lambda: (lambda a: (a.ping(), a.consultar_estadisticas("P-01", datetime(2030,6,15,18,30,tzinfo=timezone.utc), datetime(2030,6,15,18,31,tzinfo=timezone.utc), "ARG", "1m", 5))[1])(InfluxAdapter(s)), "consulta temporal P-01, 1 minuto, máximo 5 puntos"),
    ("iris", "iris", lambda: (lambda a: (a.ping(), a.obtener_partido("P-01"))[1])(IrisAdapter(s)), "lectura parametrizada Fixture.Partido P-01"),
]
failed = 0; skipped = 0
for name, module, fn, detail in checks:
    start = time.monotonic()
    try:
        if importlib.util.find_spec(module) is None:
            print(f"[SKIP] dependencia={name} driver_no_instalado={module} siguiente=instalar_requirements-drivers_o_usar_imagen_api")
            skipped += 1; continue
        result = fn(); ms=(time.monotonic()-start)*1000
        if name == "mongodb" and isinstance(result, dict) and result.get("diagnostico_mongo"):
            if not result["database_exists"] or not result["collection_exists"]:
                layer = "DATABASE_NO_EXISTE" if not result["database_exists"] else "COLECCION_EQUIPOS_NO_EXISTE"
                print(f"[FAIL] dependencia=mongodb prueba=contexto diagnostico={layer} duracion_ms={ms:.1f} siguiente=verificar_MONGO_DB_y_seed_sin_crear_ni_borrar_datos")
                failed += 1
                continue
            summary = "database=presente coleccion_equipos=presente documento_ARG=" + ("presente" if result["document_exists"] else "ausente; consulta_valida_sin_documento")
        elif name == "cassandra": summary = f"filas={len(result[0])}"
        elif name == "influxdb": summary = f"puntos={len(result)}"
        elif result is None: summary = "lectura_ejecutada=si recurso_en_contexto_no_encontrado"
        elif name == "redis" and isinstance(result, dict) and result.get("diagnostico_redis"):
            if result["clave_presente"]:
                summary = f"clave=presente sesion_vigente={'si' if result['sesion_presente'] else 'no'} ttl_raw={result['ttl_raw']} interpretacion_ttl={'sin_expiracion' if result['ttl_raw'] == -1 else 'segundos_restantes' if result['ttl_raw'] >= 0 else 'revisar_ttl'}"
            else:
                summary = "clave=ausente_o_expirada TTL=-2; Redis respondio y no equivale a dependencia_caida"
        else: summary = "lectura_ejecutada=si resultado=presente"
        print(f"[OK] dependencia={name} driver={module} ping=OK lectura=OK operacion=\"{detail}\" resultado={summary} duracion_ms={ms:.1f}")
    except ModuleNotFoundError as exc:
        print(f"[SKIP] dependencia={name} driver_no_disponible=si clase_excepcion={type(exc).__name__} siguiente=instalar_driver_en_el_entorno_de_ejecucion")
        skipped += 1
    except Exception as exc:
        ms=(time.monotonic()-start)*1000
        print(f"[FAIL] dependencia={name} operacion=ping+lectura clase_excepcion={type(exc).__name__} duracion_ms={ms:.1f} siguiente=diagnosticar_configuracion_red_autenticacion_permisos_contexto_y_logs")
        failed += 1
# Diagnóstico HTTP adicional: salud y consulta se cuentan como comprobaciones independientes.
def diagnostico_http_influx(s):
    global failed, skipped
    try:
        import httpx
    except ModuleNotFoundError:
        print("[SKIP] dependencia=influxdb pruebas=HTTP_health_y_query cliente=httpx_no_instalado")
        skipped += 2
        return
    timeout = min(max(float(s.timeout_segundos), 0.1), 5.0)
    headers = {"Authorization": f"Bearer {s.influx_token}"} if s.influx_token else {}
    sql = ("SELECT time FROM estadisticas_partido WHERE partido_id = 'P-01' "
           "AND time >= '2030-06-15T18:30:00Z' AND time < '2030-06-15T18:31:00Z' LIMIT 5")
    try:
        client = httpx.Client(base_url=s.influx_url, headers=headers, timeout=httpx.Timeout(timeout))
    except Exception as exc:
        print(f"[FAIL] dependencia=influxdb prueba=cliente_HTTP clase_excepcion={type(exc).__name__} siguiente=verificar_URL_y_configuracion_sin_publicar_secretos")
        failed += 2
        return
    with client:
        start = time.monotonic()
        try:
            health = client.get("/health")
            ms = (time.monotonic() - start) * 1000
            if health.status_code == 200:
                print(f"[OK] dependencia=influxdb prueba=HTTP_health path=/health status=200 duracion_ms={ms:.1f}")
            else:
                print(f"[FAIL] dependencia=influxdb prueba=HTTP_health path=/health status={health.status_code} duracion_ms={ms:.1f} siguiente=verificar_servicio_endpoint_y_version")
                failed += 1
        except Exception as exc:
            ms = (time.monotonic() - start) * 1000
            print(f"[FAIL] dependencia=influxdb prueba=HTTP_health clase_excepcion={type(exc).__name__} duracion_ms={ms:.1f} siguiente=verificar_URL_red_y_timeout")
            failed += 1
        start = time.monotonic()
        try:
            response = client.post("/api/v3/query_sql", json={"db": s.influx_db, "q": sql, "format": "json"})
            ms = (time.monotonic() - start) * 1000
            if response.status_code == 200:
                try:
                    rows = response.json()
                    count = len(rows) if isinstance(rows, list) else "respuesta_no_lista"
                except Exception:
                    count = "json_no_interpretable"
                print(f"[OK] dependencia=influxdb prueba=consulta_temporal status=200 autenticacion=aceptada contexto_db={s.influx_db} tabla=estadisticas_partido ventana_minutos=1 limite=5 filas={count} duracion_ms={ms:.1f} conclusion=consulta_aceptada; cero_filas_es_valido")
            else:
                body = response.text.lower()[:1200]
                if response.status_code in (401, 403) or any(term in body for term in ("invalid token", "unauthorized", "authentication failed", "forbidden")):
                    diag = "TOKEN_INVALIDO_O_SIN_PERMISO"
                elif "database" in body and any(term in body for term in ("not found", "does not exist", "unknown")):
                    diag = "DATABASE_NO_EXISTE_O_NO_DISPONIBLE"
                elif "table" in body and any(term in body for term in ("not found", "does not exist", "unknown")):
                    diag = "TABLA_NO_EXISTE_O_NO_DISPONIBLE"
                else:
                    diag = "CONSULTA_O_CONTEXTO_RECHAZADO"
                print(f"[FAIL] dependencia=influxdb prueba=consulta_temporal status={response.status_code} diagnostico={diag} duracion_ms={ms:.1f} siguiente=verificar_token_permisos_database_tabla_y_consulta_sin_publicar_respuesta")
                failed += 1
        except Exception as exc:
            ms = (time.monotonic() - start) * 1000
            print(f"[FAIL] dependencia=influxdb prueba=consulta_temporal clase_excepcion={type(exc).__name__} duracion_ms={ms:.1f} siguiente=verificar_URL_contexto_y_timeout")
            failed += 1

diagnostico_http_influx(s)
print(f"RESUMEN total={len(checks)+2} fail={failed} skip={skipped} ok={len(checks)+2-failed-skipped}")
raise SystemExit(1 if failed else 0)
PY
  )
  exit $?
fi

echo "origen=notebook/local (no se encontró un contenedor api activo)"
if ! command -v python3 >/dev/null 2>&1; then
  echo "[SKIP] Python 3 no instalado; instalar Python 3.12+ y requirements-drivers.txt."
  exit 0
fi
(cd "$ROOT" && PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" python3 - <<'PY'
import importlib.util, time
from datetime import datetime, timezone
from app.config.settings import get_settings
from app.adapters.mongo import MongoAdapter
from app.adapters.neo4j import Neo4jAdapter
from app.adapters.cassandra import CassandraAdapter
from app.adapters.redis import RedisAdapter, clave_sesion
from app.adapters.influx import InfluxAdapter
from app.adapters.iris import IrisAdapter
s = get_settings()
def mongo_check():
    adapter = MongoAdapter(s)
    adapter.ping()
    db_exists = s.mongo_db in adapter._client.list_database_names()
    if not db_exists:
        return {"diagnostico_mongo": True, "database_exists": False, "collection_exists": False, "document_exists": False}
    collections = adapter._db().list_collection_names()
    collection_exists = "equipos" in collections
    team = adapter.obtener_equipo("ARG") if collection_exists else None
    return {"diagnostico_mongo": True, "database_exists": True, "collection_exists": collection_exists, "document_exists": team is not None}
def redis_check():
    adapter = RedisAdapter(s)
    adapter.ping()
    sesion = adapter.obtener_sesion("U001")
    clave = clave_sesion("U001")
    pipe = adapter._cli().pipeline()
    pipe.exists(clave)
    pipe.ttl(clave)
    existe, ttl = pipe.execute()
    return {"diagnostico_redis": True, "sesion_presente": sesion is not None, "clave_presente": bool(existe), "ttl_raw": int(ttl)}
checks = [
    ("mongodb", "pymongo", mongo_check, "database/colección equipos/documento codigo=ARG"),
    ("neo4j", "neo4j", lambda: (lambda a: (a.ping(), a.obtener_partido("P-01"))[1])(Neo4jAdapter(s)), "lectura parametrizada P-01"),
    ("cassandra", "cassandra", lambda: (lambda a: (a.ping(), a.listar("P-01", "ARG", datetime(2030,6,15,18,30), 2, None))[1])(CassandraAdapter(s)), "SELECT por partición P-01/ARG/18:30"),
    ("redis", "redis", redis_check, "PING + lectura U001 + EXISTS/TTL de la clave de demostración"),
    ("influxdb", "httpx", lambda: (lambda a: (a.ping(), a.consultar_estadisticas("P-01", datetime(2030,6,15,18,30,tzinfo=timezone.utc), datetime(2030,6,15,18,31,tzinfo=timezone.utc), "ARG", "1m", 5))[1])(InfluxAdapter(s)), "consulta P-01 acotada a 1 minuto/5 puntos"),
    ("iris", "iris", lambda: (lambda a: (a.ping(), a.obtener_partido("P-01"))[1])(IrisAdapter(s)), "lectura Fixture.Partido P-01"),
]
failed = 0; skipped = 0
for name, module, fn, detail in checks:
    start=time.monotonic()
    try:
        if importlib.util.find_spec(module) is None:
            print(f"[SKIP] dependencia={name} driver_no_instalado={module} siguiente=instalar_requirements-drivers.txt")
            skipped += 1; continue
        result=fn(); ms=(time.monotonic()-start)*1000
        if name == "mongodb" and isinstance(result, dict) and result.get("diagnostico_mongo"):
            if not result["database_exists"] or not result["collection_exists"]:
                layer="DATABASE_NO_EXISTE" if not result["database_exists"] else "COLECCION_EQUIPOS_NO_EXISTE"
                print(f"[FAIL] dependencia=mongodb prueba=contexto diagnostico={layer} duracion_ms={ms:.1f} siguiente=verificar_MONGO_DB_y_seed_sin_crear_ni_borrar_datos")
                failed+=1
                continue
            summary="database=presente coleccion_equipos=presente documento_ARG=" + ("presente" if result["document_exists"] else "ausente; consulta_valida_sin_documento")
        elif name == "cassandra": summary=f"filas={len(result[0])}"
        elif name == "influxdb": summary=f"puntos={len(result)}"
        elif result is None: summary="lectura_ejecutada=si recurso_en_contexto_no_encontrado"
        elif name == "redis" and isinstance(result, dict) and result.get("diagnostico_redis"):
            if result["clave_presente"]: summary=f"clave=presente sesion_vigente={'si' if result['sesion_presente'] else 'no'} ttl_raw={result['ttl_raw']} interpretacion_ttl={'sin_expiracion' if result['ttl_raw'] == -1 else 'segundos_restantes' if result['ttl_raw'] >= 0 else 'revisar_ttl'}"
            else: summary="clave=ausente_o_expirada TTL=-2; Redis respondio y no equivale a dependencia_caida"
        else: summary="lectura_ejecutada=si resultado=presente"
        print(f"[OK] dependencia={name} driver={module} ping=OK lectura=OK operacion=\"{detail}\" resultado={summary} duracion_ms={ms:.1f}")
    except ModuleNotFoundError as exc:
        print(f"[SKIP] dependencia={name} driver_no_disponible=si clase_excepcion={type(exc).__name__}"); skipped+=1
    except Exception as exc:
        ms=(time.monotonic()-start)*1000
        print(f"[FAIL] dependencia={name} operacion=ping+lectura clase_excepcion={type(exc).__name__} duracion_ms={ms:.1f} siguiente=diagnosticar_configuracion_red_autenticacion_permisos_contexto_y_logs"); failed+=1
# Diagnóstico HTTP adicional: salud y consulta se cuentan como comprobaciones independientes.
def diagnostico_http_influx(s):
    global failed, skipped
    try:
        import httpx
    except ModuleNotFoundError:
        print("[SKIP] dependencia=influxdb pruebas=HTTP_health_y_query cliente=httpx_no_instalado")
        skipped += 2
        return
    timeout = min(max(float(s.timeout_segundos), 0.1), 5.0)
    headers = {"Authorization": f"Bearer {s.influx_token}"} if s.influx_token else {}
    sql = ("SELECT time FROM estadisticas_partido WHERE partido_id = 'P-01' "
           "AND time >= '2030-06-15T18:30:00Z' AND time < '2030-06-15T18:31:00Z' LIMIT 5")
    try:
        client = httpx.Client(base_url=s.influx_url, headers=headers, timeout=httpx.Timeout(timeout))
    except Exception as exc:
        print(f"[FAIL] dependencia=influxdb prueba=cliente_HTTP clase_excepcion={type(exc).__name__} siguiente=verificar_URL_y_configuracion_sin_publicar_secretos")
        failed += 2
        return
    with client:
        start = time.monotonic()
        try:
            health = client.get("/health")
            ms = (time.monotonic() - start) * 1000
            if health.status_code == 200:
                print(f"[OK] dependencia=influxdb prueba=HTTP_health path=/health status=200 duracion_ms={ms:.1f}")
            else:
                print(f"[FAIL] dependencia=influxdb prueba=HTTP_health path=/health status={health.status_code} duracion_ms={ms:.1f} siguiente=verificar_servicio_endpoint_y_version")
                failed += 1
        except Exception as exc:
            ms = (time.monotonic() - start) * 1000
            print(f"[FAIL] dependencia=influxdb prueba=HTTP_health clase_excepcion={type(exc).__name__} duracion_ms={ms:.1f} siguiente=verificar_URL_red_y_timeout")
            failed += 1
        start = time.monotonic()
        try:
            response = client.post("/api/v3/query_sql", json={"db": s.influx_db, "q": sql, "format": "json"})
            ms = (time.monotonic() - start) * 1000
            if response.status_code == 200:
                try:
                    rows = response.json()
                    count = len(rows) if isinstance(rows, list) else "respuesta_no_lista"
                except Exception:
                    count = "json_no_interpretable"
                print(f"[OK] dependencia=influxdb prueba=consulta_temporal status=200 autenticacion=aceptada contexto_db={s.influx_db} tabla=estadisticas_partido ventana_minutos=1 limite=5 filas={count} duracion_ms={ms:.1f} conclusion=consulta_aceptada; cero_filas_es_valido")
            else:
                body = response.text.lower()[:1200]
                if response.status_code in (401, 403) or any(term in body for term in ("invalid token", "unauthorized", "authentication failed", "forbidden")):
                    diag = "TOKEN_INVALIDO_O_SIN_PERMISO"
                elif "database" in body and any(term in body for term in ("not found", "does not exist", "unknown")):
                    diag = "DATABASE_NO_EXISTE_O_NO_DISPONIBLE"
                elif "table" in body and any(term in body for term in ("not found", "does not exist", "unknown")):
                    diag = "TABLA_NO_EXISTE_O_NO_DISPONIBLE"
                else:
                    diag = "CONSULTA_O_CONTEXTO_RECHAZADO"
                print(f"[FAIL] dependencia=influxdb prueba=consulta_temporal status={response.status_code} diagnostico={diag} duracion_ms={ms:.1f} siguiente=verificar_token_permisos_database_tabla_y_consulta_sin_publicar_respuesta")
                failed += 1
        except Exception as exc:
            ms = (time.monotonic() - start) * 1000
            print(f"[FAIL] dependencia=influxdb prueba=consulta_temporal clase_excepcion={type(exc).__name__} duracion_ms={ms:.1f} siguiente=verificar_URL_contexto_y_timeout")
            failed += 1

diagnostico_http_influx(s)
print(f"RESUMEN total={len(checks)+2} fail={failed} skip={skipped} ok={len(checks)+2-failed-skipped}")
raise SystemExit(1 if failed else 0)
PY
)
