import pytest

from app.deps import get_sesiones_service
from app.services.sesiones import SesionesService

ACTIVA = {"session_id": "S-DEMO-001", "usuario_id": "U001", "rol": "fan", "estado_acceso": "ACTIVA",
          "creado_en": "2030-06-14T10:00:00-03:00", "ultimo_acceso": "2030-06-14T10:05:00-03:00", "acciones": "1",
          "token_ref": "DEMO-NO-SECRETO-001", "ttl": 1750}
CERRADA = {**ACTIVA, "usuario_id": "U002", "estado_acceso": "CERRADA"}


class RepoFalso:
    def __init__(self):
        self.llamadas, self.datos = [], {"U001": ACTIVA, "U002": CERRADA}

    def obtener_sesion(self, uid):
        self.llamadas.append(("get", uid))
        return self.datos.get(uid)

    def invalidar_sesion(self, uid):
        self.llamadas.append(("del", uid))
        return self.datos.pop(uid, None) is not None


@pytest.fixture
def repo(app):
    r = RepoFalso()
    app.dependency_overrides[get_sesiones_service] = lambda: SesionesService(r)
    return r


def test_sesion_vigente_oculta_token_ref(client, repo, documentado):
    r = client.get("/sesiones/U001")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["usuario_id"] == "U001" and cuerpo["acciones"] == 1 and cuerpo["ttl_segundos"] == 1750
    assert "token_ref" not in cuerpo
    documentado(r, "get", "/sesiones/{usuario_id}")


def test_sesion_inexistente_o_expirada_404(client, repo, documentado):
    r = client.get("/sesiones/U999")
    assert r.status_code == 404 and r.json()["error"]["codigo"] == "SESION_NO_VIGENTE"
    documentado(r, "get", "/sesiones/{usuario_id}")


def test_sesion_cerrada_no_es_vigente(client, repo):
    r = client.get("/sesiones/U002")
    assert r.status_code == 404 and r.json()["error"]["codigo"] == "SESION_NO_VIGENTE"


@pytest.mark.parametrize("uid", ["u001", "U1", "USER001", "U001*", "*"])
def test_usuario_invalido_no_consulta(client, repo, uid):
    assert client.get(f"/sesiones/{uid}").status_code in (404, 422)
    assert repo.llamadas == []


def test_invalidar_es_idempotente(client, repo, documentado):
    r1, r2 = client.delete("/sesiones/U001"), client.delete("/sesiones/U001")
    assert (r1.status_code, r2.status_code) == (204, 204) and r1.content == b""
    documentado(r1, "delete", "/sesiones/{usuario_id}")
    assert client.get("/sesiones/U001").status_code == 404
