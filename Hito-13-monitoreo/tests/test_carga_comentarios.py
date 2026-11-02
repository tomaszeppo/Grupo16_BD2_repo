"""Generación y resumen del pico de comentarios, sin API real."""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from carga_comentarios import generar_comentarios, resumir  # noqa: E402

PAISES = ["ARG", "BRA", "ESP", "MAR"]


def test_claves_unicas_y_reparto():
    comentarios = generar_comentarios("c1", 1000, PAISES)
    claves = [c["clave"] for c in comentarios]
    assert len(set(claves)) == 1000
    assert all(k.startswith("h13-c1-") for k in claves)
    assert Counter(c["pais"] for c in comentarios) == {p: 250 for p in PAISES}
    # Cuerpo aceptado por el esquema del Hito 10 (U + 3 a 6 dígitos, contenido de hasta 280).
    assert all(c["cuerpo"]["usuario_id"][0] == "U" and c["cuerpo"]["usuario_id"][1:].isdigit() for c in comentarios)
    assert all(len(c["cuerpo"]["contenido"]) <= 280 for c in comentarios)


def test_corridas_distintas_no_colisionan():
    a = {c["clave"] for c in generar_comentarios("c1", 50, PAISES)}
    b = {c["clave"] for c in generar_comentarios("c2", 50, PAISES)}
    assert not a & b


def test_resumir_separa_altas_reintentos_y_errores():
    resultados = [
        {"pais": "ARG", "codigo": 201, "comentario_id": "a"},
        {"pais": "ARG", "codigo": 200, "comentario_id": "a"},
        {"pais": "BRA", "codigo": 201, "comentario_id": "b"},
        {"pais": "BRA", "codigo": 503, "comentario_id": None},
        {"pais": "ESP", "codigo": None, "comentario_id": None, "error": "ReadTimeout"},
    ]
    r = resumir(resultados)
    assert r["enviados"] == 5
    assert r["creados_201"] == 2
    assert r["reintentos_200"] == 1
    assert r["errores"] == {"503": 1, "ReadTimeout": 1}
    assert r["creados_por_pais"] == {"ARG": 1, "BRA": 1}
