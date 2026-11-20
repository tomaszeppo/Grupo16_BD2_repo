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
    n = codificar_puntaje(312, 104, 104 * 432000)
    assert n < 2**53 and int(float(n)) == n


@pytest.mark.parametrize("valores", [(-1, 0, 0), (313, 0, 0), (0, 105, 0), (0, 0, 104 * 432000 + 1)])
def test_rechaza_desbordes(valores):
    with pytest.raises(ValueError):
        codificar_puntaje(*valores)
