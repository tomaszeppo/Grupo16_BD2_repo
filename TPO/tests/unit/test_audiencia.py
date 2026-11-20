"""Cierre de cada minuto simulado: Redis → InfluxDB y aviso de estado a los espectadores."""
import json
import time
from datetime import datetime, timezone

from app.config.settings import Settings
from app.services.audiencia import Audiencia
from tests.falsos import RedisFalso

CORRIDA = "a" * 32
INSTANTE = datetime(2030, 6, 13, 15, 23, tzinfo=timezone.utc)


class InfluxQueAnota:
    def __init__(self, falla=False):
        self.minutos, self.resumenes, self.falla = [], [], falla

    def guardar_audiencia(self, *args):
        if self.falla:
            from app.errors import DependenciaNoDisponible
            raise DependenciaNoDisponible("influxdb")
        self.minutos.append(args)

    def guardar_resumen_audiencia(self, *args):
        self.resumenes.append(args)


def _audiencia(redis, influx):
    return Audiencia(redis, influx, Settings(_env_file=None))


def test_cerrar_minuto_cuenta_por_pais_y_vacia_contadores():
    redis, influx = RedisFalso(), InfluxQueAnota()
    ahora = time.time()
    redis.marcar("audiencia:P-03:ARG", "a", ahora)
    redis.marcar("audiencia:P-03:ARG", "b", ahora)
    redis.marcar("audiencia:P-03:ARG", "viejo", ahora - 60)  # proceso muerto: no cuenta
    redis.marcar("audiencia:P-03:ESP", "c", ahora)
    for _ in range(3):
        redis.incrementar("cuenta:P-03:ARG:usuario")
    redis.incrementar("cuenta:P-03:ESP:simulacion")
    estado = _audiencia(redis, influx).cerrar_minuto("P-03", 23, CORRIDA, "demo", INSTANTE,
                                                     {"local": 1, "visitante": 0}, "En juego")
    assert estado["audiencia"] == {"total": 3, "por_pais": {"ARG": 2, "BRA": 0, "ESP": 1, "URU": 0}}
    _, minuto, corrida, tipo, espectadores, comentarios, instante = influx.minutos[0]
    assert (minuto, corrida, tipo, instante) == (23, CORRIDA, "demo", INSTANTE)
    assert espectadores["ARG"] == 2 and espectadores["ESP"] == 1
    assert comentarios[("ARG", "usuario")] == 3 and comentarios[("ESP", "simulacion")] == 1
    assert redis.tomar_y_borrar("cuenta:P-03:ARG:usuario") == 0
    canal, mensaje = redis.publicados[-1]
    assert canal == "estado:P-03" and json.loads(mensaje)["minuto"] == 23


def test_paises_incluye_a_quienes_miran():
    redis = RedisFalso()
    redis.agregar_a_conjunto("paises:P-03", "JPN")
    assert _audiencia(redis, InfluxQueAnota()).paises_de("P-03") == {"ARG", "BRA", "ESP", "URU", "JPN"}


def test_redis_caido_no_corta_la_simulacion():
    redis = RedisFalso()
    redis.caida = True
    estado = _audiencia(redis, InfluxQueAnota()).cerrar_minuto("P-03", 5, CORRIDA, "demo", INSTANTE, {}, "En juego")
    assert estado["incompleto"] is True


def test_influx_caido_igual_avisa_a_los_espectadores():
    redis = RedisFalso()
    estado = _audiencia(redis, InfluxQueAnota(falla=True)).cerrar_minuto("P-03", 5, CORRIDA, "demo", INSTANTE, {}, "En juego")
    assert estado["incompleto"] is True
    assert redis.publicados[-1][0] == "estado:P-03"


def test_cerrar_partido_guarda_los_unicos():
    redis, influx = RedisFalso(), InfluxQueAnota()
    for usuario in ("U1", "U2", "U1"):
        redis.agregar_unico("unicos:P-03:ARG", usuario)
    _audiencia(redis, influx).cerrar_partido("P-03", CORRIDA, "demo", INSTANTE)
    assert influx.resumenes[0][3]["ARG"] == 2


def test_el_aviso_de_final_sale_despues_de_guardar_los_unicos():
    """La interfaz pide el análisis al recibir "Finalizado": los únicos ya tienen que estar en InfluxDB."""
    redis = RedisFalso()
    avisos_al_guardar = []

    class Influx(InfluxQueAnota):
        def guardar_resumen_audiencia(self, *args):
            avisos_al_guardar.append(len(redis.publicados))

    _audiencia(redis, Influx()).cerrar_partido("P-03", CORRIDA, "demo", INSTANTE, {"local": 1, "visitante": 0})
    assert avisos_al_guardar == [0]
    assert json.loads(redis.publicados[-1][1])["estado"] == "Finalizado"
