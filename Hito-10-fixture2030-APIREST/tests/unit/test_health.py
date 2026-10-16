from app.deps import get_health_service
from app.errors import DependenciaNoDisponible
from app.services.health import HealthService


class Ok:
    def ping(self):
        pass


class Caido:
    def ping(self):
        raise DependenciaNoDisponible("redis")


def test_todas_ok_200(app, client, documentado):
    app.dependency_overrides[get_health_service] = lambda: HealthService({"mongodb": Ok(), "redis": Ok()})
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["estado"] == "ok"
    assert set(r.json()["fuentes"]) == {"mongodb", "redis"}
    documentado(r, "get", "/health")


def test_una_caida_es_503_con_detalle_por_fuente(app, client, documentado):
    app.dependency_overrides[get_health_service] = lambda: HealthService({"mongodb": Ok(), "redis": Caido()})
    r = client.get("/health")
    assert r.status_code == 503
    assert r.json()["estado"] == "degradado" and r.json()["fuentes"]["redis"]["estado"] == "caida"
    assert r.json()["fuentes"]["mongodb"]["estado"] == "ok"
    documentado(r, "get", "/health")
