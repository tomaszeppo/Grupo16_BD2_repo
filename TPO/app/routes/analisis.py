"""Análisis de audiencia (InfluxDB): como el panel de estadísticas de una transmisión en vivo."""
from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.deps import get_influx_resumenes, get_mongo
from app.errors import NoEncontrado, ValidacionError
from app.schemas.comunes import PartidoId
from app.services.analisis_audiencia import resumir

router = APIRouter(tags=["InfluxDB · Audiencia"])
FUENTE = "influxdb"
Pais = Query(None, pattern="^[A-Z]{3}$", description="Solo un país, por ejemplo ARG")


def tramo(desde_minuto: int = Query(0, ge=0, le=90), hasta_minuto: int = Query(90, ge=0, le=90)) -> tuple[int, int]:
    if desde_minuto > hasta_minuto:
        raise ValidacionError("desde_minuto no puede ser mayor que hasta_minuto.")
    return desde_minuto, hasta_minuto


def _simulacion(mongo, partido_id: str) -> dict:
    doc = mongo.db.simulaciones.find_one({"_id": partido_id}, {"_id": 0, "corrida_id": 1, "tipo": 1, "jugadas": 1,
                                                                 "audiencia_incompleta": 1, "inicio_estadisticas": 1})
    if not doc or not doc.get("corrida_id"):
        raise NoEncontrado("Este partido no tiene una simulación con audiencia.")
    return doc


@router.get("/partidos/{partido_id}/audiencia", summary="Audiencia del partido, minuto a minuto")
def audiencia(partido_id: PartidoId, rango: tuple[int, int] = Depends(tramo), pais: str | None = Pais,
              mongo=Depends(get_mongo), influx=Depends(get_influx_resumenes)) -> dict:
    """Curva de espectadores simultáneos (total y por país) con los goles, pico, promedio, minutos vistos,
    espectadores únicos y tiempo medio de visualización. Se puede pedir un tramo de minutos o un país."""
    desde, hasta = rango
    doc = _simulacion(mongo, partido_id)
    inicio = doc.get("inicio_estadisticas")  # acota la consulta al horario del partido
    filas = influx.audiencia_por_minuto(partido_id, doc["corrida_id"], desde, hasta, pais, inicio)
    unicos = influx.resumen_audiencia(partido_id, doc["corrida_id"], inicio)
    if pais:
        unicos = {pais: unicos.get(pais, 0)}
    goles = [{"minuto": j["minuto"], "equipo_id": j["equipo_id"]} for j in doc.get("jugadas", []) if j.get("tipo") == "Gol"]
    return {"fuente": FUENTE, "partido_id": partido_id, "tipo": doc.get("tipo", "demo"), "pais": pais,
            "tramo": {"desde_minuto": desde, "hasta_minuto": hasta},
            "incompleta": bool(doc.get("audiencia_incompleta")), **resumir(filas, unicos, goles, desde, hasta)}


@router.get("/partidos/{partido_id}/comentarios/por-minuto", summary="Comentarios por minuto y país")
def comentarios_por_minuto(partido_id: PartidoId, rango: tuple[int, int] = Depends(tramo), pais: str | None = Pais,
                           mongo=Depends(get_mongo), influx=Depends(get_influx_resumenes)) -> dict:
    desde, hasta = rango
    doc = _simulacion(mongo, partido_id)
    filas = influx.comentarios_por_minuto(partido_id, doc["corrida_id"], desde, hasta, pais,
                                          doc.get("inicio_estadisticas"))
    return {"fuente": FUENTE, "partido_id": partido_id, "tramo": {"desde_minuto": desde, "hasta_minuto": hasta},
            "minutos": [{"minuto": int(f["minuto"]), "pais": f["pais"], "origen": f["origen"],
                         "comentarios": int(f["comentarios"])} for f in filas]}


@router.get("/analisis/audiencia-por-minuto", summary="Audiencia promedio por minuto, entre todos los partidos")
def audiencia_por_minuto(pais: str | None = Pais, tipo: Literal["demo", "carga"] | None = Query(None),
                         influx=Depends(get_influx_resumenes)) -> dict:
    """Para decidir cuándo poner publicidad: en qué minutos de un partido hay, en promedio, más gente mirando.
    Cada simulación cuenta como un partido visto."""
    minutos = influx.audiencia_promedio_por_minuto(pais, tipo)
    mayor = max(minutos, key=lambda m: m["promedio"], default=None)
    return {"fuente": FUENTE, "pais": pais, "tipo": tipo, "minutos": minutos,
            "pico": {"minuto": mayor["minuto"], "promedio": mayor["promedio"]} if mayor and mayor["promedio"] else None}
