from pymongo import ASCENDING, MongoClient

from app.config.settings import Settings
from seed import datos


def cargar(s: Settings) -> str:
    cli = MongoClient(
        s.mongo_host, s.mongo_port, username=s.mongo_user or None, password=s.mongo_password or None, authSource="admin"
    )
    db = cli[s.mongo_db]
    existentes = db.list_collection_names()
    if "equipos" not in existentes:
        db.create_collection("equipos", validator={"$jsonSchema": {
            "bsonType": "object", "required": ["nombre", "codigo"],
            "properties": {"nombre": {"bsonType": "string"}, "codigo": {"bsonType": "string", "pattern": "^[A-Z]{3}$"}}}})
    if "jugadores" not in existentes:
        db.create_collection("jugadores", validator={"$jsonSchema": {
            "bsonType": "object", "required": ["nombre", "apellido", "dorsal", "equipo", "posicion"],
            "properties": {"dorsal": {"bsonType": "int", "minimum": 1, "maximum": 99},
                           "equipo": {"bsonType": "string", "pattern": "^[A-Z]{3}$"},
                           "posicion": {"enum": ["Portero", "Defensa", "Centrocampista", "Delantero"]}}}})
    if "partidos" not in existentes:
        db.create_collection("partidos", validator={"$jsonSchema": {
            "bsonType": "object",
            "required": ["codigo", "equipo_local", "equipo_visitante", "fecha_hora", "sede", "estado", "eventos"],
            "properties": {
                "codigo": {"bsonType": "string", "pattern": "^P-\\d{2}$"},
                "equipo_local": {"bsonType": "string"},
                "equipo_visitante": {"bsonType": "string"},
                "fecha_hora": {"bsonType": "string"},
                "sede": {"bsonType": "string"},
                "estado": {"enum": ["Programado", "En juego", "Finalizado"]},
                "eventos": {"bsonType": "array", "items": {"bsonType": "object"}},
            },
        }})
    db.equipos.create_index([("codigo", ASCENDING)], unique=True)
    db.jugadores.create_index("equipo")
    db.jugadores.create_index("apellido")
    db.jugadores.create_index("posicion")
    db.partidos.create_index("codigo", unique=True)
    for codigo, nombre in datos.EQUIPOS:
        db.equipos.update_one({"codigo": codigo}, {"$set": {"nombre": nombre}}, upsert=True)
    for j in datos.jugadores():
        db.jugadores.update_one({"equipo": j["equipo"], "dorsal": j["dorsal"]}, {"$set": j}, upsert=True)
    sedes = {e[0]: e[1] for e in datos.ESTADIOS}
    for partido in datos.PARTIDOS:
        eventos = [
            {"tipo": tipo, "minuto": minuto, "descripcion": None, "jugador_codigo": jugador}
            for tipo, minuto, jugador in datos.EVENTOS_DETALLE.get(partido["id"], [])
        ]
        documento = {
            "codigo": partido["id"],
            "equipo_local": partido["local"],
            "equipo_visitante": partido["visitante"],
            "fecha_hora": f"{partido['fecha']}T18:30:00",
            "sede": sedes[partido["estadio"]],
            "estado": datos.ESTADOS_INICIALES.get(partido["id"], "Programado"),
            "eventos": eventos,
        }
        db.partidos.update_one(
            {"codigo": partido["id"]},
            {"$setOnInsert": documento},
            upsert=True,
        )
    return (
        f"{db.equipos.count_documents({})} equipos, {db.jugadores.count_documents({})} jugadores, "
        f"{db.partidos.count_documents({})} partidos"
    )
