import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def documentado(app):
    """Verifica que el código HTTP devuelto esté documentado en OpenAPI para esa operación."""
    spec = app.openapi()

    def _check(resp, metodo, plantilla):
        operacion = spec["paths"][plantilla][metodo.lower()]
        assert str(resp.status_code) in operacion["responses"], (
            f"{resp.status_code} no está documentado en {metodo} {plantilla}: {list(operacion['responses'])}"
        )
        cuerpo = resp.json() if resp.content else {}
        if resp.status_code >= 400 and "error" in cuerpo:
            assert {"codigo", "mensaje", "request_id"} <= set(cuerpo["error"])

    return _check
