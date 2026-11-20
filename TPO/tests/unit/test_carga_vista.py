from carga.ejecutar import _vista_partido


def test_vista_en_juego_consulta_las_cuatro_rutas_por_http():
    siguiente = _vista_partido("P-15", "ARG", False)
    pedidos = [siguiente(0) for _ in range(4)]
    assert all(p["metodo"] == "GET" for p in pedidos)
    assert [p["url"] for p in pedidos] == [
        "/en-vivo/partidos/P-15", "/partidos/P-15/estadisticas",
        "/partidos/P-15/jugadas/temporales", "/partidos/P-15/comentarios/recientes?pais=ARG",
    ]
    assert siguiente(0) == pedidos[0]
    assert siguiente(1) == pedidos[0]  # cada usuario tiene su propia secuencia


def test_vista_finalizada_usa_historial_y_escritura_es_opcional():
    siguiente = _vista_partido("P-15", "ARG", True)
    assert [siguiente(0) for _ in range(4)][-1]["url"].endswith("/comentarios/historial?pais=ARG")
    siguiente = _vista_partido("P-15", "ARG", False, "U0000001")
    comentario = [siguiente(0) for _ in range(5)][-1]
    assert comentario["metodo"] == "POST"
    assert comentario["headers"] == {"X-Usuario-Id": "U0000001"}
    assert comentario["json"]["contenido"]
