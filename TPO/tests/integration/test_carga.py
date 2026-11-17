from datetime import datetime, timezone

import pytest
from pymongo.errors import DuplicateKeyError, WriteError

from seed import cargar_mongo, cargar_neo4j


def _totales_mongo(db):
    return {c: db[c].count_documents({}) for c in ("equipos", "jugadores", "resultados")}


def test_totales_tras_la_primera_carga(cargado, mongo, neo4j):
    assert _totales_mongo(mongo.db) == {"equipos": 48, "jugadores": 1248, "resultados": 2}
    totales = cargar_neo4j.totales(neo4j._drv(), "neo4j")
    assert totales["Equipo"] == 48
    assert totales["Jugador"] == 1248
    assert totales["Estadio"] == 16
    assert totales["Partido"] == 104
    assert totales["PERTENECE_A"] == 1248
    assert totales["PARTICIPA_EN"] == 144
    assert totales["SE_JUEGA_EN"] == 104
    assert totales["CLASIFICA_A"] == 32
    eventos = sum(len(e) for e in cargado.eventos.values())
    assert totales["Evento"] == eventos == totales["OCURRE_EN"]
    assert totales["INFLUYE_EN"] == sum(1 for es in cargado.eventos.values() for e in es if e["influye_en"])
    assert totales["PROTAGONIZA"] == sum(1 for es in cargado.eventos.values() for e in es if e["jugador"])


def test_la_segunda_carga_no_cambia_ningun_total(cargado, mongo, neo4j):
    antes = (_totales_mongo(mongo.db), cargar_neo4j.totales(neo4j._drv(), "neo4j"))
    cargar_mongo.preparar(mongo.db)
    cargar_mongo.cargar(mongo.db, cargado)
    cargar_neo4j.cargar(neo4j._drv(), "neo4j", cargado)
    despues = (_totales_mongo(mongo.db), cargar_neo4j.totales(neo4j._drv(), "neo4j"))
    assert despues == antes


def test_un_segundo_equipo_con_el_mismo_codigo_es_rechazado(cargado, mongo, neo4j):
    with pytest.raises(DuplicateKeyError):
        mongo.db.equipos.insert_one({"_id": "ARG", "nombre": "Otra Argentina", "grupo": "A"})
    assert mongo.db.equipos.count_documents({"_id": "ARG"}) == 1
    from neo4j.exceptions import ConstraintError

    with pytest.raises(ConstraintError):
        neo4j._escribir("CREATE (:Equipo {codigo: 'ARG', nombre: 'Otra Argentina'})")


def test_la_validacion_rechaza_un_pronostico_con_goles_negativos(cargado, mongo):
    ahora = datetime(2030, 6, 12, tzinfo=timezone.utc)
    valido = {"_id": "U0000001:P-03", "usuario_id": "U0000001", "partido_id": "P-03", "goles_local": 1,
              "goles_visitante": 0, "cargado_en": ahora, "creado_en": ahora}
    mongo.db.pronosticos.insert_one(valido)
    with pytest.raises(WriteError):
        mongo.db.pronosticos.insert_one({**valido, "_id": "U0000002:P-03", "usuario_id": "U0000002", "goles_local": -1})
    with pytest.raises(WriteError):
        mongo.db.pronosticos.insert_one({**valido, "_id": "U0000003:P-03", "usuario_id": "usuario"})


def test_la_recarga_no_pisa_un_partido_que_ya_empezo(cargado, neo4j):
    empezo = datetime(2030, 6, 13, 14, 50, tzinfo=timezone.utc)
    neo4j._escribir("MATCH (p:Partido {id: 'P-03'}) SET p.estado = 'En juego', p.inicio_real = $t", t=empezo)
    cargar_neo4j.cargar(neo4j._drv(), "neo4j", cargado)
    fila = neo4j._leer("MATCH (p:Partido {id: 'P-03'}) RETURN p.estado AS estado, p.inicio_real AS inicio")[0]
    assert fila["estado"] == "En juego"
    assert fila["inicio"] == empezo


def test_indices_del_prode(cargado, mongo):
    def claves(coleccion):
        return {tuple(i["key"].items()) for i in mongo.db[coleccion].list_indexes()}

    assert (("usuario_id", 1),) in claves("pronosticos")
    assert (("partido_id", 1),) in claves("pronosticos")
    assert (("puntos", -1), ("exactos", -1), ("tiempo_seg", -1), ("_id", 1)) in claves("puntajes")
    assert (("integrantes", 1),) in claves("prodes")
    assert any(i["key"] == {"codigo": 1} and i.get("unique") for i in mongo.db.prodes.list_indexes())
    assert (("equipo", 1), ("posicion", 1)) in claves("jugadores")
