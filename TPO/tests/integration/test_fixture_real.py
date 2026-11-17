def test_fase_de_grupos_tiene_72_partidos(cliente):
    cuerpo = cliente.get("/partidos", params={"fase": "Fase de grupos"}).json()
    assert cuerpo["total"] == 72
    primero = cuerpo["partidos"][0]
    assert primero["id"] == "P-01"
    assert primero["estado"] == "Finalizado" and primero["goles_local"] is not None
    assert primero["local"]["codigo"] and primero["visitante"]["codigo"] and primero["estadio"]["id"]


def test_filtro_por_fecha_y_estado(cliente):
    assert cliente.get("/partidos", params={"fecha": "2030-06-13"}).json()["total"] == 3
    assert cliente.get("/partidos", params={"estado": "Finalizado"}).json()["total"] == 2
    assert cliente.get("/partidos").json()["total"] == 104


def test_detalle_coincide_con_los_datos_cargados(cliente, cargado):
    esperado = next(p for p in cargado.partidos if p["id"] == "P-03")
    partido = cliente.get("/partidos/P-03").json()["partido"]
    assert partido["local"]["codigo"] == esperado["local"]
    assert partido["visitante"]["codigo"] == esperado["visitante"]
    assert partido["fecha_hora"].startswith("2030-06-13T15:00:00")
    final = cliente.get("/partidos/P-104").json()["partido"]
    assert final["local"] is None and final["visitante"] is None


def test_eventos_iguales_a_los_cargados_y_en_orden(cliente, cargado):
    eventos = cliente.get("/partidos/P-01/eventos").json()["eventos"]
    assert [e["id"] for e in eventos] == [e["id"] for e in cargado.eventos["P-01"]]
    con_jugador = next(e for e in eventos if e["tipo"] == "Gol")
    assert con_jugador["jugador"]["equipo"] and con_jugador["jugador"]["apellido"]
    assert eventos[0]["jugador"] is None


def test_cadena_de_un_gol(cliente):
    eventos = cliente.get("/partidos/P-01/eventos").json()["eventos"]
    gol = next(e for e in eventos if e["tipo"] == "Gol")
    cadena = cliente.get(f"/partidos/P-01/eventos/{gol['id']}/cadena").json()["cadena"]
    assert [e["tipo"] for e in cadena] == ["Pase", "Tiro", "Gol"]
    assert cadena[-1]["id"] == gol["id"]
    # un evento de otro partido no se encuentra bajo este
    assert cliente.get(f"/partidos/P-02/eventos/{gol['id']}/cadena").status_code == 404


def test_participacion_en_goles(cliente, cargado):
    cuerpo = cliente.get("/estadisticas/participacion-en-goles", params={"limit": 5}).json()
    filas = cuerpo["jugadores"]
    assert 0 < len(filas) <= 5
    assert [f["participaciones"] for f in filas] == sorted((f["participaciones"] for f in filas), reverse=True)
    goles_cargados = sum(1 for es in cargado.eventos.values() for e in es if e["tipo"] == "Gol")
    todas = cliente.get("/estadisticas/participacion-en-goles", params={"limit": 100}).json()["jugadores"]
    assert sum(f["goles"] for f in todas) == goles_cargados
    assert all(f["participaciones"] >= f["goles"] for f in todas)


def test_camino_de_un_equipo_en_grupos(cliente):
    cuerpo = cliente.get("/equipos/ARG/camino").json()
    assert cuerpo["equipo"] == {"codigo": "ARG", "nombre": "Argentina"}
    assert len(cuerpo["partidos"]) == 3
    assert all(p["rival"]["codigo"] != "ARG" for p in cuerpo["partidos"])
    assert cuerpo["camino_a_la_final"] == []


def test_camino_por_el_cuadro_cuando_el_equipo_esta_en_eliminatorias(cliente, neo4j):
    neo4j._escribir("""MATCH (e:Equipo {codigo: 'ARG'}), (p:Partido {id: 'P-73'})
                       MERGE (e)-[:PARTICIPA_EN {condicion: 'local'}]->(p)""")
    cuerpo = cliente.get("/equipos/ARG/camino").json()
    assert len(cuerpo["partidos"]) == 4
    assert [p["fase"] for p in cuerpo["camino_a_la_final"]] == ["Octavos", "Cuartos", "Semifinal", "Final"]


def test_inexistentes(cliente):
    assert cliente.get("/partidos/P-999").status_code == 404
    assert cliente.get("/partidos/P-999/eventos").status_code == 404
    assert cliente.get("/equipos/XXX/camino").status_code == 404
