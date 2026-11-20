"""Reiniciar el laboratorio también borra en Redis lo que cuenta la audiencia de cada partido."""
from seed.run import borrar_audiencia_de_redis


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
