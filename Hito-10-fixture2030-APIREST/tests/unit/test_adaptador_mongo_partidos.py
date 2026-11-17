from types import SimpleNamespace

import pytest

from app.adapters.mongo import MongoAdapter
from app.config.settings import Settings
from app.errors import Conflicto, NoEncontrado


class ColeccionFalsa:
    def __init__(self, documento):
        self.documento = documento
        self.filtro_actualizacion = None

    def find_one(self, filtro, proyeccion):
        if self.documento is None or self.documento["codigo"] != filtro["codigo"]:
            return None
        return {"estado": self.documento["estado"]} if "estado" in proyeccion else dict(self.documento)

    def update_one(self, filtro, actualizacion):
        self.filtro_actualizacion = filtro
        if self.documento is None or any(self.documento.get(k) != v for k, v in filtro.items()):
            return SimpleNamespace(modified_count=0)
        self.documento.update(actualizacion["$set"])
        return SimpleNamespace(modified_count=1)


def adaptador(documento):
    coleccion = ColeccionFalsa(documento)
    db = SimpleNamespace(partidos=coleccion)
    instancia = MongoAdapter(Settings(_env_file=None))
    instancia._db = lambda: db
    return instancia, coleccion


def test_obtener_detalle_usa_documento_del_partido():
    esperado = {"codigo": "P-01", "estado": "En juego", "eventos": []}
    instancia, _ = adaptador(esperado)
    assert instancia.obtener_partido_detalle("P-01") == esperado


def test_cambiar_estado_actualiza_con_condicion_sobre_estado_previo():
    instancia, coleccion = adaptador({"codigo": "P-03", "estado": "Programado"})
    instancia.cambiar_estado_partido("P-03", "En juego")
    assert coleccion.documento["estado"] == "En juego"
    assert coleccion.filtro_actualizacion == {"codigo": "P-03", "estado": "Programado"}


@pytest.mark.parametrize(
    "documento,codigo,nuevo,error",
    [
        (None, "P-99", "En juego", NoEncontrado),
        ({"codigo": "P-03", "estado": "Programado"}, "P-03", "Finalizado", Conflicto),
    ],
)
def test_cambiar_estado_rechaza_partido_inexistente_o_transicion_invalida(documento, codigo, nuevo, error):
    instancia, _ = adaptador(documento)
    with pytest.raises(error):
        instancia.cambiar_estado_partido(codigo, nuevo)
