"""Redis real: ida y vuelta de las operaciones que usan sesiones, presencia y comentarios."""
import time


def test_ida_y_vuelta(redis_real):
    redis_real.guardar("prueba:clave", "valor", 30)
    assert redis_real.leer("prueba:clave") == "valor"
    assert redis_real.leer_renovando("prueba:clave", 60) == "valor"
    redis_real.borrar("prueba:clave")
    assert redis_real.leer("prueba:clave") is None
    assert redis_real.reservar("prueba:unica", "x", 5) is True
    assert redis_real.reservar("prueba:unica", "x", 5) is False
    assert redis_real.incrementar("prueba:cuenta") == 1
    assert redis_real.tomar_y_borrar("prueba:cuenta") == 1
    assert redis_real.tomar_y_borrar("prueba:cuenta") == 0
    ahora = time.time()
    redis_real.marcar("prueba:z", "a", ahora - 60)
    redis_real.marcar("prueba:z", "b", ahora)
    assert redis_real.contar_desde("prueba:z", ahora - 15) == 1
    redis_real.agregar_unico("prueba:hll", "U1")
    redis_real.agregar_unico("prueba:hll", "U1")
    assert redis_real.contar_unicos("prueba:hll") == 1
    redis_real.publicar("prueba:canal", "hola")


def test_salud_informa_redis(cliente):
    assert cliente.get("/health/dependencias").json()["redis"]["estado"] == "ok"
