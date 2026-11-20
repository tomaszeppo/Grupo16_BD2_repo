from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from app.dominio.ids import id_usuario
from tests.apoyo import entrar

_SESIONES: dict[str, dict] = {}


def crear_usuario(cliente, nombre="Ana", pais="ARG") -> str:
    resp = cliente.post("/usuarios", json={"nombre": nombre, "pais": pais})
    assert resp.status_code == 201, resp.text
    usuario = resp.json()["usuario"]["id"]
    _SESIONES[usuario] = entrar(cliente, usuario)
    return usuario


def como(usuario_id):
    return _SESIONES[usuario_id]


def test_altas_simultaneas_reciben_ids_distintos(cliente, mongo):
    with ThreadPoolExecutor(max_workers=10) as pool:
        ids = list(pool.map(lambda n: crear_usuario(cliente, f"Usuario {n}"), range(20)))
    assert len(set(ids)) == 20
    assert sorted(ids) == [id_usuario(n) for n in range(1, 21)]
    assert mongo.db.usuarios.count_documents({}) == 20


def test_prode_con_99_integrantes_y_diez_uniendose_a_la_vez_no_pasa_de_100(cliente, mongo):
    dueno = crear_usuario(cliente)
    prode = cliente.post("/prodes", json={"nombre": "Oficina"}, headers=como(dueno)).json()["prode"]
    relleno = [id_usuario(n) for n in range(5000, 5098)]
    mongo.db.prodes.update_one({"_id": prode["id"]}, {"$push": {"integrantes": {"$each": relleno}}})
    assert len(mongo.db.prodes.find_one({"_id": prode["id"]})["integrantes"]) == 99
    aspirantes = [crear_usuario(cliente, f"Aspirante {n}") for n in range(10)]

    def unirse(usuario):
        return cliente.post("/prodes/unirse", json={"codigo": prode["codigo"]}, headers=como(usuario)).status_code

    with ThreadPoolExecutor(max_workers=10) as pool:
        codigos = list(pool.map(unirse, aspirantes))
    assert sorted(codigos) == [200] + [409] * 9
    assert len(mongo.db.prodes.find_one({"_id": prode["id"]})["integrantes"]) == 100


def test_unirse_y_listar_mis_prodes(cliente):
    dueno, otro = crear_usuario(cliente), crear_usuario(cliente, "Beto", "BRA")
    prode = cliente.post("/prodes", json={"nombre": "Oficina"}, headers=como(dueno)).json()["prode"]
    assert cliente.post("/prodes/unirse", json={"codigo": prode["codigo"]}, headers=como(otro)).json()["resultado"] == "unido"
    assert cliente.post("/prodes/unirse", json={"codigo": prode["codigo"]}, headers=como(otro)).json()["resultado"] == "ya_estaba"
    mios = cliente.get(f"/usuarios/{otro}/prodes", headers=como(otro)).json()["prodes"]
    assert [p["id"] for p in mios] == [prode["id"]] and mios[0]["integrantes"] == [dueno, otro]
    assert cliente.post("/prodes/unirse", json={"codigo": "FFFFFFFF"}, headers=como(otro)).status_code == 404


def test_veinte_put_simultaneos_del_mismo_pronostico_dejan_uno_solo(cliente, mongo):
    u = crear_usuario(cliente)

    def pronosticar(n):
        return cliente.put("/partidos/P-03/pronostico", json={"goles_local": n % 5, "goles_visitante": 1},
                           headers=como(u)).status_code

    with ThreadPoolExecutor(max_workers=20) as pool:
        codigos = list(pool.map(pronosticar, range(20)))
    assert all(c in (200, 201) for c in codigos), codigos
    assert codigos.count(201) == 1
    assert mongo.db.pronosticos.count_documents({"_id": f"{u}:P-03"}) == 1
    assert mongo.db.pronosticos.count_documents({}) == 1


def test_alta_correccion_y_listado(cliente, mongo, reloj):
    u = crear_usuario(cliente)
    alta = cliente.put("/partidos/P-03/pronostico", json={"goles_local": 2, "goles_visitante": 1}, headers=como(u))
    assert alta.status_code == 201
    reloj.instante = datetime(2030, 6, 13, 10, 0, tzinfo=timezone.utc)
    correccion = cliente.put("/partidos/P-03/pronostico", json={"goles_local": 0, "goles_visitante": 0}, headers=como(u))
    assert correccion.status_code == 200
    guardado = mongo.db.pronosticos.find_one({"_id": f"{u}:P-03"})
    assert (guardado["goles_local"], guardado["goles_visitante"]) == (0, 0)
    assert guardado["cargado_en"] == reloj.instante
    assert guardado["creado_en"] == datetime(2030, 6, 12, 15, 0, tzinfo=timezone.utc)
    assert guardado["usuario_id"] == u and guardado["partido_id"] == "P-03"

    cliente.put("/partidos/P-04/pronostico", json={"goles_local": 1, "goles_visitante": 1}, headers=como(u))
    lista = cliente.get(f"/usuarios/{u}/pronosticos", headers=como(u)).json()
    assert lista["total"] == 2 and [p["partido_id"] for p in lista["pronosticos"]] == ["P-03", "P-04"]


def test_ventana_de_pronostico_contra_el_fixture_real(cliente, reloj):
    u = crear_usuario(cliente)
    cuerpo = {"goles_local": 1, "goles_visitante": 0}
    assert cliente.put("/partidos/P-01/pronostico", json=cuerpo, headers=como(u)).status_code == 409  # finalizado
    assert cliente.put("/partidos/P-104/pronostico", json=cuerpo, headers=como(u)).status_code == 409  # sin equipos
    assert cliente.put("/partidos/P-999/pronostico", json=cuerpo, headers=como(u)).status_code == 404
    reloj.instante = datetime(2030, 6, 13, 15, 0, tzinfo=timezone.utc)
    assert cliente.put("/partidos/P-03/pronostico", json=cuerpo, headers=como(u)).status_code == 409  # ya es la hora
    assert cliente.put("/partidos/P-04/pronostico", json=cuerpo, headers=como(u)).status_code == 201  # empieza a las 18


def test_catalogo_de_equipos(cliente):
    assert len(cliente.get("/equipos").json()["equipos"]) == 48
    plantel = cliente.get("/equipos/ARG/jugadores").json()
    assert plantel["total"] == 26 and plantel["jugadores"][0]["dorsal"] == 1
    arqueros = cliente.get("/equipos/ARG/jugadores", params={"posicion": "Arquero"}).json()
    assert arqueros["total"] == 3
