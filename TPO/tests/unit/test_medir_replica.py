"""Resumen de la medición de atraso de la réplica de Redis."""
from scripts.medir_replica_redis import resumir_atrasos


def test_resumir_atrasos_separa_los_que_no_llegaron():
    r = resumir_atrasos([1.0, 2.0, 3.0, 4.0, None], tope_ms=50)
    assert r["muestras"] == 5 and r["sin_llegar"] == 1
    assert r["p50_ms"] == 2.0 and r["p95_ms"] == 4.0 and r["max_ms"] == 4.0


def test_resumir_atrasos_sin_ninguna_llegada():
    r = resumir_atrasos([None, None], tope_ms=50)
    assert r["sin_llegar"] == 2 and r["p50_ms"] is None
