"""Resume los pedidos de una corrida: cantidad, pedidos por segundo, percentiles de latencia y errores."""
import math
from collections import Counter

EXITOSOS = frozenset({200, 201, 202})


def percentil(valores: list[float], p: float) -> float:
    """Percentil por rango más cercano: el valor que deja por debajo (o igual) al p % de la muestra."""
    if not valores:
        raise ValueError("No hay valores.")
    ordenados = sorted(valores)
    posicion = max(1, math.ceil(p / 100 * len(ordenados)))
    return ordenados[posicion - 1]


def _latencias(filas: list[dict]) -> dict:
    ms = [f["ms"] for f in filas]
    if not ms:
        return {"p50_ms": None, "p95_ms": None, "p99_ms": None, "max_ms": None}
    return {"p50_ms": round(percentil(ms, 50), 1), "p95_ms": round(percentil(ms, 95), 1),
            "p99_ms": round(percentil(ms, 99), 1), "max_ms": round(max(ms), 1)}


def resumir(filas: list[dict], duracion_segundos: float, estados_esperados=EXITOSOS, con_rutas: bool = True) -> dict:
    """La latencia se informa sobre los pedidos con respuesta esperada; los errores se cuentan aparte."""
    buenos = [f for f in filas if f["estado"] in estados_esperados]
    malos = [f for f in filas if f["estado"] not in estados_esperados]
    salida = {
        "total": len(filas),
        "por_segundo": round(len(filas) / duracion_segundos, 1) if duracion_segundos > 0 else 0.0,
        "exitosos": len(buenos),
        "errores": len(malos),
        "porcentaje_de_error": round(100 * len(malos) / len(filas), 2) if filas else 0.0,
        "errores_por_estado": dict(sorted(Counter(str(f["estado"]) for f in malos).items())),
        **_latencias(buenos),
        "max_ms_incluyendo_errores": round(max(f["ms"] for f in filas), 1) if filas else None,
    }
    if con_rutas:
        rutas = sorted({f["ruta"] for f in filas})
        salida["por_ruta"] = {r: resumir([f for f in filas if f["ruta"] == r], duracion_segundos,
                                         estados_esperados, con_rutas=False) for r in rutas}
    return salida


def linea_de_tiempo(filas: list[dict], estados_esperados=EXITOSOS) -> list[dict]:
    """Pedidos y errores de cada segundo de la corrida. Sirve para ver una caída y cuánto tarda la recuperación."""
    if not filas:
        return []
    ultimo = int(max(f["t"] for f in filas))
    salida = []
    for segundo in range(ultimo + 1):
        del_segundo = [f for f in filas if int(f["t"]) == segundo]
        salida.append({
            "segundo": segundo, "total": len(del_segundo),
            "errores": sum(1 for f in del_segundo if f["estado"] not in estados_esperados),
            "estados": dict(sorted(Counter(str(f["estado"]) for f in del_segundo).items())),
        })
    return salida
