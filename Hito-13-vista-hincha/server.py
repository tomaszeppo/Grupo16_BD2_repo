"""Vista del hincha. Sirve archivos y adapta el contrato existente, sin tocar Hitos 10/13."""
from __future__ import annotations

import asyncio
import json
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import demo

RAIZ = Path(__file__).resolve().parent
API_URL = os.getenv("FIXTURE_API_URL", "http://127.0.0.1:8001").rstrip("/")
COOKIE = "fixture_hincha"
SESIONES: dict[str, dict] = {}
RUTA = re.compile(r"(?:partidos/P-0[1-8](?:/(?:detalle|eventos|comentarios|estadisticas))?|equipos/[A-Z]{3}(?:/jugadores)?)")
app = FastAPI(title="Fixture 2030 · Hincha", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=RAIZ / "static"), name="static")


class Acceso(BaseModel):
    usuario_id: str = Field(default="U001", pattern=r"^U\d{3,6}$")
    nombre: str = Field(min_length=1, max_length=60)
    pais: Literal["ARG", "BRA", "ESP", "FRA", "URU"] = "ARG"
    modo: Literal["real", "demo"] = "real"


class Comentario(BaseModel):
    contenido: str = Field(min_length=1, max_length=280)


async def consultar(metodo, ruta, **kwargs):
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(12, connect=2)) as cliente:
            r = await cliente.request(metodo, f"{API_URL}/{ruta}", **kwargs)
    except httpx.HTTPError as exc:
        raise HTTPException(503, "No pudimos conectar con el Fixture. Intentá nuevamente en unos instantes.") from exc
    if r.is_error:
        mensajes = {404: "No encontramos esos datos o la sesión ya venció.",
                    409: "No pudimos completar la operación. Revisá los datos e intentá nuevamente.",
                    422: "Revisá los datos y el intervalo seleccionado.",
                    503: "Esta parte del Fixture no está disponible por el momento.",
                    504: "El Fixture está tardando más de lo habitual. Intentá nuevamente."}
        raise HTTPException(r.status_code, mensajes.get(r.status_code, "No pudimos completar la consulta."))
    return r.json() if r.content else None


def publico(s):
    return {k: s[k] for k in ("usuario_id", "nombre", "pais", "modo")} | {"ttl_segundos": max(0, int(s["vence"]-time.time()))}


async def sesion(request: Request):
    clave = request.cookies.get(COOKIE, "")
    s = SESIONES.get(clave)
    if not s or s["vence"] <= time.time():
        SESIONES.pop(clave, None)
        raise HTTPException(401, "Tu sesión venció. Volvé a ingresar para continuar.")
    if s["modo"] == "real":
        try:
            datos = await consultar("GET", f"sesiones/{s['usuario_id']}")
        except HTTPException as exc:
            if exc.status_code == 404:
                SESIONES.pop(clave, None)
                raise HTTPException(401, "Tu sesión venció o fue cerrada. Volvé a ingresar.") from exc
            raise
        if datos["session_id"] != s["session_id"] or datos["estado_acceso"] != "ACTIVA":
            SESIONES.pop(clave, None)
            raise HTTPException(401, "La sesión cambió. Volvé a ingresar.")
        if datos.get("ttl_segundos") is not None:
            s["vence"] = min(s["vence"], time.time()+datos["ttl_segundos"])
    return s


@app.middleware("http")
async def respuesta_local(request: Request, call_next):
    if request.method in ("POST", "DELETE"):
        origen = request.headers.get("origin")
        if origen and origen != str(request.base_url).rstrip("/"):
            return Response(status_code=403)
    respuesta = await call_next(request)
    respuesta.headers["Cache-Control"] = "no-store"
    respuesta.headers["X-Content-Type-Options"] = "nosniff"
    return respuesta


@app.get("/")
def index():
    return FileResponse(RAIZ / "static" / "index.html")


@app.post("/api/sesion")
async def ingresar(datos: Acceso, response: Response, request: Request):
    nombre = datos.nombre.strip()
    if not nombre:
        raise HTTPException(422, "Ingresá tu nombre.")
    ttl, identificador = 1800, "demo"
    if datos.modo == "real":
        existente = await consultar("GET", f"sesiones/{datos.usuario_id}")
        if existente.get("estado_acceso") != "ACTIVA":
            raise HTTPException(401, "La sesión no está activa.")
        ttl = existente.get("ttl_segundos")
        ttl = min(1800, ttl) if ttl is not None else 1800
        identificador = existente["session_id"]
    for clave, s in list(SESIONES.items()):
        if s["vence"] <= time.time():
            SESIONES.pop(clave, None)
    SESIONES.pop(request.cookies.get(COOKIE, ""), None)
    clave = secrets.token_urlsafe(32)
    s = datos.model_dump() | {"nombre": nombre, "vence": time.time()+ttl,
                              "session_id": identificador, "claves": {}}
    SESIONES[clave] = s
    response.set_cookie(COOKIE, clave, httponly=True, samesite="lax", max_age=ttl)
    return publico(s)


@app.get("/api/sesion")
async def obtener_sesion(s=Depends(sesion)):
    return publico(s)


@app.delete("/api/sesion", status_code=204)
async def salir(request: Request, response: Response):
    # El cierre es válido aunque la sesión haya expirado. Si Redis falla, conservarla para reintentar.
    clave = request.cookies.get(COOKIE, "")
    s = SESIONES.get(clave)
    if s and s["modo"] == "real":
        await consultar("DELETE", f"sesiones/{s['usuario_id']}")
    SESIONES.pop(clave, None)
    response.delete_cookie(COOKIE)


@app.get("/api/partidos")
async def partidos(s=Depends(sesion)):
    async def uno(n):
        ruta = f"partidos/P-{n:02}"
        try:
            partido = demo.leer(ruta, {}, s) if s["modo"] == "demo" else await consultar("GET", ruta)
            try:
                detalle = demo.leer(ruta+"/detalle", {}, s) if s["modo"] == "demo" else await consultar("GET", ruta+"/detalle")
                return {"partido": partido, "estado": detalle["estado"]}
            except HTTPException as exc:
                return {"partido": partido, "estado": None, "error_estado": exc.detail}
        except HTTPException as exc:
            return {"id": f"P-{n:02}", "error": exc.detail}
    # La API no tiene listado: solo se consultan los ocho IDs documentados en seed/datos.py.
    return {"items": await asyncio.gather(*(uno(n) for n in range(1, 9)))}


@app.get("/api/fixture/{ruta:path}")
async def leer(ruta: str, request: Request, s=Depends(sesion)):
    if not RUTA.fullmatch(ruta):
        raise HTTPException(404, "Ese recurso no está disponible.")
    params = dict(request.query_params)
    if ruta.endswith("/comentarios"):
        params["pais"] = s["pais"]
    if s["modo"] == "demo":
        try:
            datos = demo.leer(ruta, params, s)
        except (ValueError, KeyError):
            raise HTTPException(422, "Revisá el intervalo seleccionado.")
        if datos is None:
            raise HTTPException(404, "No hay datos para esta consulta.")
        return datos
    return await consultar("GET", ruta, params=params)


@app.post("/api/fixture/partidos/{partido_id}/comentarios")
async def comentar(partido_id: str, datos: Comentario,
                   idempotency_key: str = Header(alias="Idempotency-Key", pattern=r"^[A-Za-z0-9_-]{8,64}$"),
                   s=Depends(sesion)):
    if not re.fullmatch(r"P-0[1-8]", partido_id):
        raise HTTPException(404, "Partido no disponible.")
    contenido = datos.contenido.strip()
    if not contenido:
        raise HTTPException(422, "Escribí un comentario antes de enviarlo.")
    ruta_detalle = f"partidos/{partido_id}/detalle"
    detalle = demo.leer(ruta_detalle, {}, s) if s["modo"] == "demo" else await consultar("GET", ruta_detalle)
    if detalle.get("estado") != "En juego":
        raise HTTPException(409, "Este encuentro no está en juego. La tribuna está en modo lectura.")
    cuerpo = {"contenido": contenido, "pais": s["pais"], "usuario_id": s["usuario_id"], "usuario_nombre": s["nombre"]}
    if s["modo"] == "real":
        return await consultar("POST", f"partidos/{partido_id}/comentarios", json=cuerpo,
                               headers={"Idempotency-Key": idempotency_key})
    if idempotency_key in s["claves"]:
        anterior = s["claves"][idempotency_key]
        if anterior["contenido"] != contenido or anterior["partido_id"] != partido_id:
            raise HTTPException(409, "La clave ya se usó para otro comentario.")
        return anterior
    ahora = datetime.now(timezone.utc)
    ventana = ahora.replace(minute=(ahora.minute//30)*30, second=0, microsecond=0).isoformat().replace("+00:00", "Z")
    nuevo = cuerpo | {"comentario_id": secrets.token_hex(16), "partido_id": partido_id,
                       "creado_en": ahora.isoformat(), "ventana": ventana, "likes": 0, "estado_moderacion": "PUBLICADO"}
    demo.COMENTARIOS.append(nuevo)
    s["claves"][idempotency_key] = nuevo
    return nuevo


async def comentarios_recientes(partido_id, s, ahora=None):
    """Dos particiones evitan perder el hilo al cruzar una media hora. No escanea Cassandra."""
    ahora = ahora or datetime.now(timezone.utc)
    ventana = ahora.replace(minute=(ahora.minute//30)*30, second=0, microsecond=0)
    async def una(inicio):
        params = {"pais": s["pais"], "ventana": inicio.isoformat().replace("+00:00", "Z"), "limit": 20}
        if s["modo"] == "demo":
            return demo.leer(f"partidos/{partido_id}/comentarios", params, s)["items"]
        return (await consultar("GET", f"partidos/{partido_id}/comentarios", params=params))["items"]
    paginas = await asyncio.gather(una(ventana), una(ventana-timedelta(minutes=30)))
    unicos = {c["comentario_id"]: c for pagina in paginas for c in pagina}
    return sorted(unicos.values(), key=lambda c: c["creado_en"], reverse=True)[:40]


async def transmitir_comentarios(request, partido_id):
    while not await request.is_disconnected():
        try:
            s = await sesion(request)
            items = await comentarios_recientes(partido_id, s)
            datos = {"items": items, "consultado_en": datetime.now(timezone.utc).isoformat()}
            yield "event: comentarios\ndata: " + json.dumps(datos, ensure_ascii=False) + "\n\n"
        except HTTPException as exc:
            yield "event: estado\ndata: " + json.dumps({"codigo": exc.status_code, "mensaje": exc.detail}) + "\n\n"
            if exc.status_code == 401:
                return
        await asyncio.sleep(2)


@app.get("/api/directo/{partido_id}/comentarios")
async def directo(partido_id: str, request: Request, s=Depends(sesion)):
    if not re.fullmatch(r"P-0[1-8]", partido_id):
        raise HTTPException(404, "Partido no disponible.")
    return StreamingResponse(transmitir_comentarios(request, partido_id), media_type="text/event-stream",
                             headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})
