"""Operación del partido (poner en juego, jugadas, equipos) y cierre con puntuación, con adaptadores falsos."""
from datetime import timedelta

import pytest

from tests.conftest import ADMIN


def crear_usuario(cliente, nombre="Ana") -> str:
    return cliente.post("/usuarios", json={"nombre": nombre, "pais": "ARG"}).json()["usuario"]["id"]


def pronosticar(cliente, usuario, partido, gl, gv):
    resp = cliente.put(f"/partidos/{partido}/pronostico", json={"goles_local": gl, "goles_visitante": gv},
                       headers={"X-Usuario-Id": usuario})
    assert resp.status_code in (200, 201), resp.text


def poner_en_juego(cliente, partido="P-03"):
    return cliente.post(f"/partidos/{partido}/estado", json={"estado": "En juego"}, headers=ADMIN)


def cerrar(cliente, partido="P-03", gl=2, gv=1, **extra):
    return cliente.post(f"/partidos/{partido}/resultado", json={"goles_local": gl, "goles_visitante": gv, **extra},
                        headers=ADMIN)


# --- clave de administración ---
@pytest.mark.parametrize("encabezados", [{}, {"X-Admin-Clave": "otra"}, {"X-Admin-Clave": ""}])
def test_sin_la_clave_de_administracion_responde_401(cliente, encabezados):
    for ruta, cuerpo in (("/partidos/P-03/estado", {"estado": "En juego"}),
                         ("/partidos/P-03/resultado", {"goles_local": 1, "goles_visitante": 0}),
                         ("/partidos/P-73/equipos", {"local": "ARG", "visitante": "BRA"}),
                         ("/partidos/P-03/eventos", {"id": "EV-1", "tipo": "Gol", "minuto": 3, "orden": 1})):
        resp = cliente.post(ruta, json=cuerpo, headers=encabezados)
        assert resp.status_code == 401, ruta
        assert resp.json()["error"]["codigo"] == "NO_AUTORIZADO"


def test_con_la_clave_sin_configurar_la_administracion_queda_deshabilitada(cliente, settings):
    settings.admin_clave = ""
    assert cliente.post("/partidos/P-03/estado", json={"estado": "En juego"}, headers={"X-Admin-Clave": ""}).status_code == 401


# --- poner en juego ---
def test_poner_en_juego_fija_el_inicio_real_una_sola_vez(cliente, reloj, neo4j):
    primera = poner_en_juego(cliente)
    assert primera.status_code == 200
    assert primera.json()["partido"]["estado"] == "En juego"
    inicio = primera.json()["partido"]["inicio_real"]
    reloj.instante += timedelta(minutes=10)
    segunda = poner_en_juego(cliente)
    assert segunda.status_code == 200 and segunda.json()["partido"]["inicio_real"] == inicio


def test_poner_en_juego_cierra_los_pronosticos_en_este_proceso(cliente):
    u = crear_usuario(cliente)
    pronosticar(cliente, u, "P-03", 1, 0)  # deja cargada la copia del calendario
    poner_en_juego(cliente)
    resp = cliente.put("/partidos/P-03/pronostico", json={"goles_local": 2, "goles_visitante": 0},
                       headers={"X-Usuario-Id": u})
    assert resp.status_code == 409


def test_no_se_pone_en_juego_lo_inexistente_lo_terminado_ni_lo_que_no_tiene_equipos(cliente):
    assert poner_en_juego(cliente, "P-999").status_code == 404
    assert poner_en_juego(cliente, "P-01").status_code == 409
    assert poner_en_juego(cliente, "P-104").status_code == 409
    assert cliente.post("/partidos/P-03/estado", json={"estado": "Finalizado"}, headers=ADMIN).status_code == 422


# --- equipos de eliminatorias ---
def test_asignar_equipos_habilita_el_pronostico(cliente):
    u = crear_usuario(cliente)
    resp = cliente.post("/partidos/P-73/equipos", json={"local": "ARG", "visitante": "BRA"}, headers=ADMIN)
    assert resp.status_code == 200
    assert resp.json()["partido"]["local"]["codigo"] == "ARG"
    pronosticar(cliente, u, "P-73", 1, 0)


@pytest.mark.parametrize("partido,cuerpo,codigo", [
    ("P-73", {"local": "ARG", "visitante": "ARG"}, 422),
    ("P-73", {"local": "ARG", "visitante": "XXX"}, 404),
    ("P-73", {"local": "arg", "visitante": "BRA"}, 422),
    ("P-03", {"local": "ARG", "visitante": "BRA"}, 409),  # fase de grupos
    ("P-999", {"local": "ARG", "visitante": "BRA"}, 404),
])
def test_asignar_equipos_invalido(cliente, partido, cuerpo, codigo):
    assert cliente.post(f"/partidos/{partido}/equipos", json=cuerpo, headers=ADMIN).status_code == codigo


# --- jugadas ---
def jugada(cliente, partido="P-03", **campos):
    cuerpo = {"id": "EV-P-03-0001", "tipo": "Pase", "minuto": 10, "orden": 1, **campos}
    return cliente.post(f"/partidos/{partido}/eventos", json=cuerpo, headers=ADMIN)


def test_cargar_jugadas_con_su_cadena(cliente, neo4j):
    poner_en_juego(cliente)
    local = neo4j.partidos["P-03"]["local"]["codigo"]
    j1, j2 = f"J-{local}-09", f"J-{local}-10"
    assert jugada(cliente, jugador=j1).status_code == 201
    assert jugada(cliente, id="EV-P-03-0002", tipo="Gol", orden=2, jugador=j2,
                  influido_por=["EV-P-03-0001"]).status_code == 201
    cadena = cliente.get("/partidos/P-03/eventos/EV-P-03-0002/cadena").json()["cadena"]
    assert [e["tipo"] for e in cadena] == ["Pase", "Gol"]


def test_repetir_la_misma_jugada_no_la_duplica(cliente, neo4j):
    poner_en_juego(cliente)
    assert jugada(cliente).status_code == 201
    assert jugada(cliente).status_code == 200
    assert len(neo4j.eventos["P-03"]) == 1
    distinto = jugada(cliente, minuto=55)
    assert distinto.status_code == 409


@pytest.mark.parametrize("campos", [
    {"tipo": "Córner"}, {"minuto": -1}, {"minuto": 131}, {"orden": -1}, {"id": "x"},
    {"influido_por": ["a"] * 11}, {"jugador": "Messi"},
])
def test_jugada_invalida_422(cliente, campos):
    poner_en_juego(cliente)
    assert jugada(cliente, **campos).status_code == 422


def test_jugada_en_conflicto_409(cliente, neo4j):
    assert jugada(cliente).status_code == 409  # el partido no está en juego
    poner_en_juego(cliente)
    assert jugada(cliente, jugador="J-NZL-01").status_code == 409  # no juega este partido
    assert jugada(cliente, influido_por=["EV-P-01-0001"]).status_code == 409  # jugada de otro partido
    assert jugada(cliente, "P-999").status_code == 404


def test_un_publicador_que_falla_no_rompe_la_carga_de_la_jugada(cliente, app):
    from app import deps

    class PublicadorRoto:
        def publicar(self, partido_id, evento):
            raise RuntimeError("InfluxDB no contesta")

    app.dependency_overrides[deps.get_publicador_eventos] = lambda: PublicadorRoto()
    poner_en_juego(cliente)
    assert jugada(cliente).status_code == 201


def test_la_jugada_se_avisa_al_publicador(cliente, app):
    from app import deps

    recibidas = []

    class Publicador:
        def publicar(self, partido_id, evento):
            recibidas.append((partido_id, evento["id"], evento["tipo"]))

    app.dependency_overrides[deps.get_publicador_eventos] = lambda: Publicador()
    poner_en_juego(cliente)
    jugada(cliente)
    jugada(cliente)  # repetida: no se vuelve a avisar
    assert recibidas == [("P-03", "EV-P-03-0001", "Pase")]


# --- cierre y puntuación ---
def test_cierre_puntua_y_arma_el_ranking(cliente, reloj):
    ana, beto, ciro = crear_usuario(cliente, "Ana"), crear_usuario(cliente, "Beto"), crear_usuario(cliente, "Ciro")
    pronosticar(cliente, ana, "P-03", 2, 1)   # exacto
    pronosticar(cliente, beto, "P-03", 1, 0)  # solo ganador
    pronosticar(cliente, ciro, "P-03", 0, 0)  # nada
    reloj.instante += timedelta(hours=23)
    poner_en_juego(cliente)
    resp = cerrar(cliente)
    assert resp.status_code == 202
    estado = cliente.get("/partidos/P-03/puntuacion", headers=ADMIN).json()
    assert estado["puntuacion"]["estado"] == "completa"
    assert estado["puntuacion"]["pronosticos"] == 3
    assert set(estado["puntuacion"]["pasos"]) == {"puntuar", "sumar", "foto"}
    assert cliente.get("/partidos/P-03").json()["partido"]["estado"] == "Finalizado"

    top = cliente.get("/ranking").json()
    assert top["fuente"] == "mongodb"
    assert [(f["puesto"], f["nombre"], f["puntos"], f["exactos"]) for f in top["ranking"]] == [
        (1, "Ana", 3, 1), (2, "Beto", 1, 0), (3, "Ciro", 0, 0)]
    assert top["ranking"][0]["tiempo_seg"] == 86400 and top["ranking"][1]["tiempo_seg"] == 43200


def test_repetir_el_cierre_no_suma_dos_veces(cliente, reloj):
    ana = crear_usuario(cliente)
    pronosticar(cliente, ana, "P-03", 2, 1)
    reloj.instante += timedelta(hours=1)
    poner_en_juego(cliente)
    assert cerrar(cliente).status_code == 202
    assert cerrar(cliente).status_code == 202
    assert cliente.get("/ranking").json()["ranking"][0]["puntos"] == 3


def test_cierre_con_otro_marcador_409(cliente):
    poner_en_juego(cliente)
    cerrar(cliente)
    resp = cerrar(cliente, gl=0, gv=0)
    assert resp.status_code == 409
    assert "2-1" in resp.json()["error"]["mensaje"]


def test_no_se_cierra_lo_que_no_esta_en_juego(cliente):
    assert cerrar(cliente).status_code == 409  # programado
    assert cerrar(cliente, "P-999").status_code == 404
    assert cliente.get("/partidos/P-03/puntuacion", headers=ADMIN).status_code == 404


def test_el_marcador_tiene_que_coincidir_con_los_goles_cargados(cliente, neo4j):
    poner_en_juego(cliente)
    local = neo4j.partidos["P-03"]["local"]["codigo"]
    jugada(cliente, tipo="Gol", jugador=f"J-{local}-09")
    assert cerrar(cliente, gl=2, gv=1).status_code == 409
    assert cerrar(cliente, gl=1, gv=0).status_code == 202


@pytest.mark.parametrize("cuerpo", [
    {"goles_local": -1, "goles_visitante": 0}, {"goles_local": 1}, {"goles_local": 31, "goles_visitante": 0},
    {"goles_local": 1, "goles_visitante": 0, "clasificado": "ARG"},  # en grupos no hay clasificado
])
def test_cuerpo_de_cierre_invalido_422(cliente, cuerpo):
    poner_en_juego(cliente)
    assert cliente.post("/partidos/P-03/resultado", json=cuerpo, headers=ADMIN).status_code == 422


def test_eliminatoria_empatada_exige_decir_quien_clasifica(cliente):
    cliente.post("/partidos/P-73/equipos", json={"local": "ARG", "visitante": "BRA"}, headers=ADMIN)
    poner_en_juego(cliente, "P-73")
    assert cerrar(cliente, "P-73", 1, 1).status_code == 422
    assert cerrar(cliente, "P-73", 1, 1, clasificado="URU").status_code == 422
    assert cerrar(cliente, "P-73", 2, 1, clasificado="BRA").status_code == 422  # ganó ARG
    assert cerrar(cliente, "P-73", 1, 1, clasificado="BRA").status_code == 202


def test_pronostico_tardio_se_anula(cliente, mongo, reloj):
    """Otro proceso, con la copia vieja del calendario, aceptó un pronóstico después del inicio real."""
    ana = crear_usuario(cliente)
    pronosticar(cliente, ana, "P-03", 0, 0)
    poner_en_juego(cliente)
    tardio = mongo.pronosticos[f"{ana}:P-03"]
    tardio.update(goles_local=2, goles_visitante=1, cargado_en=reloj.instante + timedelta(seconds=10))
    cerrar(cliente)
    assert mongo.pronosticos[f"{ana}:P-03"]["anulado"] is True
    assert cliente.get("/ranking").json()["ranking"][0]["puntos"] == 0


def test_dos_partidos_acumulan(cliente, reloj):
    ana = crear_usuario(cliente)
    pronosticar(cliente, ana, "P-03", 2, 1)
    pronosticar(cliente, ana, "P-04", 0, 0)
    reloj.instante += timedelta(hours=1)
    for partido, gl, gv in (("P-03", 2, 1), ("P-04", 1, 1)):
        poner_en_juego(cliente, partido)
        cerrar(cliente, partido, gl, gv)
    fila = cliente.get("/ranking").json()["ranking"][0]
    assert (fila["puntos"], fila["exactos"]) == (4, 1)


def test_acceso_valida_clave_antes_de_abrir_panel(cliente):
    assert cliente.get("/administracion/acceso").status_code == 401
    assert cliente.get("/administracion/acceso", headers={"X-Admin-Clave": "incorrecta"}).status_code == 401
    respuesta = cliente.get("/administracion/acceso", headers=ADMIN)
    assert respuesta.status_code == 200
    assert respuesta.json() == {"autorizado": True}
