from __future__ import annotations

import asyncio
import os
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
    partido: Literal["P-06", "P-07"] = "P-06"
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
        results = await asyncio.gather(*query_tasks, targets_task, alerts_task, return_exceptions=True)

    metrics: dict[str, list] = {}
    for item in results[: len(QUERIES)]:
        if isinstance(item, tuple):
            metrics[item[0]] = item[1]
    targets_raw = results[-2]
    alerts_raw = results[-1]
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


def _launch_job(kind: str, argv: list[str]) -> dict:
    global _JOB
    with _JOB_LOCK:
        if _JOB is not None and _JOB.get("status") == "running":
            raise HTTPException(status_code=409, detail="Ya hay una prueba en ejecución. Esperá a que termine.")
        try:
            process = subprocess.Popen(
                argv,
                cwd=HITO13_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
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
            "--salida", "evidencia/resultados_sin_secretos",
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
