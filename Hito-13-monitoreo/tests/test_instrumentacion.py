"""Instrumentación de la API sin bases reales: solo métricas en memoria."""
from contextlib import contextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api_instrumentada import instrumentar, metricas
from api_instrumentada.main import create_app


def muestra(nombre, **etiquetas):
    valor = metricas.REGISTRO.get_sample_value(nombre, etiquetas)
    return valor or 0.0


def test_metrics_expone_series_propias():
    client = TestClient(create_app())
    client.get("/docs")
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "fixture2030_http_requests_total" in resp.text


def test_endpoint_usa_plantilla():
    app = FastAPI()
    app.middleware("http")(instrumentar.middleware_http)

    @app.get("/partidos/{partido_id}")
    def partido(partido_id: str):
        return {"id": partido_id}

    client = TestClient(app)
    antes = muestra("fixture2030_http_requests_total", endpoint="/partidos/{partido_id}", metodo="GET", codigo="200")
    sin_ruta = muestra("fixture2030_http_requests_total", endpoint="sin_ruta", metodo="GET", codigo="404")
    client.get("/partidos/P-01")
    client.get("/no-existe")
    assert muestra("fixture2030_http_requests_total", endpoint="/partidos/{partido_id}", metodo="GET", codigo="200") == antes + 1
    assert muestra("fixture2030_http_requests_total", endpoint="sin_ruta", metodo="GET", codigo="404") == sin_ruta + 1
    texto = TestClient(create_app()).get("/metrics").text
    assert "P-01" not in texto and "/no-existe" not in texto


def test_operacion_ok_y_error():
    @contextmanager
    def original(fuente, nombre, traducir):
        yield

    envuelta = instrumentar.envolver_operacion(original)
    etiquetas_ok = dict(fuente="redis", operacion="leer_prueba", resultado="ok")
    etiquetas_error = dict(fuente="redis", operacion="leer_prueba", resultado="error")
    ok = muestra("fixture2030_dependencia_duracion_seconds_count", **etiquetas_ok)
    error = muestra("fixture2030_dependencia_duracion_seconds_count", **etiquetas_error)

    with envuelta("redis", "leer_prueba", None):
        pass
    with pytest.raises(ValueError):
        with envuelta("redis", "leer_prueba", None):
            raise ValueError("falla")

    assert muestra("fixture2030_dependencia_duracion_seconds_count", **etiquetas_ok) == ok + 1
    assert muestra("fixture2030_dependencia_duracion_seconds_count", **etiquetas_error) == error + 1


def test_comentario_por_pais_solo_altas():
    from app.services.comentarios import ComentariosService

    instrumentar.instrumentar_comentarios()

    class Repo:
        def __init__(self):
            self.respuestas = [({"comentario_id": "c1"}, True), ({"comentario_id": "c1"}, False)]

        def registrar(self, **_):
            return self.respuestas.pop(0)

    class Partidos:
        def obtener_partido(self, partido_id):
            return {"id": partido_id}

    svc = ComentariosService(Repo(), Partidos())
    antes = muestra("fixture2030_comentarios_creados_total", pais="URU")
    datos = {"pais": "URU", "usuario_id": "U001", "usuario_nombre": "Ana", "contenido": "hola"}
    svc.crear("P-01", "clave-prueba-1", datos)
    svc.crear("P-01", "clave-prueba-1", datos)
    assert muestra("fixture2030_comentarios_creados_total", pais="URU") == antes + 1


def test_instrumentar_dos_veces_no_duplica():
    from app.services.comentarios import ComentariosService

    instrumentar.instrumentar_comentarios()
    primera = ComentariosService.crear
    instrumentar.instrumentar_comentarios()
    assert ComentariosService.crear is primera


def test_disponibilidad_si_la_fabrica_falla():
    def rota():
        raise RuntimeError("sin configuración")

    valores = [m.value for f in instrumentar.ColectorDisponibilidad(rota).collect() for m in f.samples]
    assert len(valores) == 6 and all(v == 0 for v in valores)


def test_disponibilidad_no_espera_a_una_base_colgada():
    import time

    class Rapido:
        def ping(self):
            return None

    class Colgado:
        def ping(self):
            time.sleep(1.5)

    class Roto:
        def ping(self):
            raise RuntimeError("sin conexión")

    colector = instrumentar.ColectorDisponibilidad(
        lambda: {"mongodb": Rapido(), "redis": Colgado(), "neo4j": Roto()}, limite_segundos=0.3)
    inicio = time.perf_counter()
    valores = {m.labels["fuente"]: m.value for f in colector.collect() for m in f.samples}
    assert time.perf_counter() - inicio < 1.0
    assert valores["mongodb"] == 1
    assert valores["redis"] == 0
    assert valores["neo4j"] == 0
