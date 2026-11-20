from collections import Counter
from datetime import datetime, timedelta, timezone

import pytest

from app.dominio import ids
from seed import datos

INICIO = datetime(2030, 6, 13, 15, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def fx():
    return datos.generar(INICIO)


def test_64_equipos_en_16_grupos_de_4(fx):
    assert len(fx.equipos) == 64
    assert len({e["codigo"] for e in fx.equipos}) == 64
    assert all(ids.es_codigo_equipo(e["codigo"]) for e in fx.equipos)
    assert Counter(e["grupo"] for e in fx.equipos) == {g: 4 for g in "ABCDEFGHIJKLMNOP"}


def test_los_seis_anfitriones_encabezan_grupos_distintos(fx):
    grupo_de = {e["codigo"]: e["grupo"] for e in fx.equipos}
    assert [grupo_de[c] for c in datos.ANFITRIONES] == list("ABCDEF")


def test_26_jugadores_por_equipo_con_id_unico(fx):
    assert len(fx.jugadores) == 1664
    assert len({j["id"] for j in fx.jugadores}) == 1664
    assert set(Counter(j["equipo"] for j in fx.jugadores).values()) == {26}
    arg = sorted(j["dorsal"] for j in fx.jugadores if j["equipo"] == "ARG")
    assert arg == list(range(1, 27))
    assert any(j["id"] == "J-ARG-01" for j in fx.jugadores)


def test_16_estadios(fx):
    assert len(fx.estadios) == 16
    assert len({e["id"] for e in fx.estadios}) == 16


def test_128_partidos_con_ids_correlativos(fx):
    assert [p["id"] for p in fx.partidos] == [f"P-{i:02d}" for i in range(1, 129)]
    assert all(ids.es_id_partido(p["id"]) for p in fx.partidos)
    estadios = {e["id"] for e in fx.estadios}
    assert all(p["estadio"] in estadios for p in fx.partidos)


def test_fases_y_cantidades(fx):
    assert Counter(p["fase"] for p in fx.partidos) == {
        "Fase de grupos": 96, "Dieciseisavos": 16, "Octavos": 8, "Cuartos": 4,
        "Semifinal": 2, "Tercer puesto": 1, "Final": 1,
    }


def test_grupos_con_equipos_y_tres_partidos_por_equipo(fx):
    grupos = [p for p in fx.partidos if p["fase"] == "Fase de grupos"]
    grupo_de = {e["codigo"]: e["grupo"] for e in fx.equipos}
    jugados = Counter()
    for p in grupos:
        assert p["local"] and p["visitante"] and p["local"] != p["visitante"]
        assert grupo_de[p["local"]] == grupo_de[p["visitante"]]
        jugados[p["local"]] += 1
        jugados[p["visitante"]] += 1
    assert len(jugados) == 64 and set(jugados.values()) == {3}


def test_eliminatorias_sin_equipos(fx):
    eliminatorias = [p for p in fx.partidos if p["fase"] != "Fase de grupos"]
    assert all(p["local"] is None and p["visitante"] is None for p in eliminatorias)
    assert all(p["estado"] == "Programado" for p in eliminatorias)


def test_cuadro_de_eliminatorias(fx):
    existentes = {p["id"] for p in fx.partidos}
    assert Counter(como for _, _, como in fx.cuadro) == {"ganador": 30, "perdedor": 2}
    assert all(origen in existentes and destino in existentes for origen, destino, _ in fx.cuadro)
    fase = {p["id"]: p["fase"] for p in fx.partidos}
    assert {fase[d] for o, d, como in fx.cuadro if como == "perdedor"} == {"Tercer puesto"}
    entradas = Counter(destino for _, destino, _ in fx.cuadro)
    assert set(entradas.values()) == {2}  # a cada partido llegan exactamente dos


def test_calendario_parte_de_la_fecha_de_inicio(fx):
    por_id = {p["id"]: p for p in fx.partidos}
    assert por_id["P-03"]["fecha_hora"] == INICIO
    assert por_id["P-05"]["fecha_hora"] == INICIO + timedelta(hours=3)
    assert por_id["P-11"]["fecha_hora"] == INICIO + timedelta(days=1)
    assert all(p["fecha_hora"].tzinfo is not None for p in fx.partidos)
    fechas = [p["fecha_hora"] for p in fx.partidos]
    assert fechas == sorted(fechas)


def test_los_dos_partidos_de_muestra_ya_se_jugaron(fx):
    por_id = {p["id"]: p for p in fx.partidos}
    for pid in ("P-01", "P-02"):
        p = por_id[pid]
        assert p["estado"] == "Finalizado"
        assert p["fecha_hora"] < INICIO
        assert p["inicio_real"] == p["fecha_hora"]
    assert all(p["estado"] == "Programado" for p in fx.partidos[2:])
    assert set(fx.eventos) == {"P-01", "P-02"}


def test_el_marcador_de_muestra_coincide_con_los_goles(fx):
    equipo_de = {j["id"]: j["equipo"] for j in fx.jugadores}
    por_id = {p["id"]: p for p in fx.partidos}
    for pid, eventos in fx.eventos.items():
        goles = Counter(equipo_de[e["jugador"]] for e in eventos if e["tipo"] == "Gol")
        p = por_id[pid]
        assert goles[p["local"]] == p["goles_local"]
        assert goles[p["visitante"]] == p["goles_visitante"]


def test_eventos_bien_formados(fx):
    equipo_de = {j["id"]: j["equipo"] for j in fx.jugadores}
    por_id = {p["id"]: p for p in fx.partidos}
    for pid, eventos in fx.eventos.items():
        ids_evento = [e["id"] for e in eventos]
        assert len(set(ids_evento)) == len(ids_evento)
        assert all(e["tipo"] in datos.TIPOS_DE_EVENTO for e in eventos)
        assert eventos[0]["tipo"] == "Inicio" and eventos[-1]["tipo"] == "Final"
        assert [(e["minuto"], e["orden"]) for e in eventos] == sorted((e["minuto"], e["orden"]) for e in eventos)
        juegan = {por_id[pid]["local"], por_id[pid]["visitante"]}
        for e in eventos:
            if e["jugador"] is not None:
                assert equipo_de[e["jugador"]] in juegan
            if e["influye_en"] is not None:
                assert e["influye_en"] in ids_evento


def test_cada_gol_tiene_una_jugada_previa_que_influye(fx):
    for eventos in fx.eventos.values():
        goles = [e["id"] for e in eventos if e["tipo"] == "Gol"]
        assert goles
        influidos = {e["influye_en"] for e in eventos}
        assert set(goles) <= influidos
        assert any(e["tipo"] == "Pase" for e in eventos)
        assert any(e["tipo"] == "Tarjeta amarilla" for e in eventos)


def test_misma_semilla_mismo_resultado():
    assert datos.generar(INICIO, semilla=7) == datos.generar(INICIO, semilla=7)
    assert datos.generar(INICIO, semilla=7).eventos != datos.generar(INICIO, semilla=8).eventos


def test_ids():
    assert ids.id_pronostico("U0000001", "P-01") == "U0000001:P-01"
    assert ids.es_id_usuario("U0000001") and not ids.es_id_usuario("U1")
    assert ids.es_id_partido("P-128") and not ids.es_id_partido("P-1") and not ids.es_id_partido("abc")
    assert not ids.es_codigo_equipo("arg")


def test_en_la_fase_de_grupos_los_dos_partidos_de_cada_grupo_van_en_simultaneo(fx):
    grupo_de = {e["codigo"]: e["grupo"] for e in fx.equipos}
    por_horario = {}
    for p in fx.partidos:
        if p["fase"] == "Fase de grupos":
            por_horario.setdefault(p["fecha_hora"], []).append(grupo_de[p["local"]])
    assert set(map(len, por_horario.values())) == {2}
    assert all(len(set(grupos)) == 1 for grupos in por_horario.values())  # los dos son del mismo grupo
    por_id = {p["id"]: p for p in fx.partidos}
    assert por_id["P-03"]["fecha_hora"] == por_id["P-04"]["fecha_hora"]


def test_eliminatorias_de_a_un_partido_y_con_un_dia_libre_entre_rondas(fx):
    eliminatorias = [p for p in fx.partidos if p["fase"] != "Fase de grupos"]
    assert len({p["fecha_hora"] for p in eliminatorias}) == len(eliminatorias)
    ultimo_de = {}
    primero_de = {}
    for p in eliminatorias:
        primero_de.setdefault(p["fase"], p["fecha_hora"])
        ultimo_de[p["fase"]] = p["fecha_hora"]
    fases = list(primero_de)
    for anterior, siguiente in zip(fases, fases[1:]):
        assert primero_de[siguiente] - ultimo_de[anterior] > timedelta(days=1)
