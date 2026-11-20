"""Análisis de audiencia de un partido, como el de una transmisión: curva de espectadores simultáneos, pico,
promedio, minutos vistos, espectadores únicos y tiempo medio de visualización.

Funciones puras: reciben lo que se leyó de InfluxDB y arman la respuesta.
"""


def resumir(filas: list[dict], unicos: dict[str, int], goles: list[dict], desde: int = 0, hasta: int = 90) -> dict:
    """`filas`: {minuto, pais, espectadores}. `unicos`: por país. `goles`: {minuto, equipo_id} del partido.

    - minutos_vistos: suma de espectadores de cada minuto (un espectador durante un minuto = un minuto visto).
    - promedio: espectadores simultáneos en promedio en el tramo.
    - tiempo_medio_min: minutos vistos / espectadores únicos (cuánto se quedó, en promedio, cada uno).
    """
    por_minuto: dict[int, dict[str, int]] = {m: {} for m in range(desde, hasta + 1)}
    for fila in filas:
        minuto = int(fila["minuto"])
        if desde <= minuto <= hasta and fila["espectadores"]:
            por_minuto[minuto][fila["pais"]] = por_minuto[minuto].get(fila["pais"], 0) + int(fila["espectadores"])
    curva = [{"minuto": m, "total": sum(paises.values()), "por_pais": paises} for m, paises in por_minuto.items()]
    minutos_vistos = sum(m["total"] for m in curva)
    mayor = max(curva, key=lambda m: m["total"]) if curva else None  # max() se queda con el primero si empatan
    total_unicos = sum(unicos.values())
    return {
        "curva": curva,
        "pico": {"minuto": mayor["minuto"], "espectadores": mayor["total"]} if mayor and mayor["total"] else None,
        "promedio": round(minutos_vistos / len(curva), 1) if curva else None,
        "minutos_vistos": minutos_vistos,
        "unicos": {"total": total_unicos, "por_pais": unicos},
        "tiempo_medio_min": round(minutos_vistos / total_unicos, 1) if total_unicos else None,
        "goles": [g for g in goles if desde <= g["minuto"] <= hasta],
    }
