from datetime import datetime, timezone

import pytest

from app.deps import get_comentarios_service
from app.errors import Conflicto
from app.services.comentarios import ComentariosService, codificar_cursor, decodificar_cursor, piso_ventana

VENTANA = "2030-06-15T18:30:00Z"
CUERPO = {"pais": "ARG", "usuario_id": "U001", "usuario_nombre": "Facundo", "contenido": "¡Vamos Argentina! ⚽"}


class RepoFalso:
    def __init__(self):
        self.llamadas = []
        self.claves = {}  # clave -> (partido, pais, comentario)
        self.paginas = [
            ([{"comentario_id": "c2", "usuario_id": "U001", "usuario_nombre": "F", "contenido": "b", "likes": 0,
               "estado_moderacion": "PUBLICADO", "creado_en": "2030-06-15T18:42:10.000Z"}], b"estado1"),
            ([{"comentario_id": "c1", "usuario_id": "U002", "usuario_nombre": "G", "contenido": "a", "likes": 3,
               "estado_moderacion": "PUBLICADO", "creado_en": "2030-06-15T18:41:00.000Z"}], None),
        ]

    def listar(self, partido_id, pais, ventana, limit, paging_state):
        self.llamadas.append(("listar", partido_id, pais, ventana, limit, paging_state))
        return self.paginas[1 if paging_state else 0]

    def registrar(self, *, clave, partido_id, pais, ventana, creado_en, usuario_id, usuario_nombre, contenido):
        self.llamadas.append(("registrar", clave, ventana))
        previo = self.claves.get(clave)
        if previo and (previo[0], previo[1]) != (partido_id, pais):
            raise Conflicto("La Idempotency-Key ya se usó para otro comentario.")
        if previo:
            return previo[2], False
        com = {"comentario_id": "id-" + clave, "partido_id": partido_id, "pais": pais, "ventana": "x", "creado_en": "y",
               "usuario_id": usuario_id, "usuario_nombre": usuario_nombre, "contenido": contenido, "likes": 0,
               "estado_moderacion": "PUBLICADO"}
        self.claves[clave] = (partido_id, pais, com)
        return com, True


class PartidosFalso:
    def obtener_partido(self, pid):
        return {"id": pid} if pid in ("P-01", "P-02") else None


@pytest.fixture
def repo(app):
    r = RepoFalso()
    ahora = lambda: datetime(2030, 6, 15, 18, 47, 12, 345000, tzinfo=timezone.utc)
    app.dependency_overrides[get_comentarios_service] = lambda: ComentariosService(r, PartidosFalso(), ahora=ahora)
    return r


def test_listar_ok_y_cursor(client, repo, documentado):
    r = client.get("/partidos/P-01/comentarios", params={"pais": "ARG", "ventana": VENTANA, "limit": 1})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["items"][0]["comentario_id"] == "c2"
    assert cuerpo["next_cursor"] == codificar_cursor(b"estado1")
    documentado(r, "get", "/partidos/{partido_id}/comentarios")
    r2 = client.get("/partidos/P-01/comentarios",
                    params={"pais": "ARG", "ventana": VENTANA, "limit": 1, "cursor": cuerpo["next_cursor"]})
    assert r2.json()["items"][0]["comentario_id"] == "c1" and r2.json()["next_cursor"] is None
    assert repo.llamadas[-1][-1] == b"estado1"


def test_particion_vacia_es_200_vacio(client, repo):
    repo.paginas[0] = ([], None)
    r = client.get("/partidos/P-01/comentarios", params={"pais": "ARG", "ventana": VENTANA})
    assert r.status_code == 200 and r.json()["items"] == []


@pytest.mark.parametrize("params", [
    {"ventana": VENTANA},                                    # falta pais
    {"pais": "ARG"},                                         # falta ventana (clave de partición)
    {"pais": "arg", "ventana": VENTANA},
    {"pais": "ARG", "ventana": "2030-06-15T18:30:00"},       # sin zona horaria
    {"pais": "ARG", "ventana": "2030-06-15T18:45:00Z"},      # no alineada a :00/:30
    {"pais": "ARG", "ventana": "2030-06-15T18:30:15Z"},      # segundos
    {"pais": "ARG", "ventana": "2030-13-40T18:30:00Z"},      # fecha imposible
    {"pais": "ARG", "ventana": VENTANA, "limit": 0},
    {"pais": "ARG", "ventana": VENTANA, "limit": 101},
    {"pais": "ARG", "ventana": VENTANA, "cursor": "%%%no-es-base64%%%"},
])
def test_listar_invalido_no_consulta(client, repo, params, documentado):
    r = client.get("/partidos/P-01/comentarios", params=params)
    assert r.status_code == 422
    assert repo.llamadas == []
    documentado(r, "get", "/partidos/{partido_id}/comentarios")


def test_crear_201_y_repeticion_200_mismo_registro(client, repo, documentado):
    h = {"Idempotency-Key": "clave-123456"}
    r1 = client.post("/partidos/P-01/comentarios", json=CUERPO, headers=h)
    r2 = client.post("/partidos/P-01/comentarios", json=CUERPO, headers=h)
    assert (r1.status_code, r2.status_code) == (201, 200)
    assert r1.json()["comentario_id"] == r2.json()["comentario_id"]
    assert r1.json()["contenido"] == "¡Vamos Argentina! ⚽"
    documentado(r1, "post", "/partidos/{partido_id}/comentarios")
    documentado(r2, "post", "/partidos/{partido_id}/comentarios")


def test_misma_clave_otro_partido_es_409(client, repo, documentado):
    h = {"Idempotency-Key": "clave-123456"}
    client.post("/partidos/P-01/comentarios", json=CUERPO, headers=h)
    r = client.post("/partidos/P-02/comentarios", json=CUERPO, headers=h)
    assert r.status_code == 409
    documentado(r, "post", "/partidos/{partido_id}/comentarios")


def test_ventana_de_escritura_se_calcula_en_el_servidor(client, repo):
    client.post("/partidos/P-01/comentarios", json=CUERPO, headers={"Idempotency-Key": "clave-123456"})
    _, _, ventana = repo.llamadas[-1]
    assert ventana == datetime(2030, 6, 15, 18, 30)  # 18:47 -> ventana de 30 min que empieza 18:30
    assert piso_ventana(datetime(2030, 6, 15, 19, 0, 0)) == datetime(2030, 6, 15, 19, 0)


def test_partido_inexistente_no_escribe(client, repo):
    r = client.post("/partidos/P-99/comentarios", json=CUERPO, headers={"Idempotency-Key": "clave-123456"})
    assert r.status_code == 404 and not any(c[0] == "registrar" for c in repo.llamadas)


@pytest.mark.parametrize("cambio", [
    {"contenido": ""}, {"contenido": "x" * 281}, {"pais": "ar"}, {"usuario_id": "usuario1"},
    {"usuario_nombre": ""}, {"extra": "no permitido"},
])
def test_cuerpo_invalido(client, repo, cambio, documentado):
    r = client.post("/partidos/P-01/comentarios", json={**CUERPO, **cambio}, headers={"Idempotency-Key": "clave-123456"})
    assert r.status_code == 422 and repo.llamadas == []
    documentado(r, "post", "/partidos/{partido_id}/comentarios")


@pytest.mark.parametrize("clave", [None, "corta", "con espacios no", "x" * 65])
def test_idempotency_key_obligatoria_y_valida(client, repo, clave):
    headers = {"Idempotency-Key": clave} if clave else {}
    r = client.post("/partidos/P-01/comentarios", json=CUERPO, headers=headers)
    assert r.status_code == 422 and repo.llamadas == []


def test_contenido_de_280_caracteres_con_unicode_es_valido(client, repo):
    r = client.post("/partidos/P-01/comentarios", json={**CUERPO, "contenido": "⚽" * 280},
                    headers={"Idempotency-Key": "clave-123456"})
    assert r.status_code == 201


def test_cursor_roundtrip():
    assert decodificar_cursor(codificar_cursor(b"\x00\xffabc")) == b"\x00\xffabc"
    assert codificar_cursor(None) is None and decodificar_cursor(None) is None
