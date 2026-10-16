import logging

import pytest

from app.adapters.base import operacion
from app.errors import ApiError, DependenciaNoDisponible, NoEncontrado


def test_ruta_inexistente_usa_formato_de_error(client):
    r = client.get("/no-existe")
    assert r.status_code == 404
    error = r.json()["error"]
    assert error["codigo"] == "NO_ENCONTRADO"
    assert error["request_id"] == r.headers["X-Request-ID"]


def test_request_id_del_cliente_se_respeta(client):
    r = client.get("/no-existe", headers={"X-Request-ID": "abc-123"})
    assert r.headers["X-Request-ID"] == "abc-123"


def test_request_id_hostil_se_reemplaza(client):
    for hostil in ("x" * 200, "a b;<script>"):
        r = client.get("/no-existe", headers={"X-Request-ID": hostil})
        rid = r.headers["X-Request-ID"]
        assert rid != hostil and 0 < len(rid) <= 64 and rid.replace("-", "").isalnum()


def test_error_inesperado_es_500_generico(app, client):
    app.add_api_route("/boom", lambda: 1 / 0)
    r = client.get("/boom")
    assert r.status_code == 500
    error = r.json()["error"]
    assert error["codigo"] == "ERROR_INTERNO"
    assert "division" not in error["mensaje"].lower()
    assert r.headers["X-Request-ID"] == error["request_id"]


def test_la_api_arranca_sin_ninguna_base(client):
    assert client.get("/openapi.json").status_code == 200


def test_operacion_traduce_sin_filtrar_detalle(caplog):
    def traducir(exc):
        return DependenciaNoDisponible("redis") if isinstance(exc, ConnectionError) else None

    with caplog.at_level(logging.INFO, logger="fixture2030"):
        with pytest.raises(DependenciaNoDisponible) as e:
            with operacion("redis", "get", traducir):
                raise ConnectionError("password=SECRETO host=10.0.0.1")
    assert "SECRETO" not in str(e.value)
    assert "SECRETO" not in caplog.text
    assert "dependencia=redis" in caplog.text and "operacion=get" in caplog.text


def test_operacion_deja_pasar_errores_de_dominio_y_bugs():
    with pytest.raises(NoEncontrado):
        with operacion("x", "y", lambda e: None):
            raise NoEncontrado("nada")
    with pytest.raises(ValueError):
        with operacion("x", "y", lambda e: None):
            raise ValueError("bug")
    assert issubclass(NoEncontrado, ApiError)
