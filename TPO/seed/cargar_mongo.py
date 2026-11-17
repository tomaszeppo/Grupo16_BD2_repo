"""Prepara la base del prode (colecciones, validación, índices) y carga el catálogo. Se puede repetir."""
from pymongo import ASCENDING, DESCENDING, UpdateOne

from app.dominio.ids import CODIGO_EQUIPO, ID_PARTIDO, ID_PRODE, ID_USUARIO
from seed.datos import Fixture

_ENTERO = ["int", "long"]

VALIDACIONES = {
    "usuarios": {
        "bsonType": "object",
        "required": ["_id", "nombre", "pais", "creado_en"],
        "properties": {
            "_id": {"bsonType": "string", "pattern": ID_USUARIO},
            "nombre": {"bsonType": "string", "minLength": 1, "maxLength": 60},
            "pais": {"bsonType": "string", "pattern": CODIGO_EQUIPO},
            "creado_en": {"bsonType": "date"},
        },
    },
    "prodes": {
        "bsonType": "object",
        "required": ["_id", "nombre", "dueno", "codigo", "integrantes", "creado_en"],
        "properties": {
            "_id": {"bsonType": "string", "pattern": ID_PRODE},
            "nombre": {"bsonType": "string", "minLength": 1, "maxLength": 60},
            "dueno": {"bsonType": "string", "pattern": ID_USUARIO},
            "codigo": {"bsonType": "string", "minLength": 8, "maxLength": 8},
            # El tope también se controla al unirse; acá queda como última barrera.
            "integrantes": {"bsonType": "array", "maxItems": 100,
                            "items": {"bsonType": "string", "pattern": ID_USUARIO}},
            "creado_en": {"bsonType": "date"},
        },
    },
    "pronosticos": {
        "bsonType": "object",
        "required": ["_id", "usuario_id", "partido_id", "goles_local", "goles_visitante", "cargado_en", "creado_en"],
        "properties": {
            "_id": {"bsonType": "string"},
            "usuario_id": {"bsonType": "string", "pattern": ID_USUARIO},
            "partido_id": {"bsonType": "string", "pattern": ID_PARTIDO},
            "goles_local": {"bsonType": _ENTERO, "minimum": 0, "maximum": 20},
            "goles_visitante": {"bsonType": _ENTERO, "minimum": 0, "maximum": 20},
            "cargado_en": {"bsonType": "date"},
            "creado_en": {"bsonType": "date"},
            "puntos": {"bsonType": _ENTERO, "minimum": 0, "maximum": 3},
            "exacto": {"bsonType": "bool"},
            "anulado": {"bsonType": "bool"},
            "tiempo_seg": {"bsonType": _ENTERO, "minimum": 0, "maximum": 432000},
        },
    },
}

INDICES = {
    "usuarios": [([("pais", ASCENDING)], {})],
    "prodes": [([("codigo", ASCENDING)], {"unique": True}), ([("integrantes", ASCENDING)], {})],
    "pronosticos": [([("usuario_id", ASCENDING)], {}), ([("partido_id", ASCENDING)], {})],
    # El mismo orden del ranking: puntos, exactos, tiempo y, a igualdad total, el id.
    "puntajes": [([("puntos", DESCENDING), ("exactos", DESCENDING), ("tiempo_seg", DESCENDING),
                   ("_id", ASCENDING)], {})],
    "jugadores": [([("equipo", ASCENDING), ("posicion", ASCENDING)], {})],
}


def preparar(db) -> None:
    existentes = set(db.list_collection_names())
    for nombre, esquema in VALIDACIONES.items():
        validador = {"$jsonSchema": esquema}
        if nombre in existentes:
            db.command("collMod", nombre, validator=validador, validationLevel="strict")
        else:
            db.create_collection(nombre, validator=validador)
    for nombre, indices in INDICES.items():
        for claves, opciones in indices:
            db[nombre].create_index(claves, **opciones)


def cargar(db, fixture: Fixture) -> dict[str, int]:
    db.equipos.bulk_write([
        UpdateOne({"_id": e["codigo"]}, {"$set": {"nombre": e["nombre"], "grupo": e["grupo"]}}, upsert=True)
        for e in fixture.equipos
    ])
    db.jugadores.bulk_write([
        UpdateOne({"_id": j["id"]}, {"$set": {k: v for k, v in j.items() if k != "id"}}, upsert=True)
        for j in fixture.jugadores
    ])
    # Los partidos de muestra ya se jugaron: su resultado queda registrado y sin nada por puntuar.
    jugados = [p for p in fixture.partidos if p["estado"] == "Finalizado"]
    if jugados:
        db.resultados.bulk_write([
            UpdateOne({"_id": p["id"]}, {"$setOnInsert": {
                "goles_local": p["goles_local"], "goles_visitante": p["goles_visitante"], "clasificado": None,
                "inicio_programado": p["fecha_hora"], "inicio_real": p["inicio_real"], "cerrado_en": p["fecha_hora"],
                "puntuacion": {"estado": "completa", "pasos": {}, "pronosticos": 0,
                               "iniciada_en": p["fecha_hora"], "terminada_en": p["fecha_hora"]},
            }}, upsert=True)
            for p in jugados
        ])
    return {c: db[c].count_documents({}) for c in ("equipos", "jugadores", "resultados")}
