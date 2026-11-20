def test_health_responde_ok(cliente):
    resp = cliente.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"estado": "ok"}


def test_dependencias_informa_cada_base(cliente):
    resp = cliente.get("/health/dependencias")
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["mongodb"]["estado"] == "ok"
    assert cuerpo["neo4j"]["estado"] == "ok"
    assert cuerpo["redis"]["estado"] == "ok"


def test_dependencias_marca_la_base_caida_y_sigue_respondiendo(cliente, neo4j):
    neo4j.caida = True
    resp = cliente.get("/health/dependencias")
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["neo4j"]["estado"] == "caida"
    assert cuerpo["neo4j"]["detalle"]
    assert cuerpo["mongodb"]["estado"] == "ok"


def test_dependencias_informa_redis_caido(cliente, redis):
    redis.caida = True
    cuerpo = cliente.get("/health/dependencias").json()
    assert cuerpo["redis"]["estado"] == "caida"
