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
    db.equipos.create_index([("codigo", ASCENDING)], unique=True)
    db.jugadores.create_index("equipo")
    db.jugadores.create_index("apellido")
    db.jugadores.create_index("posicion")
    for codigo, nombre in datos.EQUIPOS:
        db.equipos.update_one({"codigo": codigo}, {"$set": {"nombre": nombre}}, upsert=True)
    for j in datos.jugadores():
        db.jugadores.update_one({"equipo": j["equipo"], "dorsal": j["dorsal"]}, {"$set": j}, upsert=True)
    return f"{db.equipos.count_documents({})} equipos, {db.jugadores.count_documents({})} jugadores"
