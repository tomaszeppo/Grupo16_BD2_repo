import pytest


def test_listado_completo_ordenado_y_con_fuente(cliente):
    resp = cliente.get("/partidos")
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["fuente"] == "neo4j"
    assert cuerpo["total"] == 128
    assert cuerpo["partidos"][0]["id"] == "P-01"
    assert cuerpo["partidos"][2]["local"]["codigo"]


def test_filtros_de_fase_estado_y_fecha(cliente):
    assert cliente.get("/partidos", params={"fase": "Fase de grupos"}).json()["total"] == 96
    assert cliente.get("/partidos", params={"estado": "Finalizado"}).json()["total"] == 2
    assert cliente.get("/partidos", params={"fecha": "2030-06-13"}).json()["total"] == 6


def test_detalle_de_partido(cliente):
    resp = cliente.get("/partidos/P-03")
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["partido"]["id"] == "P-03"
    assert cuerpo["partido"]["estado"] == "Programado"
    assert cuerpo["partido"]["estadio"]["ciudad"]
    assert cuerpo["partido"]["fecha_hora"].startswith("2030-06-13T15:00:00")


def test_eliminatoria_sin_equipos_devuelve_nulos(cliente):
    partido = cliente.get("/partidos/P-128").json()["partido"]
    assert partido["fase"] == "Final" and partido["local"] is None and partido["visitante"] is None


def test_eventos_en_orden_y_limitados(cliente):
    todos = cliente.get("/partidos/P-01/eventos").json()
    assert todos["fuente"] == "neo4j"
    assert todos["eventos"][0]["tipo"] == "Inicio"
    assert cliente.get("/partidos/P-01/eventos", params={"limit": 3}).json()["eventos"] == todos["eventos"][:3]
    assert cliente.get("/partidos/P-03/eventos").json()["eventos"] == []


def test_cadena_de_un_gol_termina_en_el_gol(cliente):
    eventos = cliente.get("/partidos/P-01/eventos").json()["eventos"]
    gol = next(e for e in eventos if e["tipo"] == "Gol")
    cadena = cliente.get(f"/partidos/P-01/eventos/{gol['id']}/cadena").json()["cadena"]
    assert [e["tipo"] for e in cadena] == ["Pase", "Tiro", "Gol"]
    assert cadena[-1]["id"] == gol["id"]


@pytest.mark.parametrize("ruta", [
    "/partidos/P-999", "/partidos/P-999/eventos", "/partidos/P-01/eventos/EV-NO-EXISTE/cadena", "/equipos/XXX/camino",
])
def test_inexistente_responde_404_con_formato(cliente, ruta):
    resp = cliente.get(ruta)
    assert resp.status_code == 404
    assert resp.json()["error"]["codigo"] == "NO_ENCONTRADO"


@pytest.mark.parametrize("ruta,params", [
    ("/partidos/abc", None),
    ("/partidos/P-1", None),
    ("/partidos", {"estado": "Suspendido"}),
    ("/partidos", {"fase": "Repechaje"}),
    ("/partidos", {"fecha": "ayer"}),
    ("/partidos/P-01/eventos", {"limit": 0}),
    ("/partidos/P-01/eventos", {"limit": 101}),
    ("/equipos/argentina/camino", None),
    ("/estadisticas/participacion-en-goles", {"limit": 1000}),
])
def test_entrada_invalida_responde_422(cliente, ruta, params):
    resp = cliente.get(ruta, params=params)
    assert resp.status_code == 422
    assert resp.json()["error"]["codigo"] == "VALIDACION"


def test_neo4j_caido_responde_503(cliente, neo4j):
    neo4j.caida = True
    for ruta in ("/partidos", "/partidos/P-01", "/partidos/P-01/eventos", "/equipos/ARG/camino"):
        resp = cliente.get(ruta)
        assert resp.status_code == 503
        assert resp.json()["error"]["codigo"] == "DEPENDENCIA_NO_DISPONIBLE"


def test_camino_de_un_equipo(cliente):
    cuerpo = cliente.get("/equipos/ARG/camino").json()
    assert cuerpo["equipo"]["codigo"] == "ARG"
    assert len(cuerpo["partidos"]) == 3
