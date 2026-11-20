import re

from tests.conftest import ADMIN
from tests.apoyo import entrar


def valor(texto: str, nombre: str, **etiquetas) -> float:
    """Suma las muestras de una métrica que tengan todas las etiquetas pedidas."""
    total = 0.0
    for linea in texto.splitlines():
        if not linea.startswith(nombre + "{") and not linea.startswith(nombre + " "):
            continue
        if all(f'{k}="{v}"' in linea for k, v in etiquetas.items()):
            total += float(linea.rsplit(" ", 1)[1])
    return total


def metricas(cliente) -> str:
    resp = cliente.get("/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    return resp.text


def test_cuenta_pedidos_por_plantilla_de_ruta_y_no_por_ruta_real(cliente):
    antes = valor(metricas(cliente), "prode_api_pedidos_total", metodo="GET", ruta="/partidos/{partido_id}", estado="200")
    cliente.get("/partidos/P-03")
    cliente.get("/partidos/P-04")
    texto = metricas(cliente)
    assert valor(texto, "prode_api_pedidos_total", metodo="GET", ruta="/partidos/{partido_id}", estado="200") == antes + 2
    assert "P-03" not in texto and "P-04" not in texto
    assert valor(texto, "prode_api_duracion_segundos_count", metodo="GET", ruta="/partidos/{partido_id}") >= 2


def test_los_errores_se_cuentan_con_su_estado_y_las_rutas_inexistentes_no_inventan_etiquetas(cliente):
    antes = metricas(cliente)
    cliente.get("/partidos/P-999")
    cliente.get("/no-existe/123456")
    texto = metricas(cliente)
    assert (valor(texto, "prode_api_pedidos_total", ruta="/partidos/{partido_id}", estado="404")
            == valor(antes, "prode_api_pedidos_total", ruta="/partidos/{partido_id}", estado="404") + 1)
    assert "123456" not in texto
    assert valor(texto, "prode_api_pedidos_total", ruta="(sin ruta)", estado="404") >= 1


def test_metrics_no_se_cuenta_a_si_misma(cliente):
    metricas(cliente)
    metricas(cliente)
    assert not re.search(r'prode_api_pedidos_total\{[^}]*ruta="/metrics"', metricas(cliente))


def test_estado_del_calendario(cliente):
    texto = metricas(cliente)
    assert valor(texto, "prode_calendario_desactualizado") == 1  # todavía no se cargó
    cliente.get("/health/dependencias")
    crear = cliente.post("/usuarios", json={"nombre": "Ana", "pais": "ARG"}).json()["usuario"]["id"]
    cliente.put("/partidos/P-03/pronostico", json={"goles_local": 1, "goles_visitante": 0},
                headers=entrar(cliente, crear))
    texto = metricas(cliente)
    assert valor(texto, "prode_calendario_desactualizado") == 0
    assert "prode_calendario_antiguedad_segundos" in texto


def test_la_puntuacion_deja_su_duracion_por_paso(cliente):
    antes = metricas(cliente)
    cliente.post("/partidos/P-03/estado", json={"estado": "En juego"}, headers=ADMIN)
    cliente.post("/partidos/P-03/resultado", json={"goles_local": 1, "goles_visitante": 0}, headers=ADMIN)
    texto = metricas(cliente)
    for paso in ("puntuar", "sumar", "foto"):
        assert (valor(texto, "prode_puntuacion_duracion_segundos_count", paso=paso)
                == valor(antes, "prode_puntuacion_duracion_segundos_count", paso=paso) + 1)


def test_las_operaciones_contra_una_base_se_miden_con_su_resultado():
    from app.adapters.base import operacion
    from app.errors import DependenciaNoDisponible
    from app.metricas import texto_de_metricas

    def traducir(exc):
        return DependenciaNoDisponible("mongodb")

    antes = texto_de_metricas()
    with operacion("mongodb", "operacion_de_prueba", traducir):
        pass
    try:
        with operacion("mongodb", "operacion_de_prueba", traducir):
            raise ConnectionError("sin red")
    except DependenciaNoDisponible:
        pass
    texto = texto_de_metricas()
    etiquetas = dict(base="mongodb", operacion="operacion_de_prueba")
    assert valor(texto, "prode_base_operaciones_total", resultado="ok", **etiquetas) == valor(
        antes, "prode_base_operaciones_total", resultado="ok", **etiquetas) + 1
    assert valor(texto, "prode_base_operaciones_total", resultado="dependencia_no_disponible", **etiquetas) == valor(
        antes, "prode_base_operaciones_total", resultado="dependencia_no_disponible", **etiquetas) + 1
    assert valor(texto, "prode_base_duracion_segundos_count", **etiquetas) >= 2
