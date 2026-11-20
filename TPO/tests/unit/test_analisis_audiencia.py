"""Análisis de audiencia como el de un stream, consultas a InfluxDB y tramos de minutos."""
from types import SimpleNamespace

from app.adapters import influx
from app.services.analisis_audiencia import resumir

GOLES = [{"minuto": 1, "equipo_id": "ARG"}]


def test_resumir_calcula_pico_promedio_y_minutos_vistos():
    filas = [{"minuto": 0, "pais": "ARG", "espectadores": 2},
             {"minuto": 1, "pais": "ARG", "espectadores": 4}, {"minuto": 1, "pais": "ESP", "espectadores": 1}]
    r = resumir(filas, {"ARG": 5, "ESP": 1}, GOLES, desde=0, hasta=2)
    assert r["curva"] == [{"minuto": 0, "total": 2, "por_pais": {"ARG": 2}},
                          {"minuto": 1, "total": 5, "por_pais": {"ARG": 4, "ESP": 1}},
                          {"minuto": 2, "total": 0, "por_pais": {}}]
    assert r["pico"] == {"minuto": 1, "espectadores": 5}
    assert r["minutos_vistos"] == 7
    assert r["promedio"] == round(7 / 3, 1)
    assert r["unicos"] == {"total": 6, "por_pais": {"ARG": 5, "ESP": 1}}
    assert r["tiempo_medio_min"] == round(7 / 6, 1)
    assert r["goles"] == GOLES


def test_resumir_desempata_el_pico_por_el_primero():
    filas = [{"minuto": 3, "pais": "ARG", "espectadores": 2}, {"minuto": 7, "pais": "ARG", "espectadores": 2}]
    assert resumir(filas, {}, [], desde=0, hasta=10)["pico"] == {"minuto": 3, "espectadores": 2}


def test_resumir_sin_espectadores():
    r = resumir([], {}, [], desde=0, hasta=90)
    assert len(r["curva"]) == 91 and all(m["total"] == 0 for m in r["curva"])
    assert r["pico"] is None and r["tiempo_medio_min"] is None and r["minutos_vistos"] == 0
    assert r["promedio"] == 0.0


def test_resumir_solo_el_tramo_pedido():
    filas = [{"minuto": m, "pais": "ARG", "espectadores": 1} for m in range(91)]
    r = resumir(filas, {"ARG": 1}, [{"minuto": 80, "equipo_id": "ARG"}], desde=10, hasta=20)
    assert [m["minuto"] for m in r["curva"]] == list(range(10, 21))
    assert r["minutos_vistos"] == 11 and r["goles"] == []


def test_sql_de_audiencia_filtra_partido_corrida_tramo_y_pais():
    sql = influx.sql_audiencia("P-03", "a" * 32, 10, 20, "ARG")
    for parte in ("FROM audiencia_partido", "partido_id = 'P-03'", f"corrida_id = '{'a' * 32}'",
                  "minuto >= 10", "minuto <= 20", "pais = 'ARG'"):
        assert parte in sql


def test_sql_promedio_entre_partidos_suma_por_corrida_y_promedia_por_minuto():
    sql = influx.sql_audiencia_promedio("ARG", "carga")
    assert "GROUP BY corrida_id, minuto" in sql and "AVG(total)" in sql
    assert "pais = 'ARG'" in sql and "tipo = 'carga'" in sql
    assert "pais =" not in influx.sql_audiencia_promedio(None, None)


def test_sql_rechaza_valores_raros():
    import pytest

    from app.errors import ValidacionError

    with pytest.raises(ValidacionError):
        influx.sql_audiencia("P-03", "a" * 32, 0, 90, "AR'G")
    with pytest.raises(ValidacionError):
        influx.sql_audiencia_promedio(None, "otro")


def test_tramo_invalido_da_422(cliente):
    assert cliente.get("/partidos/P-03/audiencia?desde_minuto=50&hasta_minuto=10").status_code == 422
    assert cliente.get("/partidos/P-03/audiencia?hasta_minuto=91").status_code == 422
    assert cliente.get("/partidos/P-03/comentarios/por-minuto?desde_minuto=-1").status_code == 422
    assert cliente.get("/partidos/P-03/estadisticas?desde_minuto=30&hasta_minuto=20").status_code == 422
    assert cliente.get("/analisis/audiencia-por-minuto?tipo=otro").status_code == 422


def test_estadisticas_por_tramo_suma_solo_esos_minutos():
    from app.routes import simulaciones

    def fila(equipo, minuto, pases):
        return {"equipo_id": equipo, "minuto": minuto, "pases_intentados": pases, "pases_completados": pases,
                "tiros": 0, "tiros_arco": 0, "goles": 0, "faltas": 0, "corners": 0, "posesion_segundos": 30}

    minutos = [fila(e, m, m) for m in range(91) for e in ("ARG", "BRA")]
    doc = {"partido": {}, "estadisticas_version": 3, "corrida_id": "a" * 32}
    mongo = SimpleNamespace(db=SimpleNamespace(simulaciones=SimpleNamespace(find_one=lambda *a, **k: doc)))
    influx_falso = SimpleNamespace(agregados_eventos=lambda *a: ([dict(f) for f in minutos], []))
    r = simulaciones.estadisticas_partido("P-03", 10, 12, mongo=mongo, influx=influx_falso, neo=None)
    arg = next(e for e in r["equipos"] if e["equipo_id"] == "ARG")
    assert arg["pases_intentados"] == 10 + 11 + 12 and arg["posesion_pct"] == 50
    assert r["tramo"] == {"desde_minuto": 10, "hasta_minuto": 12}


def test_estadisticas_por_tramo_de_un_partido_archivado_salen_de_neo4j():
    from app.routes import simulaciones

    muestras = [{"equipo_id": "ARG", "minuto": m, "pases_intentados": 1, "pases_completados": 1, "tiros": 0,
                 "tiros_arco": 0, "goles": 0, "faltas": 0, "corners": 0, "posesion_segundos": 60} for m in range(91)]
    doc = {"partido": {}, "archivo_estado": "completo"}
    mongo = SimpleNamespace(db=SimpleNamespace(simulaciones=SimpleNamespace(find_one=lambda *a, **k: doc)))
    neo = SimpleNamespace(leer_estadisticas_archivadas=lambda _: {"equipos": [{"equipo_id": "ARG"}], "muestras": muestras})
    r = simulaciones.estadisticas_partido("P-03", 0, 44, mongo=mongo, influx=None, neo=neo)
    assert r["fuente"] == "neo4j" and r["equipos"][0]["pases_intentados"] == 45
    completo = simulaciones.estadisticas_partido("P-03", None, None, mongo=mongo, influx=None, neo=neo)
    assert completo["equipos"] == [{"equipo_id": "ARG"}]  # sin tramo, la respuesta de siempre


def test_tramo_archivado_calcula_la_posesion_desde_el_porcentaje_por_minuto():
    """Neo4j guarda la posesión de cada minuto como porcentaje (no en segundos): se reconstruye con 60 s por minuto."""
    from app.routes import simulaciones

    muestras = [{"equipo_id": e, "minuto": m, "posesion_pct": pct, "pases_intentados": 0, "pases_completados": 0,
                 "tiros": 0, "tiros_arco": 0, "goles": 0, "faltas": 0, "corners": 0}
                for m in range(91) for e, pct in (("ARG", 75.0 if m < 10 else 50.0), ("BRA", 25.0 if m < 10 else 50.0))]
    doc = {"partido": {}, "archivo_estado": "completo"}
    mongo = SimpleNamespace(db=SimpleNamespace(simulaciones=SimpleNamespace(find_one=lambda *a, **k: doc)))
    neo = SimpleNamespace(leer_estadisticas_archivadas=lambda _: {"equipos": [], "muestras": muestras})
    r = simulaciones.estadisticas_partido("P-03", 0, 9, mongo=mongo, influx=None, neo=neo)
    assert {e["equipo_id"]: round(e["posesion_pct"]) for e in r["equipos"]} == {"ARG": 75, "BRA": 25}


def test_las_consultas_de_un_partido_se_acotan_a_su_horario():
    """InfluxDB 3 Core limita cuántos archivos lee una consulta: con el rango de tiempo solo abre los del partido."""
    from datetime import datetime, timezone

    inicio = datetime(2030, 6, 13, 15, 0, 7, tzinfo=timezone.utc)
    for sql in (influx.sql_audiencia("P-03", "a" * 32, 0, 90, None, inicio),
                influx.sql_comentarios("P-03", "a" * 32, 0, 90, "ARG", inicio)):
        assert "time >= '2030-06-13T15:00:07Z' AND time < '2030-06-13T15:05:07Z'" in sql
    assert "time >=" not in influx.sql_audiencia("P-03", "a" * 32, 0, 90, None)  # simulaciones sin hora guardada
