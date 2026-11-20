"""Sesiones para el generador de carga: una por usuario, creadas por lotes y reutilizadas entre corridas."""
from carga import sesiones
from tests.falsos import RedisFalso


def test_preparar_crea_una_sesion_por_usuario(tmp_path):
    redis = RedisFalso()
    tokens = sesiones.preparar(redis, 5, archivo=tmp_path / "s.json")
    assert len(tokens) == 5 and len(set(tokens)) == 5
    assert redis.leer(f"sesion:{tokens[0]}") == "U0000001"
    assert redis.leer(f"sesion:{tokens[4]}") == "U0000005"


def test_preparar_reutiliza_las_sesiones_vivas(tmp_path):
    redis = RedisFalso()
    primera = sesiones.preparar(redis, 3, archivo=tmp_path / "s.json")
    assert sesiones.preparar(redis, 3, archivo=tmp_path / "s.json") == primera


def test_preparar_rehace_si_vencieron_o_faltan(tmp_path):
    redis = RedisFalso()
    primera = sesiones.preparar(redis, 3, archivo=tmp_path / "s.json")
    redis.borrar(f"sesion:{primera[0]}")
    segunda = sesiones.preparar(redis, 3, archivo=tmp_path / "s.json")
    assert segunda != primera and redis.leer(f"sesion:{segunda[0]}") == "U0000001"
    assert len(sesiones.preparar(redis, 4, archivo=tmp_path / "s.json")) == 4
