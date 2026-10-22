#!/usr/bin/env bash
# Prueba resolución y TCP con timeouts; origen notebook y opcionalmente API en Docker.
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HITO11_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT="$(cd "$HITO11_DIR/.." && pwd)"
OUT="$HITO11_DIR/docs/evidencia/resultados_tcp.txt"
ORIGEN="${1:-auto}"
mkdir -p "$(dirname "$OUT")"
: > "$OUT"
exec > >(tee -a "$OUT") 2>&1

# Leer solo las claves permitidas; .env no se ejecuta como código de shell.
if [[ -f "$ROOT/.env" ]]; then
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" == *=* ]] || continue
    key="${line%%=*}"; value="${line#*=}"
    key="${key//[[:space:]]/}"
    case "$key" in
      MONGO_HOST|MONGO_PORT|MONGO_HOST_PORT|MONGO_USER|MONGO_PASSWORD|MONGO_DB|NEO4J_URI|NEO4J_USER|NEO4J_PASSWORD|NEO4J_DB|NEO4J_HTTP_HOST_PORT|NEO4J_HOST_PORT|CASSANDRA_HOST|CASSANDRA_PORT|CASSANDRA_HOST_PORT|CASSANDRA_KEYSPACE|REDIS_HOST|REDIS_PORT|REDIS_HOST_PORT|REDIS_PASSWORD|INFLUX_URL|INFLUX_HOST_PORT|INFLUX_DB|INFLUX_TOKEN|IRIS_HOST|IRIS_PORT|IRIS_HOST_PORT|IRIS_PORTAL_HOST_PORT|IRIS_NAMESPACE|IRIS_USER|IRIS_PASSWORD) ;;
      *) continue ;;
    esac
    if [[ "$value" == \"*\" || "$value" == \'*\' ]]; then value="${value:1:${#value}-2}"; fi
    printf -v "$key" '%s' "$value"
    export "$key"
  done < "$ROOT/.env"
  echo "configuracion=.env local presente (solo se leen claves de conexión permitidas; valores omitidos)"
else
  echo "[WARN] .env local no encontrado; se usan valores por defecto solo para la prueba TCP"
fi
export TIMEOUT_PRUEBA_SEGUNDOS="${TIMEOUT_PRUEBA_SEGUNDOS:-2}"

echo "HITO 11 — PRUEBA TCP"
for variable in MONGO_HOST MONGO_DB NEO4J_URI NEO4J_DB CASSANDRA_HOST CASSANDRA_KEYSPACE REDIS_HOST INFLUX_URL INFLUX_DB IRIS_HOST IRIS_NAMESPACE; do
  if [[ -n "${!variable:-}" ]]; then echo "config_$variable=CONFIGURADA (valor omitido)"; else echo "[WARN] config_$variable=VACIA (valor omitido)"; fi
done
for variable in MONGO_PASSWORD NEO4J_PASSWORD REDIS_PASSWORD INFLUX_TOKEN IRIS_PASSWORD; do
  if [[ -n "${!variable:-}" ]]; then echo "config_$variable=CONFIGURADA (valor omitido)"; else echo "[WARN] config_$variable=VACIA (valor omitido; driver puede rechazar autenticación)"; fi
done
echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "sistema=$(uname -srm 2>/dev/null || echo desconocido)"
echo "git_commit=$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo sin-git-en-el-zip)"
echo "proyecto=Fixture2030-Hito10+11"
echo "timeout_segundos=$TIMEOUT_PRUEBA_SEGUNDOS"
echo "origen_solicitado=$ORIGEN"
echo "Nota: TCP OK solo confirma un listener; no autentica ni ejecuta consultas."

python_probe=''
run_python_probe() {
  local source="$1"
  PROBE_ORIGIN="$source" python3 - <<'PY'
import os, socket, time, urllib.parse, http.client
origin = os.environ.get("PROBE_ORIGIN", "notebook")
timeout = float(os.environ.get("TIMEOUT_PRUEBA_SEGUNDOS", "2"))
if origin == "api-container":
    targets = [
        ("mongodb", "mongodb", 27017), ("neo4j-bolt", "neo4j", 7687),
        ("cassandra-cql", "cassandra", 9042), ("redis-resp", "redis", 6379),
        ("influx-http-listener", "influxdb", 8181), ("iris-superserver", "iris", 1972),
    ]
    http_targets = [("neo4j-browser-http", "neo4j", 7474, "/", "portal"), ("iris-portal-http", "iris", 52773, "/", "portal"), ("influxdb-health-http", "influxdb", 8181, "/health", "health")]
else:
    def integer(name, default):
        try: return int(os.environ.get(name, str(default)))
        except ValueError: return int(default)
    def uri_host_port(name, scheme_default, host_override=None, port_override=None):
        uri = os.environ.get(name, "")
        parsed = urllib.parse.urlparse(uri)
        host = host_override or parsed.hostname or "localhost"
        port = port_override or parsed.port or scheme_default
        return host, int(port)
    mh = os.environ.get("MONGO_HOST", "localhost")
    mp = integer("MONGO_HOST_PORT", integer("MONGO_PORT", 27017))
    nh, uri_np = uri_host_port("NEO4J_URI", 7687)
    np = integer("NEO4J_HOST_PORT", uri_np)
    ch = os.environ.get("CASSANDRA_HOST", "localhost")
    cp = integer("CASSANDRA_HOST_PORT", integer("CASSANDRA_PORT", 9042))
    rh = os.environ.get("REDIS_HOST", "localhost")
    rp = integer("REDIS_HOST_PORT", integer("REDIS_PORT", 6379))
    ih, uri_ip = uri_host_port("INFLUX_URL", 8181)
    ip = integer("INFLUX_HOST_PORT", uri_ip)
    irh = os.environ.get("IRIS_HOST", "localhost")
    irp = integer("IRIS_HOST_PORT", integer("IRIS_PORT", 1972))
    targets = [("mongodb", mh, mp), ("neo4j-bolt", nh, np), ("cassandra-cql", ch, cp),
               ("redis-resp", rh, rp), ("influx-http-listener", ih, ip), ("iris-superserver", irh, irp)]
    http_targets = [("neo4j-browser-http", nh, integer("NEO4J_HTTP_HOST_PORT", 7474), "/", "portal"),
                    ("iris-portal-http", irh, integer("IRIS_PORTAL_HOST_PORT", 52773), "/", "portal"),
                    ("influxdb-health-http", ih, ip, "/health", "health")]

failed = 0
for name, host, port in targets:
    start = time.monotonic()
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        print(f"[FAIL] origen={origin} dependencia={name} host_resuelto=NO host={host!r} puerto={port} diagnostico=HOST_NO_RESUELTO siguiente=verificar_nombre_y_red")
        failed += 1
        continue
    resolved = sorted({info[4][0] for info in infos})
    last = "sin dirección TCP utilizable"
    connected = False
    for family, socktype, proto, _, sockaddr in infos:
        s = socket.socket(family, socktype, proto)
        s.settimeout(timeout)
        try:
            s.connect(sockaddr)
            connected = True
            break
        except ConnectionRefusedError:
            last = "CONNECTION_REFUSED"
        except socket.timeout:
            last = "TIMEOUT"
        except OSError as exc:
            last = type(exc).__name__.upper()
        finally:
            s.close()
    elapsed = (time.monotonic() - start) * 1000
    if connected:
        print(f"[OK] origen={origin} dependencia={name} host_resuelto=SI direcciones={','.join(resolved)} puerto={port} tcp=CONNECTED duracion_ms={elapsed:.1f} conclusion=listener_accesible")
    else:
        print(f"[FAIL] origen={origin} dependencia={name} host_resuelto=SI direcciones={','.join(resolved)} puerto={port} tcp={last} duracion_ms={elapsed:.1f} siguiente=revisar_listener_publicacion_red_y_origen")
        failed += 1
# Los portales se prueban como HTTP, por separado de Bolt y del Superserver.
for name, host, port, path, kind in http_targets:
    start = time.monotonic()
    try:
        conn = http.client.HTTPConnection(host, port, timeout=timeout)
        conn.request("GET", path)
        resp = conn.getresponse(); status = resp.status
        resp.read(128); conn.close()
        ms = (time.monotonic()-start)*1000
        if kind == "health" and status == 200:
            print(f"[OK] origen={origin} dependencia={name} protocolo=HTTP path={path} host={host} puerto={port} http_status={status} duracion_ms={ms:.1f} conclusion=endpoint_salud_responde")
        elif kind == "health" and status in (401, 403):
            print(f"[OK] origen={origin} dependencia={name} protocolo=HTTP path={path} host={host} puerto={port} http_status={status} duracion_ms={ms:.1f} conclusion=endpoint_alcanzable_autenticacion_requerida; se valida_con_token_en_clientes")
        elif kind == "health":
            print(f"[FAIL] origen={origin} dependencia={name} protocolo=HTTP path={path} host={host} puerto={port} http_status={status} duracion_ms={ms:.1f} siguiente=verificar_endpoint_health_y_version_de_influx")
            failed += 1
        elif status < 500:
            print(f"[OK] origen={origin} dependencia={name} protocolo=HTTP path={path} host={host} puerto={port} http_status={status} duracion_ms={ms:.1f} conclusion=servidor_http_responde_no_valida_login")
        else:
            print(f"[FAIL] origen={origin} dependencia={name} protocolo=HTTP path={path} host={host} puerto={port} http_status={status} duracion_ms={ms:.1f} siguiente=leer_logs_del_portal")
            failed += 1
    except socket.gaierror:
        print(f"[FAIL] origen={origin} dependencia={name} protocolo=HTTP host_resuelto=NO host={host} puerto={port} siguiente=verificar_nombre_y_red")
        failed += 1
    except Exception as exc:
        ms = (time.monotonic()-start)*1000
        next_step = "verificar_endpoint_health_y_version_de_influx" if kind == "health" else "revisar_portal_y_puerto"
        print(f"[FAIL] origen={origin} dependencia={name} protocolo=HTTP path={path} host={host} puerto={port} resultado={type(exc).__name__} duracion_ms={ms:.1f} siguiente={next_step}")
        failed += 1
print(f"RESUMEN origen={origin} total={len(targets)+len(http_targets)} fail={failed}")
raise SystemExit(1 if failed else 0)
PY
}

rc=0
if [[ "$ORIGEN" == "auto" || "$ORIGEN" == "notebook" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    echo "--- Origen: notebook (misma red que API local) ---"
    run_python_probe notebook || rc=1
  else
    echo "[SKIP] notebook: python3 no instalado; instalar Python 3.12+"
  fi
fi

if [[ "$ORIGEN" == "auto" || "$ORIGEN" == "api-container" ]]; then
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1 \
     && (cd "$ROOT" && docker compose --profile api ps --status running --services 2>/dev/null | grep -qx api); then
    echo "--- Origen: contenedor api (red interna Compose, puerto interno) ---"
    if (cd "$ROOT" && docker compose --profile api exec -T api env TIMEOUT_PRUEBA_SEGUNDOS="$TIMEOUT_PRUEBA_SEGUNDOS" python - <<'PY'
import os, socket, time, http.client
origin = "api-container"
timeout = float(os.environ.get("TIMEOUT_PRUEBA_SEGUNDOS", "2"))
targets = [("mongodb", "mongodb", 27017), ("neo4j-bolt", "neo4j", 7687), ("cassandra-cql", "cassandra", 9042), ("redis-resp", "redis", 6379), ("influx-http-listener", "influxdb", 8181), ("iris-superserver", "iris", 1972)]
http_targets = [("neo4j-browser-http", "neo4j", 7474, "/", "portal"), ("iris-portal-http", "iris", 52773, "/", "portal"), ("influxdb-health-http", "influxdb", 8181, "/health", "health")]
failed = 0
for name, host, port in targets:
    t = time.monotonic()
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        print(f"[FAIL] origen={origin} dependencia={name} host_resuelto=NO host={host!r} puerto={port} diagnostico=HOST_NO_RESUELTO siguiente=revisar_service_name_y_red_compose")
        failed += 1
        continue
    ok = False; last = "SIN_CONEXION"
    for family, st, proto, _, addr in infos:
        s = socket.socket(family, st, proto); s.settimeout(timeout)
        try: s.connect(addr); ok = True; break
        except ConnectionRefusedError: last = "CONNECTION_REFUSED"
        except socket.timeout: last = "TIMEOUT"
        except OSError as exc: last = type(exc).__name__.upper()
        finally: s.close()
    ms = (time.monotonic()-t)*1000
    if ok: print(f"[OK] origen={origin} dependencia={name} host_resuelto=SI host={host} puerto={port} tcp=CONNECTED duracion_ms={ms:.1f} conclusion=listener_accesible")
    else: print(f"[FAIL] origen={origin} dependencia={name} host_resuelto=SI host={host} puerto={port} tcp={last} duracion_ms={ms:.1f} siguiente=revisar_servicio_y_puerto_interno"); failed += 1
for name, host, port, path, kind in http_targets:
    t=time.monotonic()
    try:
        conn=http.client.HTTPConnection(host,port,timeout=timeout); conn.request("GET",path)
        resp=conn.getresponse(); status=resp.status; resp.read(128); conn.close()
        ms=(time.monotonic()-t)*1000
        if kind == "health" and status == 200: print(f"[OK] origen={origin} dependencia={name} protocolo=HTTP path={path} host={host} puerto={port} http_status={status} duracion_ms={ms:.1f} conclusion=endpoint_salud_responde")
        elif kind == "health" and status in (401, 403):
            print(f"[OK] origen={origin} dependencia={name} protocolo=HTTP path={path} host={host} puerto={port} http_status={status} duracion_ms={ms:.1f} conclusion=endpoint_alcanzable_autenticacion_requerida; se valida_con_token_en_clientes")
        elif kind == "health": print(f"[FAIL] origen={origin} dependencia={name} protocolo=HTTP path={path} host={host} puerto={port} http_status={status} duracion_ms={ms:.1f} siguiente=verificar_endpoint_health_y_version_de_influx"); failed+=1
        elif status < 500: print(f"[OK] origen={origin} dependencia={name} protocolo=HTTP path={path} host={host} puerto={port} http_status={status} duracion_ms={ms:.1f} conclusion=servidor_http_responde_no_valida_login")
        else: print(f"[FAIL] origen={origin} dependencia={name} protocolo=HTTP path={path} host={host} puerto={port} http_status={status} duracion_ms={ms:.1f} siguiente=leer_logs_del_portal"); failed+=1
    except Exception as exc:
        ms=(time.monotonic()-t)*1000
        next_step = "verificar_endpoint_health_y_version_de_influx" if kind == "health" else "revisar_portal_y_service_name"
        print(f"[FAIL] origen={origin} dependencia={name} protocolo=HTTP path={path} host={host} puerto={port} resultado={type(exc).__name__} duracion_ms={ms:.1f} siguiente={next_step}"); failed+=1
print(f"RESUMEN origen={origin} total={len(targets)+len(http_targets)} fail={failed}")
raise SystemExit(1 if failed else 0)
PY
    ); then :; else rc=1; fi
  else
    echo "[SKIP] api-container: Docker Compose o contenedor api en ejecución no disponible; no se infiere que los servicios estén caídos."
    [[ "$ORIGEN" == "api-container" ]] && rc=2
  fi
fi

if [[ "$ORIGEN" != "auto" && "$ORIGEN" != "notebook" && "$ORIGEN" != "api-container" ]]; then
  echo "Uso: $0 [auto|notebook|api-container]"; exit 2
fi
exit "$rc"
