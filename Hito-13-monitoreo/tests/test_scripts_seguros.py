"""Los scripts de prueba dejan el entorno como estaba aunque algo falle a mitad de camino."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import carga_comentarios  # noqa: E402
import prueba_controlada  # noqa: E402


def test_redis_se_reinicia_aunque_la_prueba_falle():
    llamadas = []
    with pytest.raises(RuntimeError):
        with prueba_controlada.contenedor_detenido("redis-x", ejecutar=llamadas.append):
            raise RuntimeError("se cortó la prueba")
    assert llamadas == [["docker", "stop", "redis-x"], ["docker", "start", "redis-x"]]


def test_resultados_se_guardan_aunque_falle_la_verificacion(tmp_path, monkeypatch):
    monkeypatch.setattr(carga_comentarios, "enviar", lambda *a, **k: [
        {"n": 0, "pais": "ARG", "codigo": 201, "comentario_id": "c1", "ventana": "v"}])

    def verificar_roto(*_):
        raise KeyError("items")

    monkeypatch.setattr(carga_comentarios, "verificar", verificar_roto)
    monkeypatch.setattr(sys, "argv", ["carga", "--cantidad", "1", "--salida", str(tmp_path)])
    with pytest.raises(KeyError):
        carga_comentarios.main()
    archivos = list(tmp_path.glob("pico_comentarios_*.jsonl"))
    assert len(archivos) == 1
    assert json.loads(archivos[0].read_text(encoding="utf-8").splitlines()[0])["comentario_id"] == "c1"
