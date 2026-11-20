"""Escenario de carga del partido en vivo: miles de espectadores con la conexión abierta y una parte comentando.

    python -m carga.ejecutar vivo --espectadores 2000 --partido P-07 --comentan 0.05

Cada espectador es un usuario distinto con su sesión (carga/sesiones.py) y mira desde el país de su usuario.
Primero se abren todas las conexiones, después se inicia la simulación (tipo "carga") y se sigue el partido
hasta el final. Una parte de los espectadores comenta: poco durante el juego y bastante más justo después de un
gol. Algunos se van y vuelven a entrar a mitad del partido.

Qué se mide:
- conexiones abiertas, fallidas y reconexiones;
- comentarios publicados, frenados por el modo lento y con error;
- demora de entrega: desde que el espectador manda su comentario hasta que le llega por su propia conexión
  (incluye guardarlo en Cassandra y repartirlo por Redis entre los procesos de la API);
- la audiencia máxima que informó la API.

Las conexiones son asincrónicas (muchas por proceso) y se reparten en varios procesos, como el resto del
generador (carga/cliente.py).
"""
import asyncio
import json
import multiprocessing
import random
import time
import uuid

import httpx

from carga.resumen import percentil

MAX_PROCESOS = 6
PROBABILIDAD_BASE = 0.03     # por segundo, para quien comenta
PROBABILIDAD_TRAS_GOL = 0.5  # por segundo, durante los segundos siguientes a un gol
SEGUNDOS_TRAS_GOL = 4
SE_VA = 0.25                 # parte de los espectadores que se va y vuelve a mitad del partido

_trabajo: dict = {}  # lo heredan los procesos hijos (fork)


def resumir_vivo(eventos: list[dict], espectadores: int) -> dict:
    def contar(tipo, condicion=lambda e: True):
        return sum(1 for e in eventos if e["tipo"] == tipo and condicion(e))

    entregas = [e["ms"] for e in eventos if e["tipo"] == "entrega"]
    medida = (lambda p: round(percentil(entregas, p), 2)) if entregas else (lambda p: None)
    comentarios = [e for e in eventos if e["tipo"] == "comentario"]
    return {
        "espectadores_pedidos": espectadores,
        "conexiones": {"abiertas": contar("conexion", lambda e: e["ok"]),
                       "fallidas": contar("conexion", lambda e: not e["ok"]),
                       "reconexiones": contar("reconexion")},
        "comentarios": {"enviados": len(comentarios),
                        "publicados": sum(1 for c in comentarios if c["estado"] in (200, 201)),
                        "modo_lento": sum(1 for c in comentarios if c["estado"] == 429),
                        # 409: llegó justo cuando el partido terminaba (ya no se puede comentar); no es una falla
                        "partido_terminado": sum(1 for c in comentarios if c["estado"] == 409),
                        "errores": sum(1 for c in comentarios if c["estado"] not in (200, 201, 409, 429))},
        "entrega_ms": {"medidas": len(entregas), "p50": medida(50), "p95": medida(95), "p99": medida(99),
                       "max": round(max(entregas), 2) if entregas else None},
        "audiencia_reportada_max": max((e["total"] for e in eventos if e["tipo"] == "audiencia"), default=0),
    }


async def _espectador(cli, partido, token, comenta, rng, estado, eventos, enviados):
    """Mira el partido; si `comenta`, comenta. Puede irse una vez y volver."""
    sale_en = time.time() + rng.uniform(20, 70) if rng.random() < SE_VA else None
    comentador = asyncio.create_task(_comentar(cli, partido, token, rng, estado, eventos, enviados)) if comenta else None
    try:
        while time.time() < estado["fin"] and not estado["terminado"]:
            limite = (sale_en - time.time()) if sale_en else None
            try:
                await asyncio.wait_for(_mirar(cli, partido, token, estado, eventos, enviados), timeout=limite)
            except asyncio.TimeoutError:  # se fue: vuelve en unos segundos
                sale_en = None
                eventos.append({"tipo": "reconexion", "t": time.time()})
                await asyncio.sleep(rng.uniform(2, 5))
            except (httpx.HTTPError, OSError):
                eventos.append({"tipo": "conexion", "ok": False, "t": time.time()})
                await asyncio.sleep(1)
    finally:
        if comentador:
            comentador.cancel()


async def _mirar(cli, partido, token, estado, eventos, enviados):
    async with cli.stream("GET", f"/partidos/{partido}/vivo", headers={"X-Sesion": token}) as respuesta:
        if respuesta.status_code != 200:
            eventos.append({"tipo": "conexion", "ok": False, "estado": respuesta.status_code, "t": time.time()})
            await asyncio.sleep(1)
            return
        eventos.append({"tipo": "conexion", "ok": True, "t": time.time()})
        tipo = None
        async for linea in respuesta.aiter_lines():
            if linea.startswith("event: "):
                tipo = linea[7:]
            elif linea.startswith("data: "):
                datos = json.loads(linea[6:])
                if tipo == "comentario" and datos.get("comentario_id") in enviados:
                    eventos.append({"tipo": "entrega", "ms": (time.perf_counter() - enviados.pop(datos["comentario_id"])) * 1000})
                elif tipo == "audiencia":
                    eventos.append({"tipo": "audiencia", "total": datos.get("total", 0)})
                elif tipo == "estado":
                    goles = sum((datos.get("marcador") or {}).values())
                    if goles > estado["goles"]:
                        estado["goles"], estado["ultimo_gol"] = goles, time.time()
                    if datos.get("estado") == "Finalizado":
                        estado["terminado"] = True
                        return
            if time.time() >= estado["fin"]:
                return


async def _comentar(cli, partido, token, rng, estado, eventos, enviados):
    while not estado["terminado"] and time.time() < estado["fin"]:
        await asyncio.sleep(1)
        tras_gol = time.time() - estado["ultimo_gol"] < SEGUNDOS_TRAS_GOL
        if rng.random() >= (PROBABILIDAD_TRAS_GOL if tras_gol else PROBABILIDAD_BASE):
            continue
        comentario_id = str(uuid.uuid4())
        enviados[comentario_id] = time.perf_counter()
        try:
            r = await cli.post(f"/partidos/{partido}/comentarios", headers={"X-Sesion": token},
                               json={"comentario_id": comentario_id, "contenido": "¡Golazo!" if tras_gol else "Vamos"})
            codigo = r.status_code
        except (httpx.HTTPError, OSError):
            codigo = 0
        if codigo not in (200, 201):
            enviados.pop(comentario_id, None)
        eventos.append({"tipo": "comentario", "estado": codigo, "t": time.time()})


async def _proceso_async(espectadores: list[tuple[str, bool, int]]) -> list[dict]:
    eventos: list[dict] = []
    enviados: dict[str, float] = {}
    estado = {"fin": _trabajo["fin"], "terminado": False, "goles": 0, "ultimo_gol": 0.0}
    limites = httpx.Limits(max_connections=None, max_keepalive_connections=None)
    tiempos = httpx.Timeout(10.0, read=40.0)  # el latido llega cada 15 s
    async with httpx.AsyncClient(base_url=_trabajo["base_url"], limits=limites, timeout=tiempos) as cli:
        tareas = [_espectador(cli, _trabajo["partido"], token, comenta, random.Random(semilla), estado, eventos, enviados)
                  for token, comenta, semilla in espectadores]
        await asyncio.gather(*tareas, return_exceptions=True)
    return eventos


def _proceso(espectadores):
    return asyncio.run(_proceso_async(espectadores))


def correr_vivo(base_url: str, partido: str, tokens: list[str], comentan: float, duracion: float, semilla: int,
                iniciar_simulacion) -> tuple[list[dict], int]:
    """Abre las conexiones, inicia la simulación con `iniciar_simulacion()` y espera el final."""
    rng = random.Random(semilla)
    espectadores = [(token, rng.random() < comentan, semilla * 100000 + n) for n, token in enumerate(tokens)]
    procesos = max(1, min(MAX_PROCESOS, len(espectadores) // 200 or 1))
    reparto = [espectadores[i::procesos] for i in range(procesos)]
    calentamiento = 5 + len(espectadores) / 500  # tiempo para que todas las conexiones queden abiertas
    _trabajo.update(base_url=base_url, partido=partido, fin=time.time() + calentamiento + duracion)
    with multiprocessing.get_context("fork").Pool(procesos) as grupo:
        pendiente = grupo.map_async(_proceso, reparto, chunksize=1)
        time.sleep(calentamiento)
        iniciar_simulacion()
        partes = pendiente.get()
    return [e for parte in partes for e in parte], procesos
