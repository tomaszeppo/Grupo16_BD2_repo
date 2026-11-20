"""Reiniciar el laboratorio también borra en Redis lo que cuenta la audiencia de cada partido."""
from seed.run import borrar_audiencia_de_redis, borrar_comentarios_de_cassandra


class RedisDeClaves:
    def __init__(self, claves):
        self.claves = set(claves)

    def scan_iter(self, match):
        prefijo = match.rstrip("*")
        return [c for c in list(self.claves) if c.startswith(prefijo)]

    def delete(self, *claves):
        self.claves.difference_update(claves)


def test_borra_audiencia_y_conserva_sesiones():
    redis = RedisDeClaves(["unicos:P-07:ARG", "paises:P-07", "audiencia:P-07:ARG", "cuenta:P-07:ARG:usuario",
                           "visto:abc", "lento:U0000001", "sesion:token"])
    assert borrar_audiencia_de_redis(redis) == 6
    assert redis.claves == {"sesion:token"}


def test_borra_los_comentarios_y_los_paises_de_cassandra():
    ejecutadas = []
    borrar_comentarios_de_cassandra(ejecutadas.append)
    assert ejecutadas == ["TRUNCATE fixture2030.comentarios_por_partido_pais",
                          "TRUNCATE fixture2030.paises_por_partido"]
