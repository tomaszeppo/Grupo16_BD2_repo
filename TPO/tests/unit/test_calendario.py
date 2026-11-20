from datetime import timedelta

import pytest

from app.errors import DependenciaNoDisponible
from app.services.calendario import Calendario


@pytest.fixture
def calendario(neo4j, reloj):
    return Calendario(neo4j, 30, reloj)


def test_dos_lecturas_seguidas_consultan_neo4j_una_sola_vez(calendario, neo4j):
    assert calendario.partido("P-03")["id"] == "P-03"
    assert calendario.partido("P-04")["id"] == "P-04"
    assert neo4j.llamadas == 1


def test_partido_inexistente_devuelve_none(calendario):
    assert calendario.partido("P-999") is None


def test_pasados_30_segundos_vuelve_a_consultar(calendario, neo4j, reloj):
    calendario.partido("P-03")
    reloj.instante += timedelta(seconds=29)
    calendario.partido("P-03")
    assert neo4j.llamadas == 1
    reloj.instante += timedelta(seconds=2)
    calendario.partido("P-03")
    assert neo4j.llamadas == 2


def test_la_copia_refleja_los_cambios_recien_al_renovarse(calendario, neo4j, reloj):
    calendario.partido("P-03")
    neo4j.partidos["P-03"]["estado"] = "En juego"
    assert calendario.partido("P-03")["estado"] == "Programado"
    reloj.instante += timedelta(seconds=31)
    assert calendario.partido("P-03")["estado"] == "En juego"


def test_invalidar_fuerza_una_consulta_nueva(calendario, neo4j):
    calendario.partido("P-03")
    neo4j.partidos["P-03"]["estado"] = "En juego"
    calendario.invalidar()
    assert calendario.partido("P-03")["estado"] == "En juego"
    assert neo4j.llamadas == 2


def test_con_neo4j_caido_sigue_con_la_copia_y_lo_informa(calendario, neo4j, reloj):
    calendario.partido("P-03")
    neo4j.caida = True
    reloj.instante += timedelta(seconds=31)
    assert calendario.partido("P-03")["id"] == "P-03"
    estado = calendario.estado()
    assert estado["cargado"] is True and estado["desactualizado"] is True
    assert estado["antiguedad_segundos"] == pytest.approx(31)


def test_con_neo4j_caido_no_reintenta_en_cada_pedido(calendario, neo4j, reloj):
    calendario.partido("P-03")
    neo4j.caida = True
    reloj.instante += timedelta(seconds=31)
    for _ in range(10):
        calendario.partido("P-03")
    assert neo4j.llamadas == 2  # la carga inicial y un solo intento fallido
    reloj.instante += timedelta(seconds=6)
    calendario.partido("P-03")
    calendario.esperar_renovacion()
    assert neo4j.llamadas == 3


def test_cuando_neo4j_vuelve_deja_de_estar_desactualizado(calendario, neo4j, reloj):
    calendario.partido("P-03")
    neo4j.caida = True
    reloj.instante += timedelta(seconds=31)
    calendario.partido("P-03")
    neo4j.caida = False
    reloj.instante += timedelta(seconds=6)
    calendario.partido("P-03")
    calendario.esperar_renovacion()
    estado = calendario.estado()
    assert estado["desactualizado"] is False and estado["antiguedad_segundos"] == 0


def test_sin_copia_y_con_neo4j_caido_propaga_el_error(calendario, neo4j):
    neo4j.caida = True
    with pytest.raises(DependenciaNoDisponible):
        calendario.partido("P-03")
    assert calendario.estado() == {"cargado": False, "antiguedad_segundos": None, "desactualizado": True}


def test_con_ttl_cero_consulta_neo4j_en_cada_pedido(neo4j, reloj):
    calendario = Calendario(neo4j, 0, reloj)
    calendario.partido("P-03")
    calendario.partido("P-03")
    assert neo4j.llamadas == 2
    neo4j.caida = True
    with pytest.raises(DependenciaNoDisponible):
        calendario.partido("P-03")


def test_salud_incluye_el_estado_del_calendario(cliente):
    cuerpo = cliente.get("/health/dependencias").json()
    assert set(cuerpo["calendario"]) == {"cargado", "antiguedad_segundos", "desactualizado"}


def test_el_listado_del_fixture_sale_de_la_copia(calendario, neo4j):
    assert len(calendario.listar(None, None, None)) == 128
    assert len(calendario.listar("Fase de grupos", None, None)) == 96
    assert [p["id"] for p in calendario.listar(None, None, "Finalizado")] == ["P-01", "P-02"]
    from datetime import date
    assert len(calendario.listar(None, date(2030, 6, 13), None)) == 6
    assert neo4j.llamadas == 1


def test_el_listado_no_deja_modificar_la_copia(calendario):
    calendario.listar(None, None, None)[0]["estado"] = "Roto"
    assert calendario.partido("P-01")["estado"] == "Finalizado"


def test_el_fixture_se_sigue_viendo_con_neo4j_caido_si_hay_copia(cliente, neo4j):
    assert cliente.get("/partidos").json()["total"] == 128
    neo4j.caida = True
    resp = cliente.get("/partidos", params={"fase": "Final"})
    assert resp.status_code == 200 and resp.json()["total"] == 1
    assert cliente.get("/partidos/P-03").status_code == 503  # el detalle sigue saliendo de Neo4j en el momento


# --- Neo4j colgado: la renovación no puede frenar a los demás pedidos (defecto hallado en la prueba de caída) ---
class _Neo4jLento:
    """Simula un Neo4j que no contesta: la consulta queda bloqueada hasta que la prueba la suelta."""

    def __init__(self, real):
        import threading

        self._real = real
        self.soltar = threading.Event()
        self.entro = threading.Event()
        self.colgado = False
        self.llamadas = 0

    def listar_partidos(self, *args):
        self.llamadas += 1
        if self.colgado:
            self.entro.set()
            self.soltar.wait(5)
            raise DependenciaNoDisponible("neo4j")
        return self._real.listar_partidos(*args)


def test_mientras_un_pedido_renueva_la_copia_los_demas_no_esperan(neo4j, reloj):
    import threading
    import time

    lento = _Neo4jLento(neo4j)
    calendario = Calendario(lento, 30, reloj)
    calendario.partido("P-03")
    lento.colgado = True
    reloj.instante += timedelta(seconds=31)

    primero = threading.Thread(target=calendario.partido, args=("P-03",))
    primero.start()
    assert lento.entro.wait(2)  # el primer pedido quedó esperando a Neo4j
    t0 = time.perf_counter()
    assert calendario.partido("P-04")["id"] == "P-04"
    assert calendario.listar("Final", None, None)[0]["fase"] == "Final"
    assert time.perf_counter() - t0 < 0.5
    lento.soltar.set()
    primero.join(2)
    assert calendario.estado()["desactualizado"] is True


def test_con_neo4j_caido_los_reintentos_no_frenan_a_ningun_pedido(neo4j, reloj):
    import time

    lento = _Neo4jLento(neo4j)
    calendario = Calendario(lento, 30, reloj)
    calendario.partido("P-03")
    lento.colgado = True
    lento.soltar.set()  # el primer intento falla enseguida: ya se sabe que Neo4j está caído
    reloj.instante += timedelta(seconds=31)
    calendario.partido("P-03")
    assert calendario.estado()["desactualizado"] is True

    lento.soltar.clear()  # ahora cada intento queda colgado
    reloj.instante += timedelta(seconds=6)
    t0 = time.perf_counter()
    assert calendario.partido("P-03")["id"] == "P-03"  # dispara el reintento, pero no lo espera
    assert time.perf_counter() - t0 < 0.5
    assert lento.entro.wait(2)
    lento.soltar.set()
    calendario.esperar_renovacion()
    assert lento.llamadas == 3
