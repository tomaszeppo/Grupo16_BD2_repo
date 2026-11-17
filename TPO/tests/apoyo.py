"""Arma la aplicación para una prueba: reemplaza adaptadores, reloj y piezas únicas por proceso."""
from app import deps
from app.main import create_app
from app.services.calendario import Calendario


def armar_app(settings, mongo, neo4j, reloj):
    aplicacion = create_app(settings)
    calendario = Calendario(neo4j, settings.calendario_ttl_segundos, reloj)
    reemplazos = {
        deps.get_settings: lambda: settings,
        deps.get_mongo: lambda: mongo,
        deps.get_neo4j: lambda: neo4j,
        deps.get_reloj: lambda: reloj,
        deps.get_calendario: lambda: calendario,
    }
    aplicacion.dependency_overrides.update(reemplazos)
    aplicacion.state.calendario = calendario
    return aplicacion
