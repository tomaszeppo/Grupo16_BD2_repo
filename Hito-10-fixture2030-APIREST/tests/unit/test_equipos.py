import pytest

from app.deps import get_equipos_service
from app.errors import DependenciaNoDisponible
from app.services.equipos import EquiposService


class RepoFalso:
    def __init__(self):
        self.llamadas = []
        self.equipos = {"ARG": {"codigo": "ARG", "nombre": "Argentina"}, "BRA": {"codigo": "BRA", "nombre": "Brasil"}}
        self.jugadores = [
            {"nombre": "Lucas", "apellido": "Alvarez", "dorsal": 1, "posicion": "Portero", "equipo": "ARG"},
            {"nombre": "Mateo", "apellido": "Benitez", "dorsal": 2, "posicion": "Defensa", "equipo": "ARG"},
            {"nombre": "Nico", "apellido": "Cruz", "dorsal": 3, "posicion": "Defensa", "equipo": "ARG"},
        ]

    def _fil(self, codigo, posicion):
        return [j for j in self.jugadores if j["equipo"] == codigo and (posicion is None or j["posicion"] == posicion)]

    def obtener_equipo(self, codigo):
        self.llamadas.append("obtener_equipo")
        return self.equipos.get(codigo)

    def contar_jugadores(self, codigo, posicion):
        self.llamadas.append("contar")
        return len(self._fil(codigo, posicion))

    def listar_jugadores(self, codigo, posicion, limit, offset):
        self.llamadas.append("listar")
        return self._fil(codigo, posicion)[offset : offset + limit]


@pytest.fixture
def repo(app):
    r = RepoFalso()
    app.dependency_overrides[get_equipos_service] = lambda: EquiposService(r)
    return r


def test_equipo_existente(client, repo, documentado):
    r = client.get("/equipos/ARG")
    assert r.status_code == 200
    assert r.json() == {"codigo": "ARG", "nombre": "Argentina"}
    documentado(r, "get", "/equipos/{codigo}")


def test_equipo_inexistente_404(client, repo, documentado):
    r = client.get("/equipos/ZZZ")
    assert r.status_code == 404 and r.json()["error"]["codigo"] == "NO_ENCONTRADO"
    documentado(r, "get", "/equipos/{codigo}")


@pytest.mark.parametrize("codigo", ["arg", "AR", "ARGE", "A1G", "%00", "ARG'--"])
def test_codigo_invalido_no_consulta_la_fuente(client, repo, codigo, documentado):
    r = client.get(f"/equipos/{codigo}")
    assert r.status_code in (404, 422)  # 404 solo si el router no matchea la ruta (p.ej. "%00")
    if r.status_code == 422:
        assert r.json()["error"]["codigo"] == "VALIDACION"
        documentado(r, "get", "/equipos/{codigo}")
    assert repo.llamadas == []


def test_jugadores_paginados(client, repo, documentado):
    r = client.get("/equipos/ARG/jugadores", params={"limit": 2, "offset": 1})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["total"] == 3 and cuerpo["limit"] == 2 and cuerpo["offset"] == 1
    assert [j["dorsal"] for j in cuerpo["items"]] == [2, 3]
    documentado(r, "get", "/equipos/{codigo}/jugadores")


def test_jugadores_filtro_posicion_sin_resultados_es_200_vacio(client, repo):
    r = client.get("/equipos/ARG/jugadores", params={"posicion": "Delantero"})
    assert r.status_code == 200 and r.json()["items"] == [] and r.json()["total"] == 0


def test_equipo_sin_jugadores_cargados_es_200_vacio(client, repo):
    r = client.get("/equipos/BRA/jugadores")
    assert r.status_code == 200 and r.json()["items"] == []


def test_jugadores_equipo_inexistente_404(client, repo):
    assert client.get("/equipos/ZZZ/jugadores").status_code == 404


def test_offset_mayor_al_total_devuelve_lista_vacia_sin_listar(client, repo):
    r = client.get("/equipos/ARG/jugadores", params={"offset": 50})
    assert r.status_code == 200 and r.json()["items"] == []
    assert "listar" not in repo.llamadas


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": -1}, {"limit": 101}, {"offset": -1}, {"posicion": "Arquero"}])
def test_parametros_de_consulta_invalidos(client, repo, params, documentado):
    r = client.get("/equipos/ARG/jugadores", params=params)
    assert r.status_code == 422
    assert repo.llamadas == []
    documentado(r, "get", "/equipos/{codigo}/jugadores")


def test_dependencia_caida_da_503(app, client, documentado):
    class Caido:
        def obtener_equipo(self, codigo):
            raise DependenciaNoDisponible("mongodb")

    app.dependency_overrides[get_equipos_service] = lambda: EquiposService(Caido())
    r = client.get("/equipos/ARG")
    assert r.status_code == 503 and r.json()["error"]["codigo"] == "DEPENDENCIA_NO_DISPONIBLE"
    documentado(r, "get", "/equipos/{codigo}")
