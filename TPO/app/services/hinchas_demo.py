"""Identidades sintéticas persistentes de laboratorio, compartidas entre simulaciones."""
import time
import uuid
from datetime import datetime, timedelta, timezone

from pymongo import ReturnDocument
from app.errors import Conflicto

NOMBRES_DEMO = {
    "ARG": ("Mica", "Nico", "Luli", "Tomi", "Sofi", "Fran", "Vale", "Fede"),
    "BRA": ("Bia", "Rafa", "Léo", "Nanda", "Gui", "Lari", "Caio", "Duda"),
    "ESP": ("Lucía", "Dani", "Pablo", "Alba", "Mario", "Clara", "Álex", "Irene"),
    "URU": ("Pato", "Cami", "Nacho", "Flor", "Mati", "Juli", "Santi", "Pau"),
}


def asegurar_hinchas(mongo, paises):
    config = mongo.db.configuracion
    clave = "hinchas_demo"
    config.update_one({"_id": clave}, {"$setOnInsert": {}}, upsert=True)
    token = uuid.uuid4().hex
    reserva = None
    for _ in range(100):
        ahora = datetime.now(timezone.utc)
        reserva = config.find_one_and_update({"_id": clave, "$or": [{"reserva_hasta": {"$exists": False}},
                                                                        {"reserva_hasta": {"$lt": ahora}}]},
            {"$set": {"reserva_token": token, "reserva_hasta": ahora + timedelta(seconds=60)}},
            return_document=ReturnDocument.AFTER)
        if reserva is not None:
            break
        time.sleep(0.1)
    if reserva is None:
        raise Conflicto("Los hinchas de prueba se están preparando; intentá de nuevo.")
    try:
        salida = {}
        for pais in paises:
            salida[pais] = []
            guardados = reserva.get("hinchas", {}).get(pais, {})
            for indice, nombre in enumerate(NOMBRES_DEMO[pais]):
                identificador = guardados.get(str(indice))
                usuario = mongo.obtener_usuario(identificador) if identificador else None
                if usuario is None:
                    usuario = mongo.crear_usuario(nombre, pais, datetime.now(timezone.utc))
                    config.update_one({"_id": clave, "reserva_token": token},
                                      {"$set": {f"hinchas.{pais}.{indice}": usuario["id"]}})
                salida[pais].append(usuario["id"])
        return salida
    finally:
        config.update_one({"_id": clave, "reserva_token": token}, {"$unset": {"reserva_token": "", "reserva_hasta": ""}})
