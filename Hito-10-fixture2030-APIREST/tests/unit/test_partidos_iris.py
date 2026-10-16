import pytest

from app.deps import get_partidos_iris_service
from app.errors import Conflicto
from app.services.partidos_iris import PartidosIrisService


class RepoFalso:
    TRANSICIONES = {("Programado", "En juego"), ("En juego", "Finalizado")}

    def __init__(self):
        self.llamadas = []
        self.partidos = {
            "P-01": {"codigo": "P-01", "equipo_local": "ARG", "equipo_visitante": "BRA",
                     "fecha_hora": "2030-06-15T18:30:00", "sede": "Estadio Monumental", "estado": "En juego",
                     "eventos": [{"tipo": "Gol", "minuto": 32, "descripcion": None, "jugador_codigo": "J-ARG-01"}]},
            "P-03": {"codigo": "P-03", "equipo_local": "GER", "equipo_visitante": "ENG",
                     "fecha_hora": "2030-06-15T18:30:00", "sede": "Camp Nou", "estado": "Programado", "eventos": []},
        }

    def obtener_partido(self, codigo):
        self.llamadas.append(("get", codigo))
        return self.partidos.get(codigo)

    def cambiar_estado(self, codigo, nuevo):
        self.llamadas.append(("set", codigo, nuevo))
        actual = self.partidos[codigo]["estado"]
        if (actual, nuevo) not in self.TRANSICIONES:
            raise Conflicto(f"No se puede pasar de '{actual}' a '{nuevo}'.")
        self.partidos[codigo]["estado"] = nuevo


@pytest.fixture
def repo(app):
    r = RepoFalso()
    app.dependency_overrides[get_partidos_iris_service] = lambda: PartidosIrisService(r)
    return r


def test_detalle(client, repo, documentado):
    r = client.get("/partidos/P-01/detalle")
    assert r.status_code == 200 and r.json()["estado"] == "En juego" and r.json()["eventos"][0]["minuto"] == 32
    documentado(r, "get", "/partidos/{partido_id}/detalle")


def test_detalle_inexistente(client, repo):
    assert client.get("/partidos/P-99/detalle").status_code == 404


def test_transicion_valida(client, repo, documentado):
    r = client.post("/partidos/P-03/estado", json={"estado": "En juego"})
    assert r.status_code == 200 and r.json()["estado"] == "En juego"
    documentado(r, "post", "/partidos/{partido_id}/estado")


def test_transicion_invalida_409(client, repo, documentado):
    r = client.post("/partidos/P-03/estado", json={"estado": "Finalizado"})
    assert r.status_code == 409 and r.json()["error"]["codigo"] == "CONFLICTO"
    documentado(r, "post", "/partidos/{partido_id}/estado")
    assert repo.partidos["P-03"]["estado"] == "Programado"


def test_repetir_el_mismo_estado_es_idempotente_y_no_escribe(client, repo):
    r = client.post("/partidos/P-01/estado", json={"estado": "En juego"})
    assert r.status_code == 200 and not any(c[0] == "set" for c in repo.llamadas)


def test_estado_inexistente_en_dominio_422(client, repo, documentado):
    r = client.post("/partidos/P-01/estado", json={"estado": "Suspendido"})
    assert r.status_code == 422 and repo.llamadas == []
    documentado(r, "post", "/partidos/{partido_id}/estado")


def test_partido_inexistente_en_transicion_404(client, repo):
    assert client.post("/partidos/P-99/estado", json={"estado": "En juego"}).status_code == 404
