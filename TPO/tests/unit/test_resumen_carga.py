import pytest

from carga.resumen import linea_de_tiempo, percentil, resumir


def filas(ms_y_estados, ruta="/x"):
    return [{"t": i * 0.1, "ruta": ruta, "estado": estado, "ms": ms} for i, (ms, estado) in enumerate(ms_y_estados)]


def test_percentiles_por_rango_mas_cercano():
    valores = list(range(1, 101))  # 1..100
    assert percentil(valores, 50) == 50
    assert percentil(valores, 95) == 95
    assert percentil(valores, 99) == 99
    assert percentil(valores, 100) == 100
    assert percentil([7], 99) == 7
    assert percentil([10, 20], 50) == 10


def test_resumen_de_una_corrida():
    datos = filas([(float(n), 200) for n in range(1, 101)])
    r = resumir(datos, duracion_segundos=10)
    assert r["total"] == 100
    assert r["por_segundo"] == 10.0
    assert (r["p50_ms"], r["p95_ms"], r["p99_ms"], r["max_ms"]) == (50.0, 95.0, 99.0, 100.0)
    assert r["exitosos"] == 100 and r["errores"] == 0 and r["errores_por_estado"] == {}
    assert r["porcentaje_de_error"] == 0.0


def test_los_errores_se_cuentan_por_estado_y_no_entran_en_la_latencia_de_exitosos():
    datos = filas([(10.0, 200), (12.0, 201), (3000.0, 503), (5.0, 409), (9000.0, 0)])
    r = resumir(datos, duracion_segundos=1)
    assert r["total"] == 5 and r["exitosos"] == 2 and r["errores"] == 3
    assert r["errores_por_estado"] == {"0": 1, "409": 1, "503": 1}
    assert r["porcentaje_de_error"] == 60.0
    assert r["max_ms"] == 12.0  # latencia medida sobre los pedidos exitosos
    assert r["max_ms_incluyendo_errores"] == 9000.0


def test_estados_esperados_no_son_error():
    datos = filas([(10.0, 409), (10.0, 200)])
    assert resumir(datos, 1, estados_esperados={200, 409})["errores"] == 0


def test_desglose_por_ruta():
    datos = filas([(10.0, 200)] * 3, "/a") + filas([(20.0, 200)] * 2, "/b")
    r = resumir(datos, 1)
    assert r["por_ruta"]["/a"]["total"] == 3 and r["por_ruta"]["/b"]["p50_ms"] == 20.0


def test_lista_vacia_no_rompe():
    r = resumir([], duracion_segundos=5)
    assert r["total"] == 0 and r["por_segundo"] == 0.0 and r["p95_ms"] is None and r["por_ruta"] == {}
    assert linea_de_tiempo([]) == []


def test_linea_de_tiempo_por_segundo():
    datos = [{"t": 0.2, "ruta": "/x", "estado": 200, "ms": 5.0}, {"t": 0.9, "ruta": "/x", "estado": 503, "ms": 5.0},
             {"t": 2.1, "ruta": "/x", "estado": 200, "ms": 7.0}]
    assert linea_de_tiempo(datos) == [
        {"segundo": 0, "total": 2, "errores": 1, "estados": {"200": 1, "503": 1}},
        {"segundo": 1, "total": 0, "errores": 0, "estados": {}},
        {"segundo": 2, "total": 1, "errores": 0, "estados": {"200": 1}},
    ]


def test_percentil_de_lista_vacia():
    with pytest.raises(ValueError):
        percentil([], 50)
