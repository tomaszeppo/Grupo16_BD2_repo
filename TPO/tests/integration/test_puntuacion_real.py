"""Cierre de partido, puntuación y ranking contra MongoDB y Neo4j reales."""
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from app.dominio.ids import id_pronostico, id_usuario
from app.dominio.puntuacion import calcular
from scripts.recalcular_puntajes import diferencias
from tests.integration.conftest import ADMIN

P03 = datetime(2030, 6, 13, 15, 0, tzinfo=timezone.utc)  # horario programado de P-03
P04 = P03 + timedelta(hours=3)


def sembrar(mongo, partido, programado, inicio_real, cantidad=300, semilla=1):
    """Usuarios y pronósticos directo en MongoDB: exactos, solo ganador, fallos, cargas viejas y tardías."""
    rng = random.Random(semilla)
    usuarios = [id_usuario(n) for n in range(1, cantidad + 1)]
    mongo.db.usuarios.delete_many({})
    mongo.db.usuarios.insert_many([{"_id": u, "nombre": f"Usuario {n}", "pais": "ARG", "creado_en": programado}
                                   for n, u in enumerate(usuarios, start=1)])
    docs = []
    for n, u in enumerate(usuarios):
        if n % 10 == 0:  # cargado cuando el partido ya había empezado
            cargado = inicio_real + timedelta(seconds=rng.randint(0, 600))
        elif n % 10 == 1:  # con más de cinco días de anticipación
            cargado = programado - timedelta(days=rng.randint(6, 20), seconds=rng.randint(0, 86399))
        elif n % 10 == 2:  # entre el inicio real y el programado no hay nada: justo antes del inicio real
            cargado = inicio_real - timedelta(milliseconds=rng.randint(1, 999))
        else:
            cargado = programado - timedelta(seconds=rng.randint(1, 400000), milliseconds=rng.randint(0, 999))
        docs.append({"_id": id_pronostico(u, partido), "usuario_id": u, "partido_id": partido,
                     "goles_local": rng.randint(0, 3), "goles_visitante": rng.randint(0, 3),
                     "cargado_en": cargado, "creado_en": cargado})
    mongo.db.pronosticos.insert_many(docs)
    return usuarios


def jugar(cliente, reloj, partido, inicio_real):
    reloj.instante = inicio_real
    assert cliente.post(f"/partidos/{partido}/estado", json={"estado": "En juego"}, headers=ADMIN).status_code == 200
    reloj.instante = inicio_real + timedelta(hours=2)


def cerrar(cliente, partido, gl, gv):
    return cliente.post(f"/partidos/{partido}/resultado", json={"goles_local": gl, "goles_visitante": gv}, headers=ADMIN)


def puntajes(mongo):
    return {f["_id"]: (f["puntos"], f["exactos"], f["tiempo_seg"]) for f in mongo.db.puntajes.find()}


def test_la_puntuacion_en_mongodb_coincide_con_las_reglas_documento_por_documento(cliente, mongo, reloj):
    inicio_real = P03 - timedelta(minutes=7)  # lo pusieron en juego unos minutos antes
    usuarios = sembrar(mongo, "P-03", P03, inicio_real)
    jugar(cliente, reloj, "P-03", inicio_real)
    assert cerrar(cliente, "P-03", 2, 1).status_code == 202

    estado = cliente.get("/partidos/P-03/puntuacion", headers=ADMIN).json()["puntuacion"]
    assert estado["estado"] == "completa" and estado["pronosticos"] == 300
    assert set(estado["pasos"]) == {"puntuar", "sumar", "foto"}

    vistos = {"exacto": 0, "ganador": 0, "nada": 0, "anulado": 0}
    for doc in mongo.db.pronosticos.find({"partido_id": "P-03"}):
        esperado = calcular(doc["goles_local"], doc["goles_visitante"], 2, 1, doc["cargado_en"], P03, inicio_real)
        obtenido = (doc["puntos"], doc["exacto"], doc["tiempo_seg"], doc["anulado"])
        assert obtenido == (esperado.puntos, esperado.exacto, esperado.tiempo_seg, esperado.anulado), doc["_id"]
        assert isinstance(doc["tiempo_seg"], int) and "_exacto" not in doc and "_anticipacion" not in doc
        vistos["anulado" if esperado.anulado else "exacto" if esperado.exacto
               else "ganador" if esperado.puntos == 1 else "nada"] += 1
    assert all(v > 0 for v in vistos.values()), vistos  # la muestra cubre los cuatro casos

    guardados = puntajes(mongo)
    assert set(guardados) == set(usuarios)
    for doc in mongo.db.pronosticos.find({"partido_id": "P-03"}):
        assert guardados[doc["usuario_id"]] == (doc["puntos"], 1 if doc["exacto"] else 0, doc["tiempo_seg"])
    assert diferencias(mongo.db) == []


def test_repetir_el_cierre_o_la_suma_no_cambia_ningun_puntaje(cliente, mongo, reloj):
    sembrar(mongo, "P-03", P03, P03)
    jugar(cliente, reloj, "P-03", P03)
    cerrar(cliente, "P-03", 1, 1)
    antes = puntajes(mongo)
    assert sum(p for p, _, _ in antes.values()) > 0
    assert cerrar(cliente, "P-03", 1, 1).status_code == 202
    for _ in range(3):
        mongo.sumar_a_puntajes("P-03")
    mongo.puntuar_pronosticos("P-03", mongo.obtener_resultado("P-03"))
    assert puntajes(mongo) == antes
    assert cerrar(cliente, "P-03", 2, 2).status_code == 409


def test_ocho_cierres_simultaneos_puntuan_una_sola_vez(cliente, mongo, reloj):
    sembrar(mongo, "P-03", P03, P03)
    jugar(cliente, reloj, "P-03", P03)
    with ThreadPoolExecutor(max_workers=8) as pool:
        codigos = list(pool.map(lambda _: cerrar(cliente, "P-03", 2, 1).status_code, range(8)))
    assert codigos == [202] * 8
    resultado = mongo.db.resultados.find_one({"_id": "P-03"})
    assert resultado["puntuacion"]["estado"] == "completa"
    assert all(f["aplicados"] == ["P-03"] for f in mongo.db.puntajes.find())
    assert diferencias(mongo.db) == []


def test_una_puntuacion_que_quedo_a_medias_se_retoma_con_el_mismo_pedido(cliente, mongo, reloj):
    sembrar(mongo, "P-03", P03, P03)
    jugar(cliente, reloj, "P-03", P03)
    # Simula un proceso que se cayó después de puntuar y antes de sumar: toma vieja y un solo paso hecho.
    hace_rato = reloj.instante - timedelta(minutes=10)
    resultado = mongo.registrar_resultado("P-03", 2, 1, None, P03, P03, hace_rato)
    mongo.puntuar_pronosticos("P-03", resultado)
    mongo.db.resultados.update_one({"_id": "P-03"}, {"$set": {
        "puntuacion.estado": "en_curso", "puntuacion.tomada_en": hace_rato, "puntuacion.iniciada_en": hace_rato,
        "puntuacion.pasos": {"puntuar": 12.5}, "puntuacion.pronosticos": 300}})
    assert mongo.db.puntajes.count_documents({}) == 0

    assert cerrar(cliente, "P-03", 2, 1).status_code == 202
    estado = mongo.db.resultados.find_one({"_id": "P-03"})["puntuacion"]
    assert estado["estado"] == "completa"
    assert estado["pasos"]["puntuar"] == 12.5  # no se repitió el paso ya hecho
    assert {"sumar", "foto"} <= set(estado["pasos"])
    assert mongo.db.puntajes.count_documents({}) == 300
    assert diferencias(mongo.db) == []


def test_una_toma_reciente_de_otro_proceso_no_se_pisa(cliente, mongo, reloj):
    sembrar(mongo, "P-03", P03, P03, cantidad=20)
    jugar(cliente, reloj, "P-03", P03)
    mongo.registrar_resultado("P-03", 2, 1, None, P03, P03, reloj.instante)
    mongo.db.resultados.update_one({"_id": "P-03"}, {"$set": {
        "puntuacion.estado": "en_curso", "puntuacion.tomada_en": reloj.instante - timedelta(seconds=5)}})
    assert cerrar(cliente, "P-03", 2, 1).status_code == 202
    assert mongo.db.resultados.find_one({"_id": "P-03"})["puntuacion"]["estado"] == "en_curso"
    assert mongo.db.puntajes.count_documents({}) == 0


def test_dos_partidos_acumulan_y_el_recalculo_completo_coincide(cliente, mongo, reloj):
    usuarios = sembrar(mongo, "P-03", P03, P03, cantidad=120)
    rng = random.Random(2)
    mongo.db.pronosticos.insert_many([
        {"_id": id_pronostico(u, "P-04"), "usuario_id": u, "partido_id": "P-04", "goles_local": rng.randint(0, 2),
         "goles_visitante": rng.randint(0, 2), "cargado_en": P03 - timedelta(hours=rng.randint(1, 200)),
         "creado_en": P03 - timedelta(days=30)} for u in usuarios[:80]])
    jugar(cliente, reloj, "P-03", P03)
    cerrar(cliente, "P-03", 2, 1)
    jugar(cliente, reloj, "P-04", P04)
    cerrar(cliente, "P-04", 1, 1)

    assert mongo.db.puntajes.count_documents({"aplicados": ["P-03", "P-04"]}) == 80
    assert mongo.db.puntajes.count_documents({"aplicados": ["P-03"]}) == 40
    assert diferencias(mongo.db) == []
    fotos = {f["_id"]: f for f in mongo.db.rankings_historicos.find()}
    assert set(fotos) == {"P-03", "P-04"}
    assert fotos["P-04"]["total_usuarios"] == 120 and len(fotos["P-04"]["primeros"]) == 100


def test_el_marcador_debe_coincidir_con_los_goles_cargados_en_neo4j(cliente, cargado, reloj):
    jugar(cliente, reloj, "P-03", P03)
    local = next(p for p in cargado.partidos if p["id"] == "P-03")["local"]
    gol = {"id": "EV-P-03-0001", "tipo": "Gol", "minuto": 12, "orden": 1, "jugador": f"J-{local}-09"}
    assert cliente.post("/partidos/P-03/eventos", json=gol, headers=ADMIN).status_code == 201
    assert cerrar(cliente, "P-03", 2, 1).status_code == 409
    assert cerrar(cliente, "P-03", 1, 0).status_code == 202
    partido = cliente.get("/partidos/P-03").json()["partido"]
    assert (partido["estado"], partido["goles_local"], partido["goles_visitante"]) == ("Finalizado", 1, 0)


# --- ranking ---
def test_orden_del_ranking_con_empates_y_puesto_de_cada_usuario(cliente, mongo):
    filas = [  # (usuario, puntos, exactos, tiempo)
        ("U0000005", 9, 3, 100), ("U0000002", 9, 2, 900), ("U0000004", 9, 2, 500), ("U0000001", 9, 2, 500),
        ("U0000003", 7, 2, 999), ("U0000006", 0, 0, 0),
    ]
    mongo.db.puntajes.insert_many([{"_id": u, "puntos": p, "exactos": e, "tiempo_seg": t, "aplicados": ["P-03"]}
                                   for u, p, e, t in filas])
    mongo.db.usuarios.insert_many([{"_id": u, "nombre": f"N{u[-1]}", "pais": "ARG", "creado_en": P03}
                                   for u, *_ in filas])
    esperado = ["U0000005", "U0000002", "U0000001", "U0000004", "U0000003", "U0000006"]

    top = cliente.get("/ranking", params={"limit": 100}).json()
    assert top["fuente"] == "mongodb"
    assert [f["usuario_id"] for f in top["ranking"]] == esperado
    assert [f["puesto"] for f in top["ranking"]] == [1, 2, 3, 4, 5, 6]
    assert top["ranking"][0]["nombre"] == "N5"
    assert cliente.get("/ranking", params={"limit": 100}).json() == top  # orden estable entre pedidos
    assert [f["usuario_id"] for f in cliente.get("/ranking", params={"limit": 2}).json()["ranking"]] == esperado[:2]

    for puesto, usuario in enumerate(esperado, start=1):
        cuerpo = cliente.get(f"/ranking/usuarios/{usuario}").json()
        assert cuerpo["puesto"] == puesto and cuerpo["total_usuarios"] == 6
    assert cliente.get("/ranking/usuarios/U0000099").status_code == 404
    assert cliente.get("/ranking/historico/P-50").status_code == 404


def test_el_top_usa_el_indice_del_ranking(mongo, cargado):
    plan = mongo.db.puntajes.find().sort([("puntos", -1), ("exactos", -1), ("tiempo_seg", -1), ("_id", 1)]).limit(20).explain()
    texto = str(plan["queryPlanner"]["winningPlan"])
    assert "IXSCAN" in texto and "SORT'" not in texto and "'stage': 'SORT'" not in texto


def test_tabla_de_un_prode_privado(cliente, mongo):
    ids = [cliente.post("/usuarios", json={"nombre": n, "pais": "ARG"}).json()["usuario"]["id"]
           for n in ("Ana", "Beto", "Ciro", "Dora")]
    ana, beto, ciro, dora = ids
    prode = cliente.post("/prodes", json={"nombre": "Oficina"}, headers={"X-Usuario-Id": ana}).json()["prode"]
    for u in (beto, ciro):
        cliente.post("/prodes/unirse", json={"codigo": prode["codigo"]}, headers={"X-Usuario-Id": u})
    mongo.db.puntajes.insert_many([
        {"_id": ana, "puntos": 4, "exactos": 1, "tiempo_seg": 10, "aplicados": ["P-03"]},
        {"_id": beto, "puntos": 6, "exactos": 2, "tiempo_seg": 10, "aplicados": ["P-03"]},
        {"_id": dora, "puntos": 9, "exactos": 3, "tiempo_seg": 10, "aplicados": ["P-03"]},  # no está en el prode
    ])
    tabla = cliente.get(f"/prodes/{prode['id']}/tabla", headers={"X-Usuario-Id": ciro}).json()
    assert [(f["puesto"], f["nombre"], f["puntos"]) for f in tabla["tabla"]] == [(1, "Beto", 6), (2, "Ana", 4), (3, "Ciro", 0)]
    assert cliente.get(f"/prodes/{prode['id']}/tabla", headers={"X-Usuario-Id": dora}).status_code == 403
    assert cliente.get("/prodes/PR-00000000/tabla", headers={"X-Usuario-Id": ana}).status_code == 404


# --- operación del partido en Neo4j ---
def test_poner_en_juego_dos_veces_no_mueve_el_inicio_real(cliente, neo4j, reloj):
    reloj.instante = P03 - timedelta(minutes=3)
    primera = cliente.post("/partidos/P-03/estado", json={"estado": "En juego"}, headers=ADMIN).json()["partido"]
    reloj.instante = P03 + timedelta(minutes=30)
    segunda = cliente.post("/partidos/P-03/estado", json={"estado": "En juego"}, headers=ADMIN).json()["partido"]
    assert primera["estado"] == segunda["estado"] == "En juego"
    assert primera["inicio_real"] == segunda["inicio_real"]
    assert primera["inicio_real"].startswith("2030-06-13T14:57:00")
    assert cliente.post("/partidos/P-104/estado", json={"estado": "En juego"}, headers=ADMIN).status_code == 409


def test_jugadas_sin_duplicar_y_con_cadena(cliente, neo4j, cargado, reloj):
    jugar(cliente, reloj, "P-03", P03)
    local = next(p for p in cargado.partidos if p["id"] == "P-03")["local"]
    pase = {"id": "EV-P-03-0001", "tipo": "Pase", "minuto": 10, "orden": 1, "jugador": f"J-{local}-08"}
    gol = {"id": "EV-P-03-0002", "tipo": "Gol", "minuto": 10, "orden": 2, "jugador": f"J-{local}-09",
           "influido_por": ["EV-P-03-0001"]}
    assert cliente.post("/partidos/P-03/eventos", json=pase, headers=ADMIN).status_code == 201
    assert cliente.post("/partidos/P-03/eventos", json=gol, headers=ADMIN).status_code == 201
    assert cliente.post("/partidos/P-03/eventos", json=gol, headers=ADMIN).status_code == 200
    assert neo4j._leer("MATCH (e:Evento)-[:OCURRE_EN]->(:Partido {id: 'P-03'}) RETURN count(e) AS n")[0]["n"] == 2
    cadena = cliente.get("/partidos/P-03/eventos/EV-P-03-0002/cadena").json()["cadena"]
    assert [e["tipo"] for e in cadena] == ["Pase", "Gol"]

    assert cliente.post("/partidos/P-03/eventos", json={**gol, "minuto": 80}, headers=ADMIN).status_code == 409
    de_otro_partido = {**pase, "id": "EV-P-03-0003", "influido_por": [cargado.eventos["P-01"][1]["id"]]}
    assert cliente.post("/partidos/P-03/eventos", json=de_otro_partido, headers=ADMIN).status_code == 409
    ajeno = {**pase, "id": "EV-P-03-0004", "jugador": "J-NZL-01"}
    assert cliente.post("/partidos/P-03/eventos", json=ajeno, headers=ADMIN).status_code == 409
    assert cliente.post("/partidos/P-04/eventos", json={**pase, "id": "EV-P-04-0001"}, headers=ADMIN).status_code == 409


def test_asignar_equipos_a_una_eliminatoria_la_vuelve_pronosticable(cliente, reloj):
    u = cliente.post("/usuarios", json={"nombre": "Ana", "pais": "ARG"}).json()["usuario"]["id"]
    cuerpo = {"goles_local": 1, "goles_visitante": 0}
    assert cliente.put("/partidos/P-73/pronostico", json=cuerpo, headers={"X-Usuario-Id": u}).status_code == 409
    asignado = cliente.post("/partidos/P-73/equipos", json={"local": "ARG", "visitante": "BRA"}, headers=ADMIN)
    assert asignado.status_code == 200 and asignado.json()["partido"]["visitante"]["codigo"] == "BRA"
    cliente.post("/partidos/P-73/equipos", json={"local": "URU", "visitante": "BRA"}, headers=ADMIN)  # corrección
    partido = cliente.get("/partidos/P-73").json()["partido"]
    assert (partido["local"]["codigo"], partido["visitante"]["codigo"]) == ("URU", "BRA")
    assert cliente.put("/partidos/P-73/pronostico", json=cuerpo, headers={"X-Usuario-Id": u}).status_code == 201
    assert cliente.post("/partidos/P-73/equipos", json={"local": "ARG", "visitante": "XXX"}, headers=ADMIN).status_code == 404
    assert cliente.post("/partidos/P-03/equipos", json={"local": "ARG", "visitante": "BRA"}, headers=ADMIN).status_code == 409
