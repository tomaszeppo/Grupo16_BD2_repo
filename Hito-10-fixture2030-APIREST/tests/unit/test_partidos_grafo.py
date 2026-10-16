import pytest

from app.deps import get_partidos_service
from app.services.partidos import PartidosService

PARTIDO = {
    "id": "P-01", "fecha": "2030-06-15", "fase": "Fase de grupos",
    "estadio": {"id": "EST001", "nombre": "Estadio Monumental", "ciudad": "Buenos Aires"},
    "equipos": [{"codigo": "ARG", "nombre": "Argentina"}, {"codigo": "BRA", "nombre": "Brasil"}],
    "ganador": "ARG", "perdedor": "BRA", "goles_ganador": 2, "goles_perdedor": 1, "origen": "SIMULADO",
}
EVENTOS = [{"id": "EV-P-01-INICIO", "tipo": "Inicio", "minuto": 0}, {"id": "EV-P-01-GOL", "tipo": "Gol", "minuto": 32}]


class RepoFalso:
    def __init__(self):
        self.llamadas = []

    def obtener_partido(self, pid):
        self.llamadas.append(("partido", pid))
        return PARTIDO if pid == "P-01" else None

    def listar_eventos(self, pid, limit):
        self.llamadas.append(("eventos", pid, limit))
        if pid == "P-01":
            return EVENTOS[:limit]
        if pid == "P-02":
            return []
        return None


@pytest.fixture
def repo(app):
    r = RepoFalso()
    app.dependency_overrides[get_partidos_service] = lambda: PartidosService(r)
    return r


def test_partido_existente(client, repo, documentado):
    r = client.get("/partidos/P-01")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["id"] == "P-01" and cuerpo["estadio"]["id"] == "EST001"
    assert [e["codigo"] for e in cuerpo["equipos"]] == ["ARG", "BRA"]
    assert cuerpo["resultado"] == {"ganador": "ARG", "perdedor": "BRA", "goles_ganador": 2, "goles_perdedor": 1, "origen": "SIMULADO"}
    documentado(r, "get", "/partidos/{partido_id}")


def test_partido_inexistente(client, repo, documentado):
    r = client.get("/partidos/P-99")
    assert r.status_code == 404
    documentado(r, "get", "/partidos/{partido_id}")


@pytest.mark.parametrize("pid", ["p-01", "P01", "P-1", "P-01'; DROP", "X" * 200, "P-0001"])
def test_id_invalido_no_llega_al_adaptador(client, repo, pid):
    r = client.get(f"/partidos/{pid}")
    assert r.status_code == 422 and repo.llamadas == []


def test_eventos_ordenados_y_limitados(client, repo, documentado):
    r = client.get("/partidos/P-01/eventos", params={"limit": 1})
    assert r.status_code == 200 and len(r.json()["items"]) == 1 and r.json()["limit"] == 1
    documentado(r, "get", "/partidos/{partido_id}/eventos")


def test_partido_sin_eventos_es_200_vacio(client, repo):
    r = client.get("/partidos/P-02/eventos")
    assert r.status_code == 200 and r.json()["items"] == []


def test_eventos_de_partido_inexistente_es_404(client, repo):
    assert client.get("/partidos/P-99/eventos").status_code == 404


@pytest.mark.parametrize("limit", [0, -3, 201])
def test_limit_de_eventos_invalido(client, repo, limit):
    assert client.get("/partidos/P-01/eventos", params={"limit": limit}).status_code == 422
    assert repo.llamadas == []
