"""Proveedores de dependencias: adaptadores singleton (conexión perezosa) y servicios."""
from functools import lru_cache

from app.adapters.mongo import MongoAdapter
from app.config.settings import get_settings
from app.services.equipos import EquiposService


@lru_cache
def get_mongo() -> MongoAdapter:
    return MongoAdapter(get_settings())


def get_equipos_service() -> EquiposService:
    return EquiposService(get_mongo())
