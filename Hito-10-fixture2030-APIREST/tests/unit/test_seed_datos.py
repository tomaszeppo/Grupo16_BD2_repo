import re

from seed import datos


def test_ids_y_codigos_coherentes_entre_fuentes():
    codigos = {c for c, _ in datos.EQUIPOS}
    assert all(re.fullmatch(r"[A-Z]{3}", c) for c in codigos)
    for p in datos.PARTIDOS:
        assert re.fullmatch(r"P-\d{2}", p["id"])
        assert p["local"] in codigos and p["visitante"] in codigos
        assert p["estadio"] in {e[0] for e in datos.ESTADIOS}
    assert [p["id"] for p in datos.PARTIDOS] == [f"P-{i:02d}" for i in range(1, 9)]


def test_jugadores_cumplen_el_esquema_de_main():
    js = datos.jugadores()
    assert len(js) == 5 * len(datos.EQUIPOS)
    assert {j["posicion"] for j in js} <= {"Portero", "Defensa", "Centrocampista", "Delantero"}
    assert all(set(j) == {"nombre", "apellido", "dorsal", "equipo", "posicion"} for j in js)
    assert len({(j["equipo"], j["dorsal"]) for j in js}) == len(js)


def test_eventos_apuntan_a_partidos_existentes():
    ids = {p["id"] for p in datos.PARTIDOS}
    assert set(datos.EVENTOS) <= ids and "P-01" in datos.EVENTOS
    assert set(datos.IRIS_EVENTOS) <= ids and set(datos.RESULTADOS) <= ids
