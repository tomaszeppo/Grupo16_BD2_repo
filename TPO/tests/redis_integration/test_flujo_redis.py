"""Pruebas aisladas con Redis y Mongo reales; ejecutar explícitamente con RUN_REDIS_INTEGRATION=1."""
import os
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
import redis
from pymongo import MongoClient

from app.adapters.ranking_redis import RankingRedis
from app.config.settings import Settings


@pytest.fixture
def entorno():
    if os.environ.get("RUN_REDIS_INTEGRATION") != "1":
        pytest.skip("Requiere Redis y Mongo reales y activación explícita")
    settings = Settings()
    r = redis.Redis.from_url("redis://redis:6379/15", decode_responses=True)
    if r.dbsize() != 0:
        pytest.fail("Redis DB 15 no está vacía; no se toca información existente")
    client = MongoClient(settings.mongo_uri, tz_aware=True)
    dbname = "test_redis_" + uuid.uuid4().hex
    db = client[dbname]
    cfg = settings.model_copy(update={"redis_lote": 2, "redis_persistencia_demora_segundos": 0})
    ranking = RankingRedis(SimpleNamespace(db=db), cfg, r)
    try:
        yield db, r, ranking
    finally:
        claves = list(r.scan_iter("prode:*"))
        if claves:
            r.delete(*claves)
        client.drop_database(dbname)
        client.close()


def test_calculo_por_lotes_reintento_y_recuperacion(entorno):
    db, r, ranking = entorno
    inicio = datetime.now(timezone.utc).replace(microsecond=0)
    db.usuarios.insert_many([{"_id": f"U{i:07d}", "nombre": f"Hincha {i}"} for i in range(1, 5)])
    db.pronosticos.insert_many([
        {"_id": f"U{i:07d}:P-03", "usuario_id": f"U{i:07d}", "partido_id": "P-03",
         "goles_local": gl, "goles_visitante": gv, "cargado_en": inicio + timedelta(seconds=desfase)}
        for i, gl, gv, desfase in [(1, 2, 1, -30), (2, 1, 0, -30), (3, 0, 0, -30), (4, 2, 1, 1)]])
    resultado = {"goles_local": 2, "goles_visitante": 1, "inicio_real": inicio,
                 "inicio_programado": inicio + timedelta(days=1)}
    assert ranking.preparar_partido("P-03") == 4
    assert ranking.puntuar_en_redis("P-03", resultado) == 4
    assert ranking.puntuar_en_redis("P-03", resultado) == 4
    assert [(x["usuario_id"], x["puntos"]) for x in ranking.top(4)] == [
        ("U0000001", 3), ("U0000002", 1), ("U0000003", 0), ("U0000004", 0)]
    assert ranking.posicion("U0000001")["puesto"] == 1
    ranking.persistir_partido("P-03")
    ranking.persistir_partido("P-03")
    assert db.puntajes.find_one({"_id": "U0000001"})["puntos"] == 3
    assert db.pronosticos.find_one({"usuario_id": "U0000004"})["anulado"] is True
    # Simula pérdida de la copia Redis y recuperación desde los datos persistidos.
    claves = list(r.scan_iter("prode:*"))
    if claves:
        r.delete(*claves)
    ranking.puntuar_en_redis("P-03", resultado)
    ranking.persistir_partido("P-03")
    assert ranking.posicion("U0000001")["puntos"] == 3
    assert db.puntajes.find_one({"_id": "U0000001"})["puntos"] == 3


def test_recuperacion_con_volcado_parcial_no_suma_dos_veces(entorno):
    db, r, ranking = entorno
    inicio = datetime.now(timezone.utc).replace(microsecond=0)
    db.usuarios.insert_many([{"_id": "U0000001", "nombre": "A"}, {"_id": "U0000002", "nombre": "B"}])
    db.pronosticos.insert_many([
        {"_id": f"U{i:07d}:P-04", "usuario_id": f"U{i:07d}", "partido_id": "P-04", "goles_local": 2,
         "goles_visitante": 1, "cargado_en": inicio - timedelta(seconds=10)} for i in (1, 2)])
    resultado = {"goles_local": 2, "goles_visitante": 1, "inicio_real": inicio, "inicio_programado": inicio}
    ranking.puntuar_en_redis("P-04", resultado)
    # Primera persona ya persistida; el proceso cae antes de transferir la segunda.
    db.puntajes.insert_one({"_id": "U0000001", "puntos": 3, "exactos": 1, "tiempo_seg": 10, "aplicados": ["P-04"]})
    claves = list(r.scan_iter("prode:*"))
    if claves:
        r.delete(*claves)
    ranking.puntuar_en_redis("P-04", resultado)
    ranking.persistir_partido("P-04")
    assert [db.puntajes.find_one({"_id": f"U{i:07d}"})["puntos"] for i in (1, 2)] == [3, 3]
    assert [f["puntos"] for f in ranking.top(2)] == [3, 3]


def test_reintento_de_aplicacion_interrumpida_usa_base_original(entorno):
    import json
    db, r, ranking = entorno
    inicio = datetime.now(timezone.utc).replace(microsecond=0)
    db.usuarios.insert_one({"_id": "U0000001", "nombre": "A"})
    db.pronosticos.insert_one({"_id": "U0000001:P-05", "usuario_id": "U0000001", "partido_id": "P-05",
                              "goles_local": 2, "goles_visitante": 1, "cargado_en": inicio - timedelta(seconds=10)})
    resultado = {"goles_local": 2, "goles_visitante": 1, "inicio_real": inicio, "inicio_programado": inicio}
    ranking.preparar_partido("P-05")
    r.hset("prode:partido:P-05:aplicados", "U0000001", json.dumps({"estado": "preparado", "base": {"puntos": 0, "exactos": 0, "tiempo_seg": 0}}))
    r.hset("prode:ranking:datos", "U0000001", json.dumps({"puntos": 3, "exactos": 1, "tiempo_seg": 10}))
    ranking.puntuar_en_redis("P-05", resultado)
    assert ranking.posicion("U0000001")["puntos"] == 3
    ranking.persistir_partido("P-05")
    assert db.puntajes.find_one({"_id": "U0000001"})["puntos"] == 3


def test_acumula_dos_partidos_y_tabla_de_grupo(entorno):
    from app.services.ranking import RankingService
    db, r, ranking = entorno
    inicio = datetime.now(timezone.utc).replace(microsecond=0)
    db.usuarios.insert_many([{"_id": "U0000001", "nombre": "Admin"}, {"_id": "U0000002", "nombre": "Amigo"}, {"_id": "U0000003", "nombre": "Fuera"}])
    for partido in ("P-03", "P-04"):
        db.pronosticos.insert_many([{"_id": f"{u}:{partido}", "usuario_id": u, "partido_id": partido,
            "goles_local": gl, "goles_visitante": gv, "cargado_en": inicio - timedelta(seconds=10)}
            for u, gl, gv in [("U0000001", 2, 1), ("U0000002", 1, 0), ("U0000003", 2, 1)]])
        resultado = {"goles_local": 2, "goles_visitante": 1, "inicio_real": inicio, "inicio_programado": inicio}
        ranking.puntuar_en_redis(partido, resultado)
        ranking.persistir_partido(partido)
    mongo = SimpleNamespace(obtener_prode=lambda _: {"id":"PR-00000001", "nombre":"Grupo X", "integrantes":["U0000001", "U0000002"]})
    _, tabla = RankingService(ranking, mongo).tabla_de_prode("PR-00000001", "U0000001")
    assert [(f["usuario_id"], f["puntos"]) for f in tabla] == [("U0000001", 6), ("U0000002", 2)]
    assert ranking.posicion("U0000003")["puntos"] == 6
    assert db.puntajes.find_one({"_id":"U0000001"})["puntos"] == 6


def test_tabla_muestra_nombres_de_integrantes_sin_pronosticos(entorno):
    db, r, ranking = entorno
    db.usuarios.insert_many([{"_id":"U0000001", "nombre":"Admin"}, {"_id":"U0000002", "nombre":"Mica"}])
    filas = ranking.puntajes_de(["U0000001", "U0000002"])
    assert [(f["nombre"], f["puntos"]) for f in filas] == [("Admin", 0), ("Mica", 0)]
    assert r.hget("prode:ranking:nombres", "U0000002") == "Mica"
