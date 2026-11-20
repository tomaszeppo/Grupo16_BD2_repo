"""Arma la aplicación para una prueba: reemplaza adaptadores, reloj y piezas únicas por proceso."""
from app import deps
from app.main import create_app
from app.services.calendario import Calendario


def armar_app(settings, mongo, neo4j, reloj, redis=None, cassandra=None):
    from tests.falsos import CassandraFalso, RedisFalso

    redis = redis if redis is not None else RedisFalso()
    cassandra = cassandra if cassandra is not None else CassandraFalso()
    aplicacion = create_app(settings)
    calendario = Calendario(neo4j, settings.calendario_ttl_segundos, reloj)
    reemplazos = {
        deps.get_settings: lambda: settings,
        deps.get_mongo: lambda: mongo,
        deps.get_neo4j: lambda: neo4j,
        deps.get_reloj: lambda: reloj,
        deps.get_calendario: lambda: calendario,
        deps.get_redis: lambda: redis,
        deps.get_cassandra: lambda: cassandra,
    }
    aplicacion.dependency_overrides.update(reemplazos)
    aplicacion.state.calendario = calendario
    return aplicacion


def entrar(cliente, usuario_id: str) -> dict:
    """Abre una sesión y devuelve el encabezado para usarla. Borra la cookie para que cada pedido sea explícito."""
    resp = cliente.post("/sesiones", json={"usuario_id": usuario_id})
    assert resp.status_code == 201, resp.text
    cliente.cookies.clear()
    return {"X-Sesion": resp.json()["token"]}
