"""Resumen del escenario de carga del partido en vivo."""
from carga.vivo import resumir_vivo


def test_resumir_vivo():
    eventos = [
        {"tipo": "conexion", "ok": True}, {"tipo": "conexion", "ok": True}, {"tipo": "conexion", "ok": False},
        {"tipo": "comentario", "estado": 201}, {"tipo": "comentario", "estado": 201},
        {"tipo": "comentario", "estado": 429}, {"tipo": "comentario", "estado": 503},
        {"tipo": "entrega", "ms": 10.0}, {"tipo": "entrega", "ms": 20.0},
        {"tipo": "audiencia", "total": 2}, {"tipo": "audiencia", "total": 1},
        {"tipo": "reconexion"},
    ]
    r = resumir_vivo(eventos, espectadores=3)
    assert r["espectadores_pedidos"] == 3
    assert r["conexiones"] == {"abiertas": 2, "fallidas": 1, "reconexiones": 1}
    assert r["comentarios"] == {"enviados": 4, "publicados": 2, "modo_lento": 1, "partido_terminado": 0, "errores": 1}
    assert r["entrega_ms"] == {"medidas": 2, "p50": 10.0, "p95": 20.0, "p99": 20.0, "max": 20.0}
    assert r["audiencia_reportada_max"] == 2


def test_resumir_vivo_sin_entregas():
    r = resumir_vivo([{"tipo": "conexion", "ok": False}], espectadores=1)
    assert r["entrega_ms"]["p95"] is None and r["audiencia_reportada_max"] == 0


def test_comentario_con_el_partido_terminado_no_es_error():
    r = resumir_vivo([{"tipo": "comentario", "estado": 409}, {"tipo": "comentario", "estado": 0}], espectadores=1)
    assert r["comentarios"] == {"enviados": 2, "publicados": 0, "modo_lento": 0, "partido_terminado": 1, "errores": 1}
