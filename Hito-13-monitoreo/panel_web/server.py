from __future__ import annotations

import asyncio
import json
import os
import time
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

HITO13_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = Path(__file__).resolve().parent / "static"
SCRIPT_CONTROLADO = HITO13_DIR / "scripts" / "prueba_controlada.py"

API_URL = os.getenv("FIXTURE_API_URL", "http://127.0.0.1:8001").rstrip("/")
PROMETHEUS_URL = os.getenv("FIXTURE_PROMETHEUS_URL", "http://127.0.0.1:9090").rstrip("/")
GRAFANA_URL = os.getenv("FIXTURE_GRAFANA_URL", "http://127.0.0.1:3000").rstrip("/")
REDIS_CONTAINER = os.getenv("FIXTURE_REDIS_CONTAINER", "fixture2030-api-redis-1")

QUERIES: dict[str, str] = {
    "availability": "fixture2030_dependencia_disponible",
    "rps": "sum(rate(fixture2030_http_requests_total[1m]))",
    "p95": "histogram_quantile(0.95, sum by (le) (rate(fixture2030_http_request_duration_seconds_bucket[1m])))",
    "p99": "histogram_quantile(0.99, sum by (le) (rate(fixture2030_http_request_duration_seconds_bucket[1m])))",
    "db_p95": "histogram_quantile(0.95, sum by (le, fuente) (rate(fixture2030_dependencia_duracion_seconds_bucket[1m])))",
    "comments": "sum by (pais) (rate(fixture2030_comentarios_creados_total[1m]))",
    "cpu": 'rate(process_cpu_seconds_total{job="api"}[1m]) * 100',
    "memory": 'process_resident_memory_bytes{job="api"} / 1024 / 1024',
    "mongo_ops": 'sum by (type) (rate(mongodb_op_counters_total{job="mongodb"}[1m]))',
    "redis_commands": 'rate(redis_commands_processed_total{job="redis"}[1m])',
    "error_rate": 'sum(rate(fixture2030_http_requests_total{codigo=~"5.."}[1m])) / clamp_min(sum(rate(fixture2030_http_requests_total[1m])), 0.001) * 100',
    "targets_up": "up",
    "redis_memory": 'redis_memory_used_bytes{job="redis"} / 1024 / 1024',
    "redis_memory_max": 'redis_memory_max_bytes{job="redis"} / 1024 / 1024',
    # Las mismas vistas que Grafana: pedidos por endpoint, respuestas por código y el p99 que vigila la alerta.
    "by_endpoint": "sum by (endpoint, metodo) (rate(fixture2030_http_requests_total[1m]))",
    "by_code": "sum by (codigo) (rate(fixture2030_http_requests_total[1m]))",
    "p99_post_comments": 'histogram_quantile(0.99, sum by (le) (rate(fixture2030_http_request_duration_seconds_bucket{endpoint="/partidos/{partido_id}/comentarios", metodo="POST"}[1m])))',
}

app = FastAPI(
    title="Fixture 2030 · Panel de monitoreo",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    description="Panel local para visualizar Prometheus y ejecutar las pruebas controladas del Hito 13.",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

_JOB_LOCK = threading.Lock()
_JOB: dict | None = None
_JOB_LOG_LIMIT = 300


class RunRequest(BaseModel):
    scenario: Literal["pico", "estado", "falla"]
    cantidad: int = Field(default=3000, ge=100, le=6000)
    tasa: float = Field(default=50, gt=0, le=100)
    partido: Literal["P-02", "P-06", "P-07", "P-08"] = "P-06"
    confirmar: bool = False


class RecorridoRequest(BaseModel):
    cantidad: int = Field(default=3000, ge=100, le=6000)
    tasa: float = Field(default=50, gt=0, le=100)
    confirmar: bool = False


async def _get_json(client: httpx.AsyncClient, url: str, **kwargs) -> dict:
    response = await client.get(url, **kwargs)
    response.raise_for_status()
    return response.json()


async def _query_range(client: httpx.AsyncClient, name: str, expression: str, start: float, end: float, step: int):
    try:
        result = await _get_json(
            client,
            f"{PROMETHEUS_URL}/api/v1/query_range",
            params={"query": expression, "start": start, "end": end, "step": step},
        )
        if result.get("status") != "success":
            return name, []
        return name, result.get("data", {}).get("result", [])
    except (httpx.HTTPError, ValueError):
        return name, []


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/dashboard")
async def dashboard(minutes: int = 10):
    minutes = max(2, min(minutes, 60))
    now = datetime.now(timezone.utc).timestamp()
    start = now - minutes * 60
    step = 5
    timeout = httpx.Timeout(5.0, connect=2.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        query_tasks = [
            _query_range(client, name, expression, start, now, step)
            for name, expression in QUERIES.items()
        ]
        targets_task = _get_json(client, f"{PROMETHEUS_URL}/api/v1/targets")
        alerts_task = _get_json(client, f"{PROMETHEUS_URL}/api/v1/alerts")
        rules_task = _get_json(client, f"{PROMETHEUS_URL}/api/v1/rules", params={"type": "alert"})
        results = await asyncio.gather(*query_tasks, targets_task, alerts_task, rules_task, return_exceptions=True)

    metrics: dict[str, list] = {}
    for item in results[: len(QUERIES)]:
        if isinstance(item, tuple):
            metrics[item[0]] = item[1]
    targets_raw = results[-3]
    alerts_raw = results[-2]
    rules_raw = results[-1]
    # Las cuatro reglas siempre, aunque estén en reposo: así se ve qué se vigila y no solo lo que ya falló.
    rules = []
    if isinstance(rules_raw, dict):
        for group in rules_raw.get("data", {}).get("groups", []):
            for rule in group.get("rules", []):
                labels = rule.get("labels", {})
                annotations = rule.get("annotations", {})
                rules.append({
                    "name": rule.get("name", "Alerta"),
                    "state": rule.get("state", "inactive"),
                    "severity": labels.get("severidad", ""),
                    "forSeconds": rule.get("duration", 0),
                    "summary": annotations.get("resumen", ""),
                    "impact": annotations.get("impacto", ""),
                    "sources": sorted({
                        a.get("labels", {}).get("fuente") or a.get("labels", {}).get("job", "")
                        for a in rule.get("alerts", [])
                    } - {""}),
                })
    targets = []
    if isinstance(targets_raw, dict):
        for target in targets_raw.get("data", {}).get("activeTargets", []):
            labels = target.get("labels", {})
            targets.append({
                "job": labels.get("job", "desconocido"),
                "health": target.get("health", "unknown"),
                "lastScrape": target.get("lastScrape"),
                "lastError": target.get("lastError", ""),
                "scrapeUrl": target.get("scrapeUrl", ""),
            })
    alerts = []
    if isinstance(alerts_raw, dict):
        for alert in alerts_raw.get("data", {}).get("alerts", []):
            labels = alert.get("labels", {})
            annotations = alert.get("annotations", {})
            alerts.append({
                "name": labels.get("alertname", "Alerta"),
                "state": alert.get("state", "unknown"),
                "severity": labels.get("severidad", labels.get("severity", "")),
                "source": labels.get("fuente", labels.get("job", "")),
                "summary": annotations.get("resumen", annotations.get("summary", "")),
                "action": annotations.get("accion", annotations.get("action", "")),
                "activeAt": alert.get("activeAt"),
            })

    prometheus_ok = isinstance(targets_raw, dict) and targets_raw.get("status") == "success"
    return {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "prometheusOk": prometheus_ok,
        "metrics": metrics,
        "targets": targets,
        "alerts": alerts,
        "rules": rules,
        "windowMinutes": minutes,
    }


def _tail_log(line: str) -> None:
    global _JOB
    with _JOB_LOCK:
        if _JOB is None:
            return
        _JOB["logs"].append(line.rstrip("\r\n"))
        if len(_JOB["logs"]) > _JOB_LOG_LIMIT:
            _JOB["logs"] = _JOB["logs"][-_JOB_LOG_LIMIT :]


def _read_process_output(process: subprocess.Popen) -> None:
    assert process.stdout is not None
    for line in process.stdout:
        _tail_log(line)
    return_code = process.wait()
    with _JOB_LOCK:
        if _JOB is not None and _JOB.get("process") is process:
            _JOB["exitCode"] = return_code
            _JOB["status"] = "completed" if return_code == 0 else "failed"
            _JOB["finishedAt"] = datetime.now(timezone.utc).isoformat()
            _JOB["process"] = None


def _popen(argv: list[str], cwd: Path) -> subprocess.Popen:
    # Sin PYTHONIOENCODING, Python en Windows escribe en cp1252 cuando la salida es un pipe y los acentos llegan rotos.
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )


def _launch_job(kind: str, argv: list[str]) -> dict:
    global _JOB
    with _JOB_LOCK:
        if _JOB is not None and _JOB.get("status") == "running":
            raise HTTPException(status_code=409, detail="Ya hay una prueba en ejecución. Esperá a que termine.")
        try:
            process = _popen(argv, HITO13_DIR)
        except OSError as exc:
            raise HTTPException(status_code=500, detail=f"No se pudo iniciar el proceso: {exc}") from exc
        _JOB = {
            "id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
            "kind": kind,
            "status": "running",
            "pid": process.pid,
            "startedAt": datetime.now(timezone.utc).isoformat(),
            "finishedAt": None,
            "exitCode": None,
            "logs": [f"$ {' '.join(argv)}"],
            "process": process,
        }
        reader = threading.Thread(target=_read_process_output, args=(process,), daemon=True)
        reader.start()
        return _public_job(_JOB)


def _public_job(job: dict | None) -> dict:
    if not job:
        return {"status": "idle", "logs": []}
    return {key: value for key, value in job.items() if key != "process"}


def _check_api_ready() -> dict:
    try:
        response = httpx.get(f"{API_URL}/health", timeout=5)
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail=f"La API instrumentada no responde en {API_URL}. Levantá primero el stack del Hito 13. ({type(exc).__name__})",
        ) from exc
    if response.status_code != 200 or data.get("estado") != "ok":
        fuentes = data.get("fuentes", {})
        caidas = [name for name, info in fuentes.items() if info.get("estado") != "ok"]
        detalle = ", ".join(caidas) if caidas else "una o más dependencias"
        raise HTTPException(status_code=409, detail=f"No se inicia la prueba: hay dependencias sin disponibilidad ({detalle}). Revisá /health.")
    return data


def _ensure_redis_container() -> None:
    if not shutil.which("docker"):
        raise HTTPException(status_code=503, detail="No se encontró Docker CLI en este equipo. La prueba de falla necesita Docker Desktop en ejecución.")
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Running}}", REDIS_CONTAINER],
        capture_output=True,
        text=True,
        timeout=8,
    )
    if result.returncode != 0 or result.stdout.strip().lower() != "true":
        raise HTTPException(status_code=409, detail=f"El contenedor {REDIS_CONTAINER} no está iniciado. Levantá las bases del Hito 10 antes de probar la falla.")


@app.post("/api/run")
def run_test(payload: RunRequest):
    if payload.scenario == "falla" and not payload.confirmar:
        raise HTTPException(status_code=400, detail="Confirmá explícitamente que autorizás detener y reiniciar Redis durante la prueba.")
    _check_api_ready()
    if not SCRIPT_CONTROLADO.exists():
        raise HTTPException(status_code=500, detail=f"No existe el script de pruebas: {SCRIPT_CONTROLADO}")

    if payload.scenario == "pico":
        argv = [
            sys.executable, str(SCRIPT_CONTROLADO), "pico",
            "--partido", "P-01",
            "--cantidad", str(payload.cantidad),
            "--tasa", str(payload.tasa),
        ]
        kind = f"Pico de comentarios · {payload.cantidad:,} a {payload.tasa:g}/s".replace(",", ".")
    elif payload.scenario == "estado":
        argv = [sys.executable, str(SCRIPT_CONTROLADO), "estado", "--partido-estado", payload.partido]
        kind = f"Transición IRIS · {payload.partido}"
    else:
        _ensure_redis_container()
        argv = [sys.executable, str(SCRIPT_CONTROLADO), "falla", "--partido", "P-01"]
        kind = "Falla controlada de Redis · 75 s"

    return _launch_job(kind, argv)


@app.post("/api/capture")
def capture_evidence():
    if not SCRIPT_CONTROLADO.exists():
        raise HTTPException(status_code=500, detail="No se encontró el script de captura del Hito 13.")
    env_file = HITO13_DIR / ".env"
    if not env_file.exists() or not any(line.strip().startswith("GRAFANA_ADMIN_PASSWORD=") and line.split("=", 1)[1].strip() for line in env_file.read_text(encoding="utf-8").splitlines()):
        raise HTTPException(status_code=409, detail="Falta GRAFANA_ADMIN_PASSWORD en Hito-13-monitoreo/.env.")
    try:
        response = httpx.get(f"{GRAFANA_URL}/api/health", timeout=3)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"Grafana no responde en {GRAFANA_URL}.") from exc
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=10)
    fmt = lambda value: value.isoformat(timespec="seconds")
    name = "panel_web_" + end.strftime("%Y%m%d_%H%M%S")
    argv = [
        sys.executable, str(SCRIPT_CONTROLADO), "capturar",
        "--desde", fmt(start), "--hasta", fmt(end), "--nombre", name,
    ]
    return _launch_job("Captura de evidencia Grafana · últimos 10 minutos", argv)


# ---------------------------------------------------------------------------
# Recorrido de situaciones: corre todas las pruebas en orden, una detrás de otra,
# y deja en el estado del trabajo qué paso está activo para que la página lo muestre.
# ---------------------------------------------------------------------------

HITO10_DIR = HITO13_DIR.parent / "Hito-10-fixture2030-APIREST"
EVIDENCIA_DIR = HITO13_DIR / "evidencia"
# Partidos que la siembra deja en "Programado". La transición no tiene vuelta atrás: se usa el primero que siga libre.
CANDIDATOS_ESTADO = ("P-08", "P-06", "P-02")
PAUSA_ENTRE_SITUACIONES = 20

SITUACIONES = (
    ("preparacion", "Preparación"),
    ("normal", "Operación normal"),
    ("pico", "Pico de comentarios"),
    ("estado", "Cambio de estado en IRIS"),
    ("falla", "Caída de Redis"),
    ("captura", "Captura de evidencia"),
)


def _paso(indice: int, **cambios) -> None:
    with _JOB_LOCK:
        if _JOB is not None:
            _JOB["steps"][indice].update(cambios)
            if cambios.get("status") == "running":
                _JOB["currentStep"] = indice


def _ejecutar(argv: list[str], cwd: Path = HITO13_DIR) -> int:
    _tail_log(f"$ {' '.join(argv)}")
    process = _popen(argv, cwd)
    with _JOB_LOCK:
        if _JOB is not None:
            _JOB["pid"] = process.pid
    assert process.stdout is not None
    for line in process.stdout:
        _tail_log(line)
    return process.wait()


def _esperar(segundos: int, motivo: str) -> None:
    _tail_log(f"… {motivo}: {segundos} s")
    time.sleep(segundos)


def _ultimo(patron: str, desde: float) -> dict | None:
    archivos = [p for p in EVIDENCIA_DIR.glob(patron) if p.stat().st_mtime >= desde]
    if not archivos:
        return None
    try:
        return json.loads(max(archivos, key=lambda p: p.stat().st_mtime).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _p95_del_pico(desde: float) -> float | None:
    archivos = [p for p in (EVIDENCIA_DIR / "resultados_sin_secretos").glob("pico_comentarios_*.jsonl") if p.stat().st_mtime >= desde]
    if not archivos:
        return None
    duraciones = []
    for linea in max(archivos, key=lambda p: p.stat().st_mtime).read_text(encoding="utf-8").splitlines():
        try:
            duraciones.append(float(json.loads(linea)["duracion_ms"]))
        except (ValueError, KeyError):
            continue
    if not duraciones:
        return None
    duraciones.sort()
    return duraciones[max(0, min(len(duraciones) - 1, round(0.95 * len(duraciones) + 0.5) - 1))]


def _sesion_vigente() -> bool:
    try:
        return httpx.get(f"{API_URL}/sesiones/U001", timeout=5).status_code == 200
    except httpx.HTTPError:
        return False


def _partido_programado() -> str | None:
    for partido in CANDIDATOS_ESTADO:
        try:
            r = httpx.get(f"{API_URL}/partidos/{partido}/detalle", timeout=5)
            if r.status_code == 200 and r.json().get("estado") == "Programado":
                return partido
        except (httpx.HTTPError, ValueError):
            continue
    return None


def _grafana_lista() -> bool:
    env_file = HITO13_DIR / ".env"
    if not env_file.exists():
        return False
    clave = [l.split("=", 1)[1].strip() for l in env_file.read_text(encoding="utf-8").splitlines() if l.startswith("GRAFANA_ADMIN_PASSWORD=")]
    if not clave or not clave[0]:
        return False
    try:
        return httpx.get(f"{GRAFANA_URL}/api/health", timeout=3).status_code == 200
    except httpx.HTTPError:
        return False


def _correr_recorrido(cantidad: int, tasa: float) -> None:
    py, script = sys.executable, str(SCRIPT_CONTROLADO)
    inicio_ventana = datetime.now(timezone.utc) - timedelta(seconds=30)
    hubo_error = False
    partido = None

    def fallo(indice: int, codigo: int) -> None:
        nonlocal hubo_error
        hubo_error = True
        _paso(indice, status="failed", summary=f"El script terminó con código {codigo}. Ver la consola.",
              finishedAt=datetime.now(timezone.utc).isoformat())

    def listo(indice: int, resumen: str, estado: str = "done") -> None:
        _paso(indice, status=estado, summary=resumen, finishedAt=datetime.now(timezone.utc).isoformat())

    def empezar(indice: int) -> float:
        _paso(indice, status="running", startedAt=datetime.now(timezone.utc).isoformat())
        _tail_log("")
        _tail_log(f"══ {indice}. {SITUACIONES[indice][1]} ══")
        return time.time()

    try:
        # 0. Preparación: sesiones vigentes (vencen a los 30 min) y un partido libre para el cambio de estado.
        empezar(0)
        notas = []
        if _sesion_vigente():
            notas.append("Sesión U001 vigente")
        else:
            _tail_log("La sesión U001 venció: se vuelven a cargar las sesiones de Redis.")
            codigo = _ejecutar(["docker", "compose", "--profile", "api", "run", "--rm", "api",
                                "python", "-m", "seed.run", "--solo", "redis"], HITO10_DIR)
            notas.append("Sesiones recargadas" if codigo == 0 and _sesion_vigente() else "No se pudieron recargar las sesiones")
        partido = _partido_programado()
        notas.append(f"Partido para el cambio de estado: {partido}" if partido else "No queda partido en Programado")
        listo(0, " · ".join(notas))

        # 1. Operación normal: la línea de base.
        t = empezar(1)
        codigo = _ejecutar([py, script, "normal", "--duracion", "40"])
        if codigo:
            fallo(1, codigo)
        else:
            datos = _ultimo("operacion_normal_*.json", t) or {}
            respuestas = datos.get("respuestas_por_base", {})
            total = sum(respuestas.values())
            errores = sum(v for k, v in respuestas.items() if not k.endswith(" 200"))
            listo(1, f"{total} lecturas contra las seis bases · {errores} con error")

        # 2. Pico de comentarios.
        t = empezar(2)
        codigo = _ejecutar([py, script, "pico", "--partido", "P-01", "--cantidad", str(cantidad), "--tasa", str(tasa)])
        if codigo:
            fallo(2, codigo)
        else:
            datos = _ultimo("resultados_sin_secretos/pico_comentarios_*_resumen.json", t) or {}
            v = datos.get("verificacion", {})
            p95 = _p95_del_pico(t)
            partes = [
                f"{datos.get('creados_201', '?')} de {datos.get('enviados', '?')} guardados",
                f"{v.get('faltantes', '?')} faltantes",
                f"{v.get('duplicados', '?')} duplicados",
                f"tasa real {datos.get('tasa_real_por_s', '?')}/s",
            ]
            if p95 is not None:
                partes.append(f"p95 del cliente {p95:.1f} ms")
            listo(2, " · ".join(partes))
        _esperar(PAUSA_ENTRE_SITUACIONES, "Pausa para que el tráfico vuelva a la normalidad")

        # 3. Cambio de estado en IRIS.
        t = empezar(3)
        if not partido:
            listo(3, "Se saltea: no queda ningún partido en Programado (la transición no tiene vuelta atrás).", "skipped")
        else:
            codigo = _ejecutar([py, script, "estado", "--partido-estado", partido])
            if codigo:
                fallo(3, codigo)
            else:
                datos = _ultimo("estado_partido_*.json", t) or {}
                codigos = " → ".join(str(p.get("codigo")) for p in datos.get("pasos", [])[1:])
                listo(3, f"{partido}: En juego, Finalizado y vuelta a En juego → respuestas {codigos}")

        # 4. Caída de Redis.
        t = empezar(4)
        try:
            _ensure_redis_container()
        except HTTPException as exc:
            listo(4, f"Se saltea: {exc.detail}", "skipped")
        else:
            codigo = _ejecutar([py, script, "falla", "--partido", "P-01"])
            if codigo:
                fallo(4, codigo)
            else:
                datos = _ultimo("prueba_de_falla_*.json", t) or {}
                fases = datos.get("fases", {})
                durante = fases.get("durante_fin", {})
                despues = fases.get("despues", {})
                alertas = sorted({a["alerta"] for f in ("durante_15s", "durante_fin") for a in fases.get(f, {}).get("alertas_prometheus", [])})
                trafico = datos.get("trafico_de_fondo", {})
                fallidos = sum(v for k, v in trafico.items() if k.startswith("GET sesiones") and not k.endswith(" 200"))
                listo(4, " · ".join([
                    f"Durante: salud {durante.get('health', {}).get('codigo')}, sesión {durante.get('sesion_U001', {}).get('codigo')}",
                    f"alertas: {', '.join(alertas) or 'ninguna'}",
                    f"{fallidos} consultas de sesión fallidas",
                    f"Después: salud {despues.get('health', {}).get('codigo')}, sesión {despues.get('sesion_U001', {}).get('codigo')}",
                ]))

        # 5. Captura de todo el recorrido.
        empezar(5)
        if not _grafana_lista():
            listo(5, "Se saltea: Grafana no responde o falta GRAFANA_ADMIN_PASSWORD en .env.", "skipped")
        else:
            _esperar(15, "Espera para que Prometheus registre el final")
            fin_ventana = datetime.now(timezone.utc)
            nombre = "recorrido_" + datetime.now().strftime("%Y%m%d_%H%M%S")
            codigo = _ejecutar([py, script, "capturar", "--desde", inicio_ventana.isoformat(timespec="seconds"),
                                "--hasta", fin_ventana.isoformat(timespec="seconds"), "--nombre", nombre])
            if codigo:
                fallo(5, codigo)
            else:
                listo(5, f"15 paneles y series guardados en evidencia/dashboards/{nombre}/")
    except Exception as exc:  # noqa: BLE001 - cualquier error tiene que quedar visible en la página
        hubo_error = True
        _tail_log(f"Error inesperado: {type(exc).__name__}: {exc}")
    finally:
        with _JOB_LOCK:
            if _JOB is not None:
                for paso in _JOB["steps"]:
                    if paso["status"] in ("pending", "running"):
                        paso["status"] = "failed" if paso["status"] == "running" else "skipped"
                _JOB["status"] = "failed" if hubo_error else "completed"
                _JOB["exitCode"] = 1 if hubo_error else 0
                _JOB["finishedAt"] = datetime.now(timezone.utc).isoformat()
                _JOB["currentStep"] = None


@app.post("/api/recorrido")
def run_recorrido(payload: RecorridoRequest):
    global _JOB
    if not payload.confirmar:
        raise HTTPException(status_code=400, detail="El recorrido detiene Redis unos 75 segundos. Marcá la confirmación para empezar.")
    _check_api_ready()
    _ensure_redis_container()
    with _JOB_LOCK:
        if _JOB is not None and _JOB.get("status") == "running":
            raise HTTPException(status_code=409, detail="Ya hay una prueba en ejecución. Esperá a que termine.")
        _JOB = {
            "id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
            "kind": "Recorrido de situaciones",
            "mode": "recorrido",
            "status": "running",
            "pid": None,
            "startedAt": datetime.now(timezone.utc).isoformat(),
            "finishedAt": None,
            "exitCode": None,
            "currentStep": 0,
            "steps": [{"id": i, "title": t, "status": "pending", "summary": "", "startedAt": None, "finishedAt": None}
                      for i, t in SITUACIONES],
            "logs": [f"Recorrido: {payload.cantidad} comentarios a {payload.tasa:g}/s en el pico."],
            "process": None,
        }
        threading.Thread(target=_correr_recorrido, args=(payload.cantidad, payload.tasa), daemon=True).start()
        return _public_job(_JOB)


@app.get("/api/job")
def get_job():
    with _JOB_LOCK:
        return _public_job(_JOB)


@app.get("/api/health")
async def panel_health():
    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            response = await client.get(f"{PROMETHEUS_URL}/-/ready")
        prometheus_ok = response.status_code == 200
    except httpx.HTTPError:
        prometheus_ok = False
    return {
        "panel": "ok",
        "prometheus": "ok" if prometheus_ok else "down",
        "apiUrl": API_URL,
        "prometheusUrl": PROMETHEUS_URL,
        "grafanaUrl": GRAFANA_URL,
    }
