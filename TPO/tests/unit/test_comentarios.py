"""Comentarios: repetidos, modo lento, guardado en la región del usuario, reparto e historial."""
import json
import uuid
from datetime import timedelta

from tests.apoyo import entrar
from tests.conftest import ADMIN


def _preparar(cliente, pais="ARG", nombre="Ana", en_juego=True):
    usuario = cliente.post("/usuarios", json={"nombre": nombre, "pais": pais}).json()["usuario"]["id"]
    if en_juego:
        cliente.post("/partidos/P-03/estado", json={"estado": "En juego"}, headers=ADMIN)
    return entrar(cliente, usuario)


def _comentar(cliente, como, texto="Vamos!", comentario_id=None):
    cuerpo = {"comentario_id": str(comentario_id or uuid.uuid4()), "contenido": texto}
    return cliente.post("/partidos/P-03/comentarios", json=cuerpo, headers=como)


def test_publicar_guarda_publica_y_cuenta(cliente, redis, cassandra):
    resp = _comentar(cliente, _preparar(cliente), "  Vamos!  ")
    assert resp.status_code == 201, resp.text
    cuerpo = resp.json()
    assert cuerpo["fuente"] == "cassandra" and cuerpo["region_atendida"] == "america"
    assert cuerpo["pais"] == "ARG" and cuerpo["contenido"] == "Vamos!" and cuerpo["origen"] == "usuario"
    fila = next(iter(cassandra.filas.values()))
    assert fila["origen"] == "usuario" and fila["usuario_nombre"] == "Ana"
    canales = [canal for canal, _ in redis.publicados]
    assert canales == ["chat:P-03:ARG", "chat:P-03:todos"]
    mensaje = json.loads(redis.publicados[0][1])
    assert mensaje["tipo"] == "comentario" and mensaje["contenido"] == "Vamos!" and "enviado_en" in mensaje
    assert redis.leer("cuenta:P-03:ARG:usuario") == "1"
    assert "ARG" in redis.miembros("paises:P-03")


def test_un_espanol_escribe_en_europa(cliente, cassandra):
    assert _comentar(cliente, _preparar(cliente, "ESP", "Lola")).json()["region_atendida"] == "europa"


def test_si_cae_su_region_lo_atiende_la_otra(cliente, cassandra):
    cassandra.caidas = {"europa"}
    assert _comentar(cliente, _preparar(cliente, "ESP", "Lola")).json()["region_atendida"] == "america"


def test_reintento_con_el_mismo_id_no_duplica(cliente, redis, cassandra):
    como = _preparar(cliente)
    comentario_id = uuid.uuid4()
    primero = _comentar(cliente, como, comentario_id=comentario_id)
    segundo = _comentar(cliente, como, comentario_id=comentario_id)
    assert primero.status_code == 201 and segundo.status_code == 200
    assert segundo.json()["comentario_id"] == primero.json()["comentario_id"]
    assert len(cassandra.filas) == 1
    assert len(redis.publicados) == 2  # un solo comentario, en sus dos canales


def test_modo_lento(cliente):
    como = _preparar(cliente)
    assert _comentar(cliente, como).status_code == 201
    resp = _comentar(cliente, como)
    assert resp.status_code == 429
    assert resp.json()["error"]["codigo"] == "DEMASIADOS_PEDIDOS"


def test_reintento_despues_del_modo_lento(cliente, redis):
    ahora = [1000.0]
    redis.reloj = lambda: ahora[0]
    como = _preparar(cliente)
    assert _comentar(cliente, como, "uno").status_code == 201
    segundo = uuid.uuid4()
    assert _comentar(cliente, como, "dos", segundo).status_code == 429
    ahora[0] += 5.1
    assert _comentar(cliente, como, "dos", segundo).status_code == 201


def test_solo_en_juego(cliente):
    assert _comentar(cliente, _preparar(cliente, en_juego=False)).status_code == 409


def test_falla_cassandra_libera_el_id(cliente, redis, cassandra):
    como = _preparar(cliente)
    cassandra.caidas = {"europa", "america"}
    comentario_id = uuid.uuid4()
    assert _comentar(cliente, como, comentario_id=comentario_id).status_code == 503
    assert redis.leer(f"visto:{comentario_id}") is None
    assert redis.leer("lento:U0000001") is None


def test_cuerpo_invalido(cliente):
    como = _preparar(cliente)
    assert _comentar(cliente, como, "   ").status_code == 422
    assert cliente.post("/partidos/P-03/comentarios", json={"contenido": "sin id"}, headers=como).status_code == 422
    assert cliente.post("/partidos/P-03/comentarios", json={"comentario_id": str(uuid.uuid4()), "contenido": "x",
                                                          "pais": "BRA"}, headers=como).status_code == 422
    assert _comentar(cliente, {}).status_code == 401


def test_historial_de_un_pais(cliente, reloj):
    como = _preparar(cliente)
    _comentar(cliente, como, "primero")
    reloj.instante += timedelta(seconds=10)
    como2 = entrar(cliente, cliente.post("/usuarios", json={"nombre": "Beto", "pais": "ARG"}).json()["usuario"]["id"])
    _comentar(cliente, como2, "segundo")
    resp = cliente.get("/partidos/P-03/comentarios?pais=ARG")
    assert resp.status_code == 200
    assert [c["contenido"] for c in resp.json()["items"]] == ["segundo", "primero"]
    assert resp.json()["siguiente"] is None


def test_historial_todos_mezcla_paises_por_fecha(cliente, reloj):
    _comentar(cliente, _preparar(cliente, "ARG", "Ana"), "de Argentina")
    reloj.instante += timedelta(seconds=10)
    _comentar(cliente, _preparar(cliente, "ESP", "Lola", en_juego=False), "de España")
    items = cliente.get("/partidos/P-03/comentarios?alcance=todos").json()["items"]
    assert [(c["pais"], c["contenido"]) for c in items] == [("ESP", "de España"), ("ARG", "de Argentina")]


def test_historial_pagina_con_antes_de(cliente, reloj):
    for n in range(3):
        _comentar(cliente, _preparar(cliente, "ARG", f"Hincha {n}", en_juego=n == 0), f"c{n}")
        reloj.instante += timedelta(seconds=10)
    pagina = cliente.get("/partidos/P-03/comentarios?pais=ARG&limit=2").json()
    assert [c["contenido"] for c in pagina["items"]] == ["c2", "c1"] and pagina["siguiente"]
    resto = cliente.get("/partidos/P-03/comentarios", params={"pais": "ARG", "antes_de": pagina["siguiente"]}).json()
    assert [c["contenido"] for c in resto["items"]] == ["c0"]


def test_recientes_sigue_respondiendo(cliente):
    _comentar(cliente, _preparar(cliente), "hola")
    resp = cliente.get("/partidos/P-03/comentarios/recientes?pais=ARG")
    assert resp.status_code == 200 and resp.json()["items"][0]["contenido"] == "hola"
    assert cliente.get("/partidos/P-03/comentarios/recientes?pais=arg").status_code == 422


def test_paginar_no_saltea_comentarios_del_mismo_instante(cliente, reloj):
    """Varios comentarios con la misma hora justo en el corte de página: tienen que aparecer todos, una vez."""
    _comentar(cliente, _preparar(cliente, "ARG", "Viejo"), "anterior")
    reloj.instante += timedelta(seconds=10)
    for n in range(3):  # el reloj no avanza: los tres quedan con la misma hora
        _comentar(cliente, _preparar(cliente, "ARG", f"Hincha {n}", en_juego=False), f"junto{n}")
    vistos, antes_de = [], None
    for _ in range(5):
        parametros = {"pais": "ARG", "limit": 2, **({"antes_de": antes_de} if antes_de else {})}
        pagina = cliente.get("/partidos/P-03/comentarios", params=parametros).json()
        vistos += [c["contenido"] for c in pagina["items"]]
        antes_de = pagina["siguiente"]
        if not antes_de:
            break
    assert sorted(vistos) == ["anterior", "junto0", "junto1", "junto2"]


def test_historial_de_un_partido_terminado_hace_dias(cliente, reloj):
    """Sin `antes_de`, el historial de un partido cerrado arranca en su cierre y no en la hora actual."""
    _comentar(cliente, _preparar(cliente), "durante el partido")
    reloj.instante += timedelta(minutes=5)
    cierre = cliente.post("/partidos/P-03/resultado", json={"goles_local": 1, "goles_visitante": 0}, headers=ADMIN)
    assert cierre.status_code == 202, cierre.text
    reloj.instante += timedelta(days=3)
    resp = cliente.get("/partidos/P-03/comentarios?pais=ARG")
    assert [c["contenido"] for c in resp.json()["items"]] == ["durante el partido"]
    assert cliente.get("/partidos/P-03/comentarios/recientes?pais=ARG").json()["items"]


def test_historial_sigue_respondiendo_si_no_se_puede_consultar_el_cierre(cliente, mongo):
    _comentar(cliente, _preparar(cliente), "hola")
    mongo.caida = True
    resp = cliente.get("/partidos/P-03/comentarios?pais=ARG")
    assert resp.status_code == 200 and resp.json()["items"][0]["contenido"] == "hola"


def test_cada_pais_que_comenta_queda_anotado_en_cassandra_una_vez(cliente, cassandra):
    como = _preparar(cliente, "MEX", "Memo")
    _comentar(cliente, como, "uno")
    _comentar(cliente, _preparar(cliente, "MEX", "Lupe", en_juego=False), "dos")
    assert cassandra.paises == {"P-03": {"MEX"}}
    assert cassandra.altas_de_pais == 1


def test_historial_de_todos_no_depende_de_redis(cliente, redis):
    """Qué países comentaron un partido se lee de Cassandra: perder Redis no deja el historial incompleto."""
    _comentar(cliente, _preparar(cliente, "MEX", "Memo"), "de México")
    _comentar(cliente, _preparar(cliente, "FRA", "Léa", en_juego=False), "de Francia")
    redis.borrar("paises:P-03")
    items = cliente.get("/partidos/P-03/comentarios?alcance=todos").json()["items"]
    assert sorted(c["pais"] for c in items) == ["FRA", "MEX"]
    redis.caida = True
    resp = cliente.get("/partidos/P-03/comentarios?alcance=todos")
    assert resp.status_code == 200 and len(resp.json()["items"]) == 2
