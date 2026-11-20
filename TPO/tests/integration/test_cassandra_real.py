"""Cassandra real en dos regiones: lo que se escribe en una aparece en la otra."""
import time
import uuid
from datetime import datetime, timezone

from app.adapters.cassandra import CassandraAdapter


def test_escribe_en_una_region_y_se_lee_en_la_otra(ajustes):
    cassandra = CassandraAdapter(ajustes)
    ahora = datetime.now(timezone.utc).replace(microsecond=0)
    ventana = ahora.replace(minute=ahora.minute // 30 * 30, second=0)
    partido = f"P-{90 + uuid.uuid4().int % 10}"
    comentario = {"partido_id": partido, "pais": "ARG", "ventana": ventana, "creado_en": ahora,
                  "comentario_id": uuid.uuid4(), "usuario_nombre": "Prueba", "contenido": "desde América",
                  "origen": "usuario"}
    assert cassandra.guardar_comentario("america", comentario) == "america"
    for _ in range(50):
        filas, region = cassandra.comentarios("europa", partido, "ARG", ventana, datetime(2100, 1, 1, tzinfo=timezone.utc), 10)
        if any(f["comentario_id"] == str(comentario["comentario_id"]) for f in filas):
            break
        time.sleep(0.1)
    assert region == "europa"
    assert any(f["contenido"] == "desde América" for f in filas)


def test_cada_region_responde_al_ping(ajustes):
    cassandra = CassandraAdapter(ajustes)
    cassandra.ping_region("america")
    cassandra.ping_region("europa")
