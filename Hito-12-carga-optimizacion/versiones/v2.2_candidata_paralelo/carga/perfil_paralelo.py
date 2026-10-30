"""Preparacion determinista y coordinacion; no conecta ni escribe en Cassandra."""
import datetime
import random

_barrera = None
PERFILES = {'A': (50000, 100, 1), 'B': (50000, 50, 2)}


def validar_perfil(perfil, filas, concurrencia, procesos):
    if perfil not in PERFILES or (filas, concurrencia, procesos) != PERFILES[perfil]:
        raise ValueError('Perfil invalido: A=50000/100/1; B=50000/50/2. Validacion previa a conectar.')


def parametros(desde, hasta, partido, base, crear_uuid):
    """Misma secuencia que la base 1x100, independiente del reparto entre procesos."""
    if desde < 0 or hasta < desde:
        raise ValueError('Rango invalido')
    azar = random.Random(2030)
    for _ in range(desde):
        azar.randint(0, 10)
    filas = []
    for i in range(desde, hasta):
        momento = base + datetime.timedelta(milliseconds=i)
        filas.append((partido, i % 13, crear_uuid(momento, i), f'user-{i % 5000:06d}',
                      'Comentario de prueba de rendimiento', momento, 'visible', azar.randint(0, 10)))
    return filas


def inicializar_worker(barrera):
    global _barrera
    _barrera = barrera


def esperar_inicio():
    if _barrera is not None:
        _barrera.wait(timeout=60)


def abortar_inicio():
    if _barrera is not None:
        _barrera.abort()
