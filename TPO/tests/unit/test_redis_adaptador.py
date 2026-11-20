"""Adaptador de Redis: traducción de errores y comportamiento del falso que usan las demás pruebas."""
import pytest

from app.adapters.redis import _traducir
from app.errors import DependenciaNoDisponible, DependenciaTimeout
from tests.falsos import RedisFalso


def test_errores_del_driver_se_traducen():
    import redis

    assert isinstance(_traducir(redis.exceptions.ConnectionError("x")), DependenciaNoDisponible)
    assert isinstance(_traducir(redis.exceptions.TimeoutError("x")), DependenciaTimeout)
    assert _traducir(ValueError("x")) is None


def test_redis_falso_contar_desde_descarta_viejos():
    r = RedisFalso()
    r.marcar("z", "a", 10)
    r.marcar("z", "b", 20)
    assert r.contar_desde("z", 15) == 1
    r.marcar("z", "b", 30)
    assert r.contar_desde("z", 0) == 1  # "a" ya se borró


def test_redis_falso_respeta_vencimientos():
    ahora = [1000.0]
    r = RedisFalso(reloj=lambda: ahora[0])
    assert r.reservar("k", "v", 5) is True
    assert r.reservar("k", "v", 5) is False
    ahora[0] += 5.1
    assert r.leer("k") is None
    assert r.reservar("k", "v", 5) is True


def test_redis_falso_caido():
    r = RedisFalso()
    r.caida = True
    with pytest.raises(DependenciaNoDisponible):
        r.leer("k")
