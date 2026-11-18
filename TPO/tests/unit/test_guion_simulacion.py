from types import SimpleNamespace
import json
import pytest
from app.errors import Conflicto, NoEncontrado
from seed.cargar_guion_simulacion import construir_guion, obtener_o_crear

PARTIDO = {"id":"P-12", "local":{"codigo":"ARG"}, "visitante":{"codigo":"BRA"}}

class Jugadores:
    def find_one(self, filtro, proyeccion):
        if filtro["dorsal"] == 26: return None
        return {"_id": f"J-{filtro['equipo']}-{filtro['dorsal']:02d}"}

class Guiones:
    def __init__(self): self.documentos = {}
    def find_one(self, filtro): return self.documentos.get(filtro["_id"])
    def update_one(self, filtro, operacion, upsert=False):
        self.documentos.setdefault(filtro["_id"], operacion["$setOnInsert"])


def test_guion_inserta_una_vez_y_conserva_relaciones():
    db = SimpleNamespace(jugadores=Jugadores(), guiones_simulacion=Guiones())
    primero = obtener_o_crear(PARTIDO, db)
    assert len(primero["jugadas"]) == 6
    assert primero["jugadas"][2]["tipo"] == "Gol"
    assert primero["jugadas"][2]["jugador"] == "J-ARG-09"
    assert primero["jugadas"][2]["influido_por"] == [primero["jugadas"][1]["id"]]
    assert obtener_o_crear(PARTIDO, db) == primero
    assert len(db.guiones_simulacion.documentos) == 1


def test_guion_rechaza_relacion_futura(tmp_path):
    archivo = tmp_path / "guion.json"
    archivo.write_text(json.dumps([{"equipo":"local","tipo":"Gol","minuto":23,"dorsal":9,"previa":1}]))
    with pytest.raises(Conflicto): construir_guion(PARTIDO, SimpleNamespace(jugadores=Jugadores()), archivo)


def test_guion_rechaza_jugador_inexistente(tmp_path):
    archivo = tmp_path / "guion.json"
    archivo.write_text(json.dumps([{"equipo":"local","tipo":"Gol","minuto":23,"dorsal":26}]))
    with pytest.raises(NoEncontrado): construir_guion(PARTIDO, SimpleNamespace(jugadores=Jugadores()), archivo)
