"""Los tres momentos de la demo y la captura de evidencia. Lo invoca ejecutar_prueba_controlada.ps1.

  normal  lecturas moderadas contra las seis bases: la línea de base para comparar
  pico    ráfaga de comentarios por país (scripts/carga_comentarios.py) contra la API instrumentada
  estado  transición Programado -> En juego -> Finalizado de un partido en IRIS
  falla   docker stop / start del contenedor de Redis con tráfico de fondo; registra antes, durante y después
  capturar  renderiza los paneles de Grafana y exporta las series de Prometheus de una ventana de tiempo

Todo se escribe en evidencia/ con fecha y commit. No borra datos ni volúmenes: Redis se detiene y se vuelve a iniciar.
"""
import argparse
import json
import os
import subprocess
import sys
import threading
import time
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[1]
EVIDENCIA = RAIZ / "evidencia"
API = "http://127.0.0.1:8001"
PROMETHEUS = "http://127.0.0.1:9090"
GRAFANA = "http://127.0.0.1:3000"
REDIS = "fixture2030-api-redis-1"


def ahora():
    return datetime.now(timezone.utc)


def commit():
    return subprocess.run(["git", "-C", str(RAIZ), "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True).stdout.strip()


def guardar(nombre, datos):
    EVIDENCIA.mkdir(exist_ok=True)
    ruta = EVIDENCIA / nombre
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Guardado:", ruta.relative_to(RAIZ))
    return ruta


def foto(cliente):
    """Estado observable en un instante: health de la API, una sesión y las alertas activas de Prometheus."""
    def pedir(metodo, url, **kw):
        try:
            r = cliente.request(metodo, url, timeout=10, **kw)
            return {"codigo": r.status_code, "cuerpo": r.json() if r.content else None}
        except httpx.HTTPError as exc:
            return {"codigo": None, "error": type(exc).__name__}

    alertas = pedir("GET", f"{PROMETHEUS}/api/v1/alerts")
    return {
        "hora_utc": ahora().isoformat(),
        "health": pedir("GET", f"{API}/health"),
        "sesion_U001": pedir("GET", f"{API}/sesiones/U001"),
        "alertas_prometheus": [
            {"alerta": a["labels"]["alertname"], "estado": a["state"], "fuente": a["labels"].get("fuente"),
             "job": a["labels"].get("job"), "desde": a.get("activeAt")}
            for a in (alertas.get("cuerpo") or {}).get("data", {}).get("alerts", [])
        ],
    }


# Una lectura por base: así la operación normal deja datos en todos los paneles de duración por base.
LECTURAS_NORMALES = (
    ("redis", "/sesiones/U001", {}),
    ("mongodb", "/equipos/ARG/jugadores", {}),
    ("neo4j", "/partidos/P-01", {}),
    ("neo4j", "/partidos/P-01/eventos", {}),
    ("iris", "/partidos/P-01/detalle", {}),
    ("influxdb", "/partidos/P-01/estadisticas",
     {"desde": "2030-06-15T18:30:00Z", "hasta": "2030-06-15T18:40:00Z", "agregacion": "1m"}),
    ("cassandra", "/partidos/P-01/comentarios", {"pais": "ARG", "ventana": "2030-06-15T18:30:00Z"}),
)


def percentil(valores, p):
    """Percentil por rango más cercano, el mismo criterio que usamos para el pico."""
    if not valores:
        return None
    orden = sorted(valores)
    return orden[max(0, min(len(orden) - 1, round(p / 100 * len(orden) + 0.5) - 1))]


def momento_normal(args):
    """Tráfico de lectura moderado contra las seis bases: es la línea de base con la que se comparan las demás situaciones."""
    print(f"Operación normal: {args.duracion} s de lecturas contra las seis bases")
    codigos = Counter()
    duraciones = {}
    fin = time.monotonic() + args.duracion
    inicio = ahora()
    with httpx.Client(base_url=API, timeout=10) as c:
        while time.monotonic() < fin:
            for fuente, url, params in LECTURAS_NORMALES:
                t = time.perf_counter()
                try:
                    r = c.get(url, params=params)
                    codigos[f"{fuente} {r.status_code}"] += 1
                except httpx.HTTPError as exc:
                    codigos[f"{fuente} {type(exc).__name__}"] += 1
                duraciones.setdefault(fuente, []).append((time.perf_counter() - t) * 1000)
            time.sleep(0.5)
    registro = {
        "commit": commit(),
        "ventana_utc": {"desde": inicio.isoformat(), "hasta": ahora().isoformat()},
        "respuestas_por_base": dict(sorted(codigos.items())),
        "tiempo_cliente_ms": {
            fuente: {"pedidos": len(v), "p50": round(percentil(v, 50), 2), "p95": round(percentil(v, 95), 2)}
            for fuente, v in sorted(duraciones.items())
        },
    }
    print(json.dumps(registro["respuestas_por_base"], ensure_ascii=False))
    guardar(f"operacion_normal_{datetime.now():%Y%m%d_%H%M%S}.json", registro)


def momento_pico(args):
    cmd = [sys.executable, str(RAIZ / "scripts" / "carga_comentarios.py"), "--partido", args.partido,
           "--cantidad", str(args.cantidad), "--tasa", str(args.tasa),
           "--salida", str(EVIDENCIA / "resultados_sin_secretos")]
    print("Pico de comentarios:", " ".join(cmd[1:]))
    subprocess.run(cmd, check=True, cwd=RAIZ)


def momento_estado(args):
    registro = {"commit": commit(), "partido": args.partido_estado, "pasos": []}
    with httpx.Client(base_url=API, timeout=10) as c:
        registro["pasos"].append({"accion": "GET detalle (antes)", "hora_utc": ahora().isoformat(),
                                  **respuesta(c.get(f"/partidos/{args.partido_estado}/detalle"))})
        for estado in ("En juego", "Finalizado", "En juego"):
            r = c.post(f"/partidos/{args.partido_estado}/estado", json={"estado": estado})
            registro["pasos"].append({"accion": f"POST estado = {estado}", "hora_utc": ahora().isoformat(),
                                      **respuesta(r)})
            time.sleep(2)
    # El último paso (volver a "En juego" desde "Finalizado") debe ser rechazado: la transición no tiene vuelta atrás.
    guardar(f"estado_partido_{datetime.now():%Y%m%d_%H%M%S}.json", registro)


def respuesta(r):
    try:
        cuerpo = r.json()
    except ValueError:
        cuerpo = r.text[:300]
    return {"codigo": r.status_code, "cuerpo": cuerpo}


def _docker(cmd):
    subprocess.run(cmd, check=True, capture_output=True)


@contextmanager
def contenedor_detenido(nombre, ejecutar=_docker):
    """Detiene el contenedor y lo vuelve a iniciar siempre, aunque la prueba se corte en el medio."""
    print("docker stop", nombre)
    ejecutar(["docker", "stop", nombre])
    try:
        yield
    finally:
        print("docker start", nombre)
        ejecutar(["docker", "start", nombre])


def momento_falla(args):
    """Tráfico de fondo constante (sesiones, partidos, comentarios) para que el panel muestre el cambio."""
    detener = threading.Event()
    conteo = Counter()

    def fondo():
        n = 0
        with httpx.Client(base_url=API, timeout=5) as c:
            while not detener.is_set():
                for metodo, url, kw in (
                    ("GET", "/sesiones/U001", {}),
                    ("GET", f"/partidos/{args.partido}", {}),
                    ("POST", f"/partidos/{args.partido}/comentarios",
                     {"json": {"pais": "URU", "usuario_id": "U900", "usuario_nombre": "Fondo",
                               "contenido": f"Tráfico de fondo durante la prueba de falla #{n}"},
                      "headers": {"Idempotency-Key": f"h13-falla-{datetime.now():%Y%m%d%H%M%S}-{n:05d}"}}),
                ):
                    try:
                        r = c.request(metodo, url, **kw)
                        conteo[f"{metodo} {url.split('/')[1]} {r.status_code}"] += 1
                    except httpx.HTTPError as exc:
                        conteo[f"{metodo} {url.split('/')[1]} {type(exc).__name__}"] += 1
                n += 1
                time.sleep(0.25)

    registro = {"commit": commit(), "contenedor": REDIS, "fases": {}}
    hilo = threading.Thread(target=fondo, daemon=True)
    with httpx.Client(timeout=10) as c:
        inicio = ahora()
        hilo.start()
        time.sleep(args.antes)
        registro["fases"]["antes"] = foto(c)

        registro["detenido_utc"] = ahora().isoformat()
        with contenedor_detenido(REDIS):
            time.sleep(15)
            registro["fases"]["durante_15s"] = foto(c)
            time.sleep(max(0, args.caida - 15))
            registro["fases"]["durante_fin"] = foto(c)
        registro["iniciado_utc"] = ahora().isoformat()
        time.sleep(args.despues)
        registro["fases"]["despues"] = foto(c)
        detener.set()
        hilo.join()
        registro["ventana_utc"] = {"desde": inicio.isoformat(), "hasta": ahora().isoformat()}
    registro["trafico_de_fondo"] = dict(sorted(conteo.items()))
    nombre = f"prueba_de_falla_{datetime.now():%Y%m%d_%H%M%S}.json"
    guardar(nombre, registro)


PANELES = {1: "disponibilidad_bases", 15: "disponibilidad_en_el_tiempo", 12: "destinos_up", 2: "pedidos_por_endpoint", 3: "errores_por_codigo",
           9: "proporcion_5xx", 4: "latencia_p95_p99", 5: "comentarios_por_pais", 6: "p99_post_comentarios",
           7: "duracion_por_base", 10: "mongodb_operaciones", 8: "redis_memoria", 11: "redis_comandos",
           13: "api_cpu", 14: "api_memoria"}

CONSULTAS = {
    "disponibilidad": "fixture2030_dependencia_disponible",
    "pedidos_por_codigo_por_s": "sum by (codigo) (rate(fixture2030_http_requests_total[1m]))",
    "p99_post_comentarios_s": 'histogram_quantile(0.99, sum by (le) (rate(fixture2030_http_request_duration_seconds_bucket{endpoint="/partidos/{partido_id}/comentarios", metodo="POST"}[1m])))',
    "comentarios_por_pais_por_s": "sum by (pais) (rate(fixture2030_comentarios_creados_total[1m]))",
    "p95_por_base_s": "histogram_quantile(0.95, sum by (le, fuente) (rate(fixture2030_dependencia_duracion_seconds_bucket[1m])))",
}


def capturar(args):
    desde = datetime.fromisoformat(args.desde)
    hasta = datetime.fromisoformat(args.hasta)
    carpeta = EVIDENCIA / "dashboards" / args.nombre
    carpeta.mkdir(parents=True, exist_ok=True)
    clave = os.environ.get("GRAFANA_ADMIN_PASSWORD") or leer_env("GRAFANA_ADMIN_PASSWORD")
    ms = lambda d: str(int(d.timestamp() * 1000))  # noqa: E731
    with httpx.Client(auth=("admin", clave), timeout=120) as c:
        for panel, nombre in PANELES.items():
            r = c.get(f"{GRAFANA}/render/d-solo/fixture2030", params={
                "orgId": 1, "panelId": panel, "from": ms(desde), "to": ms(hasta),
                "width": 1100, "height": 450, "tz": "America/Argentina/Buenos_Aires"})
            r.raise_for_status()
            (carpeta / f"{panel:02d}_{nombre}.png").write_bytes(r.content)
        series = {}
        for nombre, q in CONSULTAS.items():
            r = c.get(f"{PROMETHEUS}/api/v1/query_range", params={
                "query": q, "start": desde.timestamp(), "end": hasta.timestamp(), "step": "5s"})
            series[nombre] = {"consulta": q, "paso": "5s", "resultado": r.json()["data"]["result"]}
    (carpeta / "series_prometheus.json").write_text(
        json.dumps({"desde_utc": args.desde, "hasta_utc": args.hasta, "commit": commit(), "series": series},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print("Capturas y series en", carpeta.relative_to(RAIZ))


def leer_env(clave):
    for linea in (RAIZ / ".env").read_text(encoding="utf-8").splitlines():
        if linea.startswith(clave + "="):
            return linea.split("=", 1)[1].strip()
    raise SystemExit(f"Falta {clave} en .env")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="momento", required=True)
    n = sub.add_parser("normal")
    n.add_argument("--duracion", type=int, default=40)
    p = sub.add_parser("pico")
    p.add_argument("--partido", default="P-01")
    p.add_argument("--cantidad", type=int, default=3000)
    p.add_argument("--tasa", type=float, default=50)
    e = sub.add_parser("estado")
    e.add_argument("--partido-estado", default="P-03")
    f = sub.add_parser("falla")
    f.add_argument("--partido", default="P-01")
    f.add_argument("--antes", type=int, default=30)
    f.add_argument("--caida", type=int, default=75)
    f.add_argument("--despues", type=int, default=45)
    c = sub.add_parser("capturar")
    c.add_argument("--desde", required=True, help="ISO-8601 con zona")
    c.add_argument("--hasta", required=True)
    c.add_argument("--nombre", required=True)
    args = ap.parse_args()
    {"normal": momento_normal, "pico": momento_pico, "estado": momento_estado, "falla": momento_falla, "capturar": capturar}[args.momento](args)


if __name__ == "__main__":
    main()
