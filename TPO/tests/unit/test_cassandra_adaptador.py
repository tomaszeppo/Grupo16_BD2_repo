"""Si la región del usuario no responde, Cassandra atiende desde la otra."""
import uuid
from datetime import datetime, timezone

import pytest

from app.errors import DependenciaNoDisponible
from tests.falsos import CassandraFalso


def _comentario(pais="ESP"):
    ahora = datetime(2030, 6, 13, 15, 10, tzinfo=timezone.utc)
    return {"partido_id": "P-03", "pais": pais, "ventana": ahora.replace(minute=0), "creado_en": ahora,
            "comentario_id": uuid.uuid4(), "usuario_nombre": "Ana", "contenido": "hola", "origen": "usuario"}


def test_atiende_la_propia_region():
    assert CassandraFalso().guardar_comentario("europa", _comentario()) == "europa"


def test_si_la_region_cae_atiende_la_otra():
    cassandra = CassandraFalso()
    cassandra.caidas = {"europa"}
    assert cassandra.guardar_comentario("europa", _comentario()) == "america"
    filas, region = cassandra.comentarios("europa", "P-03", "ESP", _comentario()["ventana"],
                                          datetime(2031, 1, 1, tzinfo=timezone.utc), 10)
    assert region == "america" and len(filas) == 1


def test_con_las_dos_caidas_no_hay_servicio():
    cassandra = CassandraFalso()
    cassandra.caidas = {"europa", "america"}
    with pytest.raises(DependenciaNoDisponible):
        cassandra.guardar_comentario("europa", _comentario())


def test_cambio_de_region_real_traduce_y_reintenta(monkeypatch):
    """El adaptador real: un NoHostAvailable en una región se reintenta en la otra."""

    class NoHostAvailable(Exception):  # mismo nombre que la del driver, que en Windows no carga sin libev
        pass

    from app.adapters.cassandra import CassandraAdapter
    from app.config.settings import Settings

    adaptador = CassandraAdapter(Settings(_env_file=None))
    usadas = []

    class Sesion:
        def __init__(self, region):
            self.region = region

        def execute(self, consulta, parametros):
            usadas.append(self.region)
            if self.region == "europa":
                raise NoHostAvailable("sin nodos")
            return []

    monkeypatch.setattr(adaptador, "_sesion", lambda region: Sesion(region))
    monkeypatch.setattr(adaptador, "_preparada", lambda sesion, nombre: nombre)
    assert adaptador.guardar_comentario("europa", _comentario()) == "america"
    assert usadas == ["europa", "america"]
