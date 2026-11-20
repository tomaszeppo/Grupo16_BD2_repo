"""Usuarios, sesiones, prodes y pronósticos con adaptadores falsos."""
from datetime import timedelta

import pytest

from tests.apoyo import entrar

_SESIONES: dict[str, dict] = {}  # usuario → encabezado de su sesión; se pisa en cada prueba al crear el usuario


def crear_usuario(cliente, nombre="Ana", pais="ARG") -> str:
    resp = cliente.post("/usuarios", json={"nombre": nombre, "pais": pais})
    assert resp.status_code == 201, resp.text
    usuario = resp.json()["usuario"]["id"]
    _SESIONES[usuario] = entrar(cliente, usuario)
    return usuario


def como(usuario_id: str) -> dict:
    return _SESIONES[usuario_id]


# --- usuarios y sesiones ---
def test_alta_de_usuario_con_ids_correlativos(cliente):
    assert crear_usuario(cliente) == "U0000001"
    assert crear_usuario(cliente, "Beto", "BRA") == "U0000002"
    cuerpo = cliente.get("/usuarios/U0000002").json()
    assert cuerpo["fuente"] == "mongodb"
    assert cuerpo["usuario"]["nombre"] == "Beto" and cuerpo["usuario"]["pais"] == "BRA"


@pytest.mark.parametrize("cuerpo", [
    {"nombre": "", "pais": "ARG"}, {"nombre": "   ", "pais": "ARG"}, {"nombre": "x" * 61, "pais": "ARG"},
    {"nombre": "Ana", "pais": "arg"}, {"nombre": "Ana", "pais": "ARGENTINA"}, {"nombre": "Ana"}, {},
])
def test_alta_de_usuario_invalida(cliente, cuerpo):
    assert cliente.post("/usuarios", json=cuerpo).status_code == 422


def test_usuario_inexistente_404(cliente):
    assert cliente.get("/usuarios/U0000099").status_code == 404
    assert cliente.get("/usuarios/juan").status_code == 422


@pytest.mark.parametrize("encabezados", [{}, {"X-Sesion": "inexistente"}, {"X-Usuario-Id": "U0000001"}])
def test_sin_usuario_valido_responde_401(cliente, encabezados):
    resp = cliente.put("/partidos/P-03/pronostico", json={"goles_local": 1, "goles_visitante": 0}, headers=encabezados)
    assert resp.status_code == 401
    assert resp.json()["error"]["codigo"] == "NO_AUTORIZADO"
    assert cliente.post("/prodes", json={"nombre": "Oficina"}, headers=encabezados).status_code == 401


# --- prodes ---
def test_crear_prode_deja_al_dueno_como_integrante(cliente):
    u = crear_usuario(cliente)
    resp = cliente.post("/prodes", json={"nombre": "Oficina"}, headers=como(u))
    assert resp.status_code == 201
    prode = resp.json()["prode"]
    assert prode["id"].startswith("PR-") and len(prode["codigo"]) == 8
    assert prode["dueno"] == u and prode["integrantes"] == [u]
    assert [p["id"] for p in cliente.get(f"/usuarios/{u}/prodes", headers=como(u)).json()["prodes"]] == [prode["id"]]


def test_unirse_dos_veces_no_duplica(cliente):
    dueno, otro = crear_usuario(cliente), crear_usuario(cliente, "Beto")
    codigo = cliente.post("/prodes", json={"nombre": "Oficina"}, headers=como(dueno)).json()["prode"]["codigo"]
    primera = cliente.post("/prodes/unirse", json={"codigo": codigo}, headers=como(otro))
    segunda = cliente.post("/prodes/unirse", json={"codigo": codigo}, headers=como(otro))
    assert primera.status_code == 200 and primera.json()["resultado"] == "unido"
    assert segunda.status_code == 200 and segunda.json()["resultado"] == "ya_estaba"
    assert segunda.json()["prode"]["integrantes"] == [dueno, otro]


def test_prode_lleno_responde_409(cliente, mongo):
    dueno = crear_usuario(cliente)
    prode = cliente.post("/prodes", json={"nombre": "Oficina"}, headers=como(dueno)).json()["prode"]
    mongo.prodes[prode["id"]]["integrantes"] += [f"U{n:07d}" for n in range(1000, 1099)]  # 100 en total
    nuevo = crear_usuario(cliente, "Ciro")
    resp = cliente.post("/prodes/unirse", json={"codigo": prode["codigo"]}, headers=como(nuevo))
    assert resp.status_code == 409
    assert "100" in resp.json()["error"]["mensaje"]


def test_codigo_inexistente_404_y_malformado_422(cliente):
    u = crear_usuario(cliente)
    assert cliente.post("/prodes/unirse", json={"codigo": "FFFFFFFF"}, headers=como(u)).status_code == 404
    assert cliente.post("/prodes/unirse", json={"codigo": "corto"}, headers=como(u)).status_code == 422
    assert cliente.post("/prodes", json={"nombre": ""}, headers=como(u)).status_code == 422


def test_los_prodes_de_otro_usuario_no_se_pueden_ver(cliente):
    a, b = crear_usuario(cliente), crear_usuario(cliente, "Beto")
    resp = cliente.get(f"/usuarios/{a}/prodes", headers=como(b))
    assert resp.status_code == 403
    assert resp.json()["error"]["codigo"] == "PROHIBIDO"


# --- equipos ---
def test_equipos_y_plantel(cliente, mongo):
    mongo.equipos["ARG"] = {"_id": "ARG", "nombre": "Argentina", "grupo": "A"}
    mongo.jugadores["J-ARG-01"] = {"_id": "J-ARG-01", "nombre": "Lucas", "apellido": "Sosa", "dorsal": 1,
                                   "posicion": "Arquero", "equipo": "ARG"}
    assert cliente.get("/equipos").json()["equipos"] == [{"codigo": "ARG", "nombre": "Argentina", "grupo": "A"}]
    cuerpo = cliente.get("/equipos/ARG/jugadores").json()
    assert cuerpo["fuente"] == "mongodb" and cuerpo["total"] == 1 and cuerpo["jugadores"][0]["id"] == "J-ARG-01"
    assert cliente.get("/equipos/ARG/jugadores", params={"posicion": "Delantero"}).json()["total"] == 0
    assert cliente.get("/equipos/XXX/jugadores").status_code == 404
    assert cliente.get("/equipos/ARG/jugadores", params={"limit": 500}).status_code == 422
    assert cliente.get("/equipos/ARG/jugadores", params={"posicion": "Líbero"}).status_code == 422


# --- pronósticos ---
def pronosticar(cliente, usuario, partido="P-03", gl=2, gv=1):
    return cliente.put(f"/partidos/{partido}/pronostico", json={"goles_local": gl, "goles_visitante": gv},
                       headers=como(usuario))


def test_alta_201_y_correccion_200_con_la_hora_de_la_ultima_carga(cliente, reloj):
    u = crear_usuario(cliente)
    alta = pronosticar(cliente, u)
    assert alta.status_code == 201
    assert alta.json()["fuente"] == "mongodb"
    assert alta.json()["pronostico"]["id"] == f"{u}:P-03"
    primera_hora = alta.json()["pronostico"]["cargado_en"]

    reloj.instante += timedelta(hours=2)
    correccion = pronosticar(cliente, u, gl=0, gv=0)
    assert correccion.status_code == 200
    p = correccion.json()["pronostico"]
    assert (p["goles_local"], p["goles_visitante"]) == (0, 0)
    assert p["cargado_en"] > primera_hora
    assert p["creado_en"] == alta.json()["pronostico"]["creado_en"]

    lista = cliente.get(f"/usuarios/{u}/pronosticos", headers=como(u)).json()
    assert lista["total"] == 1 and lista["pronosticos"][0]["goles_local"] == 0


@pytest.mark.parametrize("cuerpo", [
    {"goles_local": -1, "goles_visitante": 0}, {"goles_local": 21, "goles_visitante": 0},
    {"goles_local": 1.5, "goles_visitante": 0}, {"goles_local": "2", "goles_visitante": 0},
    {"goles_local": 1}, {"goles_local": None, "goles_visitante": 1}, {},
])
def test_goles_fuera_de_rango_o_no_enteros_422(cliente, cuerpo):
    u = crear_usuario(cliente)
    resp = cliente.put("/partidos/P-03/pronostico", json=cuerpo, headers=como(u))
    assert resp.status_code == 422
    assert resp.json()["error"]["codigo"] == "VALIDACION"


def test_partido_inexistente_404_e_id_invalido_422(cliente):
    u = crear_usuario(cliente)
    assert pronosticar(cliente, u, "P-999").status_code == 404
    assert pronosticar(cliente, u, "abc").status_code == 422


def test_no_se_pronostica_un_partido_que_no_esta_programado(cliente, neo4j):
    u = crear_usuario(cliente)
    neo4j.partidos["P-03"]["estado"] = "En juego"
    resp = pronosticar(cliente, u)
    assert resp.status_code == 409
    assert "empezó" in resp.json()["error"]["mensaje"]
    finalizado = pronosticar(cliente, u, "P-01")
    assert finalizado.status_code == 409


def test_no_se_pronostica_a_la_hora_de_inicio_ni_despues(cliente, reloj):
    u = crear_usuario(cliente)
    reloj.instante = reloj.instante.replace(day=13, hour=14, minute=59, second=59)
    assert pronosticar(cliente, u).status_code == 201
    reloj.instante = reloj.instante.replace(hour=15, minute=0, second=0)  # hora exacta de P-03
    resp = pronosticar(cliente, u)
    assert resp.status_code == 409
    assert "horario" in resp.json()["error"]["mensaje"]


def test_eliminatoria_sin_equipos_definidos_409(cliente):
    u = crear_usuario(cliente)
    resp = pronosticar(cliente, u, "P-104")
    assert resp.status_code == 409
    assert "equipos" in resp.json()["error"]["mensaje"]


def test_neo4j_caido_sin_copia_del_calendario_responde_503(cliente, neo4j):
    u = crear_usuario(cliente)
    neo4j.caida = True
    resp = pronosticar(cliente, u)
    assert resp.status_code == 503
    assert resp.json()["error"]["codigo"] == "DEPENDENCIA_NO_DISPONIBLE"
    assert set(resp.json()["error"]) >= {"codigo", "mensaje", "request_id"}


def test_neo4j_caido_con_copia_del_calendario_se_sigue_pronosticando(cliente, neo4j, reloj):
    u = crear_usuario(cliente)
    assert pronosticar(cliente, u).status_code == 201  # deja la copia cargada
    neo4j.caida = True
    reloj.instante += timedelta(minutes=5)
    assert pronosticar(cliente, u, "P-04").status_code == 201
    assert cliente.get("/health/dependencias").json()["calendario"]["desactualizado"] is True


def test_mongodb_caido_responde_503(cliente, mongo):
    u = crear_usuario(cliente)
    mongo.caida = True
    assert pronosticar(cliente, u).status_code == 503


def test_los_pronosticos_de_otro_usuario_no_se_pueden_ver(cliente):
    a, b = crear_usuario(cliente), crear_usuario(cliente, "Beto")
    assert cliente.get(f"/usuarios/{a}/pronosticos", headers=como(b)).status_code == 403
