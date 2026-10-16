import json
import re
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]


def _requests(items):
    for it in items:
        if "item" in it:
            yield from _requests(it["item"])
        else:
            yield it


def _plantilla(path: str) -> str:
    return re.sub(r"/(P-\d+|U\d+|[A-Z]{3}|[a-z]-?\d+|[a-z]{3})(?=/|$)", "/{}", path)


def _coleccion():
    return json.loads((RAIZ / "postman" / "fixture2030_collection.json").read_text(encoding="utf-8"))


def test_cada_request_de_postman_existe_en_openapi():
    spec = yaml.safe_load((RAIZ / "openapi" / "openapi.yaml").read_text(encoding="utf-8"))
    normalizadas = {re.sub(r"\{[^}]+\}", "{}", p): set(ops) for p, ops in spec["paths"].items()}
    cuenta = 0
    for req in _requests(_coleccion()["item"]):
        path = "/" + "/".join(req["request"]["url"]["path"])
        plantilla = _plantilla(path)
        assert plantilla in normalizadas, f"{path} no existe en OpenAPI"
        assert req["request"]["method"].lower() in normalizadas[plantilla]
        cuenta += 1
    assert cuenta >= 30  # casos felices + errores por módulo


def test_hay_escenarios_de_error_por_modulo():
    nombres = " ".join(r["name"] for r in _requests(_coleccion()["item"]))
    for palabra in ("404", "422", "409"):
        assert palabra in nombres


def test_cada_request_tiene_test_de_estado():
    for req in _requests(_coleccion()["item"]):
        codigo = "".join(req["event"][0]["script"]["exec"])
        assert "to.have.status(" in codigo
