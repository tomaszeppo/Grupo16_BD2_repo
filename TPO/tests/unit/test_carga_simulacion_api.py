from carga.simulacion_api import esperado


def test_resultado_esperado_refleja_las_reglas_del_tpo():
    assert esperado((2, 1), (2, 1)) == 3
    assert esperado((1, 0), (2, 1)) == 1
    assert esperado((1, 1), (2, 2)) == 1
    assert esperado((0, 2), (2, 1)) == 0
