import pytest

from app.dominio.ranking_redis import codificar_puntaje, miembro_redis, usuario_de_miembro


def test_desempates_en_mismo_orden_que_el_tpo():
    a = codificar_puntaje(3, 1, 0)
    b = codificar_puntaje(3, 0, 104 * 432000)
    c = codificar_puntaje(2, 104, 104 * 432000)
    assert a > b > c
    assert codificar_puntaje(3, 1, 10) > codificar_puntaje(3, 1, 9)
    assert miembro_redis("U0000001") > miembro_redis("U0000002")
    assert usuario_de_miembro(miembro_redis("U0000001")) == "U0000001"


def test_puntaje_cabe_en_double_sin_perdida():
    n = codificar_puntaje(384, 128, 128 * 432000)
    assert n < 2**53 and int(float(n)) == n


@pytest.mark.parametrize("valores", [(-1, 0, 0), (385, 0, 0), (0, 129, 0), (0, 0, 128 * 432000 + 1)])
def test_rechaza_desbordes(valores):
    with pytest.raises(ValueError):
        codificar_puntaje(*valores)


def test_posicion_sin_datos_no_rompe():
    """Un usuario que figura en el conjunto ordenado pero no tiene datos se informa como sin puntaje."""
    from types import SimpleNamespace

    from app.adapters.ranking_redis import RankingRedis

    class Tubo:
        def __init__(self):
            self.respuestas = []

        def zrevrank(self, clave, miembro):
            self.respuestas.append(0)

        def hget(self, clave, campo):
            self.respuestas.append(None)

        def zcard(self, clave):
            self.respuestas.append(1)

        def execute(self):
            return self.respuestas

    cliente = SimpleNamespace(exists=lambda clave: 1, pipeline=lambda transaction=False: Tubo())
    ranking = RankingRedis(mongo=None, settings=SimpleNamespace(redis_lote=500, redis_persistencia_demora_segundos=0),
                           cliente=cliente)
    assert ranking.posicion("U0000001") is None


def test_las_lecturas_personales_van_a_la_replica_y_si_falla_al_primario():
    from types import SimpleNamespace

    import redis

    from app.adapters.ranking_redis import RankingRedis

    class Cliente:
        def __init__(self, nombre, falla=False):
            self.nombre, self.falla, self.usado = nombre, falla, 0

    primario, replica = Cliente("primario"), Cliente("replica")
    ajustes = SimpleNamespace(redis_lote=500, redis_persistencia_demora_segundos=0)
    ranking = RankingRedis(None, ajustes, cliente=primario, lectura=replica)
    assert ranking._leer(lambda c: c.nombre) == "replica"

    def falla_en_la_replica(cliente):
        if cliente is replica:
            raise redis.ConnectionError("réplica caída")
        return cliente.nombre

    assert ranking._leer(falla_en_la_replica) == "primario"
    assert RankingRedis(None, ajustes, cliente=primario)._leer(lambda c: c.nombre) == "primario"


def test_el_ranking_publico_se_guarda_unos_segundos_en_cada_proceso():
    from app.services import ranking as modulo

    modulo._COPIA_PUBLICA.clear()
    ahora = [100.0]

    class Contador:
        nombre = "redis"
        consultas = 0

        def top(self, limit):
            self.consultas += 1
            return [{"puesto": 1, "consulta": self.consultas}]

    fuente = Contador()
    servicio = modulo.RankingService(fuente, mongo=None, copia_segundos=2, reloj=lambda: ahora[0])
    assert servicio.top(20) == servicio.top(20) and fuente.consultas == 1
    servicio.top(100)
    assert fuente.consultas == 2  # cada tamaño tiene su copia
    ahora[0] += 2.1
    assert servicio.top(20)[0]["consulta"] == 3
    modulo._COPIA_PUBLICA.clear()
