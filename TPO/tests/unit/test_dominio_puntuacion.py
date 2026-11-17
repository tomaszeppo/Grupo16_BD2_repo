from datetime import datetime, timedelta, timezone

import pytest

from app.dominio.puntuacion import TOPE_ANTICIPACION, Puntaje, calcular

INICIO = datetime(2030, 6, 13, 15, 0, tzinfo=timezone.utc)


def puntuar(pron, real, antes=timedelta(hours=1), inicio_real=INICIO):
    return calcular(pron[0], pron[1], real[0], real[1], INICIO - antes, INICIO, inicio_real)


def test_resultado_exacto_vale_3_y_suma_toda_la_anticipacion():
    assert puntuar((2, 1), (2, 1)) == Puntaje(puntos=3, exacto=True, tiempo_seg=3600, anulado=False)


def test_acertar_solo_el_ganador_vale_1_y_suma_la_mitad():
    assert puntuar((3, 1), (2, 1)) == Puntaje(puntos=1, exacto=False, tiempo_seg=1800, anulado=False)


def test_acertar_el_empate_sin_el_marcador_vale_1():
    assert puntuar((1, 1), (0, 0)).puntos == 1
    assert puntuar((0, 0), (0, 0)).puntos == 3


def test_no_acertar_vale_0_y_no_suma_tiempo():
    assert puntuar((0, 1), (2, 1)) == Puntaje(puntos=0, exacto=False, tiempo_seg=0, anulado=False)
    assert puntuar((1, 1), (2, 1)).puntos == 0
    assert puntuar((2, 1), (1, 1)).puntos == 0


def test_la_anticipacion_se_recorta_a_cinco_dias():
    assert TOPE_ANTICIPACION == 432000
    assert puntuar((2, 1), (2, 1), antes=timedelta(days=6)).tiempo_seg == 432000
    assert puntuar((3, 1), (2, 1), antes=timedelta(days=6)).tiempo_seg == 216000
    assert puntuar((2, 1), (2, 1), antes=timedelta(days=5)).tiempo_seg == 432000


def test_la_mitad_se_redondea_hacia_abajo():
    assert puntuar((3, 1), (2, 1), antes=timedelta(seconds=1001)).tiempo_seg == 500


def test_cargado_despues_del_horario_programado_no_suma_tiempo():
    # el partido empezó tarde: el pronóstico vale, pero no hay anticipación que premiar
    tarde = puntuar((2, 1), (2, 1), antes=timedelta(minutes=-5), inicio_real=INICIO + timedelta(minutes=10))
    assert tarde == Puntaje(puntos=3, exacto=True, tiempo_seg=0, anulado=False)


@pytest.mark.parametrize("despues", [timedelta(0), timedelta(seconds=1), timedelta(minutes=20)])
def test_cargado_cuando_el_partido_ya_habia_empezado_se_anula(despues):
    inicio_real = INICIO - timedelta(minutes=30)  # lo pusieron en juego antes de hora
    cargado = inicio_real + despues
    resultado = calcular(2, 1, 2, 1, cargado, INICIO, inicio_real)
    assert resultado == Puntaje(puntos=0, exacto=False, tiempo_seg=0, anulado=True)


def test_un_instante_antes_del_inicio_real_cuenta():
    inicio_real = INICIO - timedelta(minutes=30)
    resultado = calcular(2, 1, 2, 1, inicio_real - timedelta(milliseconds=1), INICIO, inicio_real)
    # la anticipación cuenta cambios de segundo (como $dateDiff en MongoDB): de 14:29:59,999 a 15:00:00 son 1801
    assert resultado.puntos == 3 and resultado.anulado is False and resultado.tiempo_seg == 1801
