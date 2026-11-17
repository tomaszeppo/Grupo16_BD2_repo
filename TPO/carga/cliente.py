"""Motor del generador de carga: N usuarios virtuales que hacen pedidos sin pausa durante un tiempo fijo.

Los usuarios virtuales son hilos repartidos en varios procesos. Una primera versión con asyncio en un solo
proceso se saturaba ella misma cerca de los 100 pedidos por segundo y medía su propio límite en lugar del de
la API (se detectó porque el consumo de CPU de la API y de MongoDB estaba lejos del tope). Con procesos e
hilos el generador queda holgado para lo que la API puede atender en este laboratorio.
"""
import multiprocessing
import threading
import time
from collections.abc import Callable

import httpx

SIN_RESPUESTA = 0  # el pedido no obtuvo respuesta HTTP (conexión rechazada, corte o tiempo de espera del cliente)
MAX_PROCESOS = 6

_trabajo: dict = {}  # lo heredan los procesos hijos al crearse (fork)


def _usuario_virtual(numero: int, filas: list[dict]) -> None:
    siguiente, inicio, fin = _trabajo["siguiente"], _trabajo["inicio"], _trabajo["fin"]
    with httpx.Client(base_url=_trabajo["base_url"], timeout=_trabajo["tiempo_de_espera"]) as http:
        while time.time() < fin:
            pedido = siguiente(numero)
            t0 = time.time()
            p0 = time.perf_counter()
            try:
                estado = http.request(pedido["metodo"], pedido["url"], json=pedido.get("json"),
                                      headers=pedido.get("headers")).status_code
            except httpx.HTTPError:
                estado = SIN_RESPUESTA
                time.sleep(0.05)  # con el servicio caído no tiene sentido insistir sin pausa
            filas.append({"t": round(t0 - inicio, 3), "ruta": pedido["ruta"], "estado": estado,
                          "ms": round((time.perf_counter() - p0) * 1000, 2)})


def _proceso(numeros: list[int]) -> list[dict]:
    por_hilo = [[] for _ in numeros]
    hilos = [threading.Thread(target=_usuario_virtual, args=(n, filas)) for n, filas in zip(numeros, por_hilo)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    return [fila for filas in por_hilo for fila in filas]


def correr(base_url: str, siguiente_pedido: Callable[[int], dict], concurrencia: int, duracion: float,
           tiempo_de_espera: float = 15.0) -> tuple[list[dict], float, int]:
    """Corre la carga y devuelve (filas, duración real en segundos, procesos usados).

    `siguiente_pedido(numero_de_usuario_virtual)` devuelve un dict con `ruta` (la plantilla, para agrupar),
    `metodo`, `url` y opcionalmente `json` y `headers`. Cada fila es un pedido: segundo en que empezó,
    plantilla de ruta, estado HTTP y milisegundos hasta recibir la respuesta completa.
    """
    procesos = max(1, min(MAX_PROCESOS, concurrencia // 5 or 1))
    reparto = [list(range(i, concurrencia, procesos)) for i in range(procesos)]
    inicio = time.time() + 1.0  # un segundo para que todos los procesos estén listos y arranquen juntos
    _trabajo.update(siguiente=siguiente_pedido, base_url=base_url, tiempo_de_espera=tiempo_de_espera,
                    inicio=inicio, fin=inicio + duracion)
    with multiprocessing.get_context("fork").Pool(procesos, initializer=_esperar_inicio) as grupo:
        partes = grupo.map(_proceso, reparto, chunksize=1)
    filas = sorted((fila for parte in partes for fila in parte), key=lambda f: f["t"])
    return filas, duracion, procesos


def _esperar_inicio() -> None:
    time.sleep(max(0.0, _trabajo["inicio"] - time.time()))
