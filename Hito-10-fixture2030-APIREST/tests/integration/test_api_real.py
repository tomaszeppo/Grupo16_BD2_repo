import os
import uuid

import httpx
import pytest

BASE = os.getenv("API_URL", "http://127.0.0.1:8000")
pytestmark = pytest.mark.integration
V = "2030-06-15T18:30:00Z"


@pytest.fixture(scope="module")
def http():
    with httpx.Client(base_url=BASE, timeout=15) as c:
        yield c


def err(r):
    return r.json()["error"]["codigo"]


def test_health_todas_las_fuentes_ok(http):
    r = http.get("/health")
    assert r.status_code == 200, r.text
    assert {f["estado"] for f in r.json()["fuentes"].values()} == {"ok"}
    assert set(r.json()["fuentes"]) == {"mongodb", "neo4j", "cassandra", "redis", "influxdb", "iris"}


def test_correlacion_request_id(http):
    r = http.get("/equipos/ARG", headers={"X-Request-ID": "prueba-integracion-1"})
    assert r.headers["X-Request-ID"] == "prueba-integracion-1"


# --- MongoDB
def test_mongo_equipo(http):
    assert http.get("/equipos/ARG").json() == {"codigo": "ARG", "nombre": "Argentina"}


def test_mongo_jugadores_paginacion(http):
    r = http.get("/equipos/ARG/jugadores", params={"limit": 2, "offset": 1})
    cuerpo = r.json()
    assert r.status_code == 200 and cuerpo["total"] == 5 and len(cuerpo["items"]) == 2


def test_mongo_ausente_y_validacion(http):
    assert http.get("/equipos/ZZZ").status_code == 404
    r = http.get("/equipos/arg")
    assert r.status_code == 422 and err(r) == "VALIDACION"


# --- Neo4j
def test_neo4j_partido_y_eventos(http):
    p = http.get("/partidos/P-01").json()
    assert [e["codigo"] for e in p["equipos"]] == ["ARG", "BRA"] and p["estadio"]["id"] == "EST001"
    assert p["resultado"]["origen"] == "SIMULADO"
    ev = http.get("/partidos/P-01/eventos").json()["items"]
    assert [e["minuto"] for e in ev] == [0, 32, 90]


def test_neo4j_distingue_inexistente_de_sin_eventos(http):
    assert http.get("/partidos/P-99").status_code == 404
    assert http.get("/partidos/P-03/eventos").json()["items"] == []  # existe, sin eventos sembrados


# --- Cassandra
def test_cassandra_lectura_y_paginacion(http):
    p = {"pais": "ARG", "ventana": V, "limit": 2}
    r1 = http.get("/partidos/P-01/comentarios", params=p).json()
    assert len(r1["items"]) == 2 and r1["next_cursor"]
    creados = [i["creado_en"] for i in r1["items"]]
    assert creados == sorted(creados, reverse=True)
    r2 = http.get("/partidos/P-01/comentarios", params={**p, "cursor": r1["next_cursor"]}).json()
    assert {i["comentario_id"] for i in r1["items"]}.isdisjoint({i["comentario_id"] for i in r2["items"]})


def test_cassandra_particion_vacia_es_200(http):
    r = http.get("/partidos/P-01/comentarios", params={"pais": "BRA", "ventana": V})
    assert r.status_code == 200 and r.json()["items"] == []


def test_cassandra_escritura_idempotente(http):
    h = {"Idempotency-Key": uuid.uuid4().hex}
    cuerpo = {"pais": "ARG", "usuario_id": "U001", "usuario_nombre": "Facundo", "contenido": "Prueba de integración ⚽"}
    a = http.post("/partidos/P-01/comentarios", json=cuerpo, headers=h)
    b = http.post("/partidos/P-01/comentarios", json=cuerpo, headers=h)
    assert (a.status_code, b.status_code) == (201, 200), (a.text, b.text)
    assert a.json()["comentario_id"] == b.json()["comentario_id"] and a.json()["creado_en"] == b.json()["creado_en"]
    otro = http.post("/partidos/P-02/comentarios", json=cuerpo, headers=h)
    assert otro.status_code == 409 and err(otro) == "CONFLICTO"


def test_cassandra_partido_inexistente_no_escribe(http):
    r = http.post("/partidos/P-99/comentarios", headers={"Idempotency-Key": uuid.uuid4().hex},
                  json={"pais": "ARG", "usuario_id": "U001", "usuario_nombre": "F", "contenido": "x"})
    assert r.status_code == 404


# --- Redis
def test_redis_sesion_vigente_cerrada_y_ausente(http):
    r = http.get("/sesiones/U001")
    assert r.status_code == 200 and 0 < r.json()["ttl_segundos"] <= 1800 and "token_ref" not in r.json()
    assert http.get("/sesiones/U002").status_code == 404
    assert err(http.get("/sesiones/U999")) == "SESION_NO_VIGENTE"


def test_redis_invalidacion_idempotente(http):
    assert http.delete("/sesiones/U003").status_code == 204
    assert http.delete("/sesiones/U003").status_code == 204
    assert http.get("/sesiones/U003").status_code == 404


# --- InfluxDB
def test_influx_ventana_agregada(http):
    r = http.get("/partidos/P-01/estadisticas",
                 params={"desde": V, "hasta": "2030-06-15T18:35:00Z", "agregacion": "1m", "equipo": "ARG"})
    cuerpo = r.json()
    assert r.status_code == 200, r.text
    assert len(cuerpo["puntos"]) == 10 and not cuerpo["truncado"]  # 5 min x 2 fuentes
    assert {p["equipo_id"] for p in cuerpo["puntos"]} == {"ARG"} and "velocidad_kmh_max" in cuerpo["puntos"][0]


def test_influx_raw_se_trunca_en_500(http):
    r = http.get("/partidos/P-01/estadisticas",
                 params={"desde": V, "hasta": "2030-06-15T18:40:00Z", "agregacion": "raw"})
    assert r.status_code == 200, r.text
    assert r.json()["truncado"] is True and len(r.json()["puntos"]) == 500


def test_influx_sin_datos_es_200_vacio_y_ventana_invalida_422(http):
    r = http.get("/partidos/P-05/estadisticas", params={"desde": V, "hasta": "2030-06-15T18:35:00Z"})
    assert r.status_code == 200 and r.json()["puntos"] == []
    assert http.get("/partidos/P-01/estadisticas",
                    params={"desde": "2030-06-15T18:35:00Z", "hasta": V}).status_code == 422


# --- IRIS
def test_iris_detalle(http):
    r = http.get("/partidos/P-01/detalle")
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "En juego" and len(r.json()["eventos"]) == 2


def test_iris_transiciones(http):
    assert http.post("/partidos/P-03/estado", json={"estado": "Finalizado"}).status_code == 409  # salta "En juego"
    a = http.post("/partidos/P-08/estado", json={"estado": "En juego"})
    b = http.post("/partidos/P-08/estado", json={"estado": "En juego"})  # idempotente
    assert (a.status_code, b.status_code) == (200, 200), (a.text, b.text)
    assert b.json()["estado"] == "En juego"
    assert http.post("/partidos/P-08/estado", json={"estado": "Programado"}).status_code == 409
    assert http.get("/partidos/P-99/detalle").status_code == 404
