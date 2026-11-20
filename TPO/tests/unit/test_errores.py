from app.errors import Conflicto

CAMPOS = {"codigo", "mensaje", "request_id"}


def test_ruta_inexistente_usa_el_formato_de_error(cliente):
    resp = cliente.get("/no-existe")
    assert resp.status_code == 404
    assert CAMPOS <= set(resp.json()["error"])
    assert resp.json()["error"]["codigo"] == "NO_ENCONTRADO"


def test_api_error_usa_el_formato_de_error(app, cliente):
    @app.get("/_prueba/conflicto")
    def _lanzar():
        raise Conflicto("No se puede.")

    resp = cliente.get("/_prueba/conflicto")
    assert resp.status_code == 409
    assert resp.json()["error"]["codigo"] == "CONFLICTO"
    assert resp.json()["error"]["mensaje"] == "No se puede."
    assert resp.json()["error"]["request_id"] == resp.headers["X-Request-ID"]


def test_error_inesperado_no_filtra_detalles(app, cliente):
    @app.get("/_prueba/rota")
    def _romper():
        raise RuntimeError("clave secreta en el mensaje")

    resp = cliente.get("/_prueba/rota")
    assert resp.status_code == 500
    assert resp.json()["error"]["codigo"] == "ERROR_INTERNO"
    assert "secreta" not in resp.text


def _registros(caplog):
    return [(r.levelname, r.getMessage().split(" ")[0]) for r in caplog.records if r.name == "prode2030"]


def test_el_registro_normal_solo_anota_los_pedidos_con_problemas(cliente, neo4j, caplog):
    """Anotar cada pedido y cada operación costaba cerca de la mitad del rendimiento (ver docs/rendimiento.md)."""
    import logging

    with caplog.at_level(logging.INFO, logger="prode2030"):
        assert cliente.get("/partidos/P-03").status_code == 200
        assert _registros(caplog) == []
        assert cliente.get("/partidos/P-999").status_code == 404
        neo4j.caida = True
        assert cliente.get("/partidos/P-03").status_code == 503
    assert _registros(caplog) == [("WARNING", "request"), ("WARNING", "request")]


def test_con_nivel_debug_se_anota_cada_pedido(cliente, caplog):
    import logging

    with caplog.at_level(logging.DEBUG, logger="prode2030"):
        cliente.get("/partidos/P-03")
    mensajes = [r.getMessage() for r in caplog.records if r.name == "prode2030"]
    assert any(m.startswith("request metodo=GET ruta=/partidos/P-03 status=200") for m in mensajes)


def test_las_operaciones_contra_una_base_se_anotan_solo_si_fallan(caplog):
    import logging

    from app.adapters.base import operacion
    from app.errors import DependenciaNoDisponible

    with caplog.at_level(logging.INFO, logger="prode2030"):
        with operacion("mongodb", "prueba_de_registro", lambda exc: DependenciaNoDisponible("mongodb")):
            pass
        assert _registros(caplog) == []
        try:
            with operacion("mongodb", "prueba_de_registro", lambda exc: DependenciaNoDisponible("mongodb")):
                raise ConnectionError("clave secreta en el mensaje")
        except DependenciaNoDisponible:
            pass
    assert _registros(caplog) == [("WARNING", "dependencia=mongodb")]
    assert "secreta" not in caplog.text and "causa=ConnectionError" in caplog.text


def test_flujo_en_vivo_no_corta_por_el_tope_de_duracion():
    """La conexión en vivo dura todo el partido: el tope por pedido no puede cortarla. El resto sí se corta."""
    import asyncio

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.observability import crear_middleware, es_flujo_en_vivo

    app = FastAPI()
    app.middleware("http")(crear_middleware(0.1))

    @app.get("/partidos/{partido_id}/vivo")
    async def vivo(partido_id: str):
        await asyncio.sleep(0.3)
        return {"ok": True}

    @app.get("/lento")
    async def lento():
        await asyncio.sleep(0.3)
        return {"ok": True}

    cliente = TestClient(app)
    respuesta = cliente.get("/partidos/P-01/vivo")
    assert respuesta.status_code == 200 and respuesta.headers["X-Request-ID"]
    assert cliente.get("/lento").status_code == 504
    assert es_flujo_en_vivo("/partidos/P-01/vivo") and not es_flujo_en_vivo("/partidos/P-01/vivo/otra")
