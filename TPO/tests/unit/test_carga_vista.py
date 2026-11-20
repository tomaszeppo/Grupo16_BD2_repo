from carga.ejecutar import _vista_partido


def test_vista_en_juego_consulta_las_cuatro_rutas_por_http():
    siguiente = _vista_partido("P-15", "ARG", False)
    pedidos = [siguiente(0) for _ in range(4)]
    assert all(p["metodo"] == "GET" for p in pedidos)
    assert [p["url"] for p in pedidos] == [
        "/en-vivo/partidos/P-15", "/partidos/P-15/estadisticas",
        "/partidos/P-15/jugadas/temporales", "/partidos/P-15/comentarios?pais=ARG",
    ]
    assert siguiente(0) == pedidos[0]
    assert siguiente(1) == pedidos[0]  # cada usuario tiene su propia secuencia


def test_vista_finalizada_usa_el_mismo_historial_y_la_escritura_lleva_sesion_e_id():
    siguiente = _vista_partido("P-15", "ARG", True)
    assert [siguiente(0) for _ in range(4)][-1]["url"] == "/partidos/P-15/comentarios?pais=ARG"
    siguiente = _vista_partido("P-15", "ARG", False, "token-de-sesion")
    primero = [siguiente(0) for _ in range(5)][-1]
    segundo = [siguiente(0) for _ in range(5)][-1]
    assert primero["metodo"] == "POST" and primero["headers"] == {"X-Sesion": "token-de-sesion"}
    assert primero["json"]["contenido"] and primero["json"]["comentario_id"] != segundo["json"]["comentario_id"]
