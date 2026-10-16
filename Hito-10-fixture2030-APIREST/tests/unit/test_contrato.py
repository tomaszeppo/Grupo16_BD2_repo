from pathlib import Path

import yaml

RUTA = Path(__file__).resolve().parents[2] / "openapi" / "openapi.yaml"
ESPERADAS = {
    ("get", "/equipos/{codigo}"), ("get", "/equipos/{codigo}/jugadores"),
    ("get", "/partidos/{partido_id}"), ("get", "/partidos/{partido_id}/eventos"),
    ("get", "/partidos/{partido_id}/comentarios"), ("post", "/partidos/{partido_id}/comentarios"),
    ("get", "/sesiones/{usuario_id}"), ("delete", "/sesiones/{usuario_id}"),
    ("get", "/partidos/{partido_id}/estadisticas"),
    ("get", "/partidos/{partido_id}/detalle"), ("post", "/partidos/{partido_id}/estado"),
    ("get", "/health"),
}


def test_yaml_publicado_coincide_con_la_aplicacion(app):
    publicado = yaml.safe_load(RUTA.read_text(encoding="utf-8"))
    assert publicado == app.openapi(), "openapi.yaml desactualizado: ejecutar scripts/exportar_openapi.py"


def test_exactamente_los_endpoints_previstos(app):
    spec = app.openapi()
    reales = {(m, p) for p, ops in spec["paths"].items() for m in ops}
    assert reales == ESPERADAS


def test_metadatos_y_tags(app):
    spec = app.openapi()
    assert spec["info"]["title"] and spec["info"]["version"] and spec["servers"][0]["url"]
    assert len(spec["tags"]) >= 7


def test_todas_las_operaciones_documentan_los_errores_comunes(app):
    spec = app.openapi()
    for ruta, ops in spec["paths"].items():
        for metodo, op in ops.items():
            codigos = set(op["responses"])
            assert {"422", "503"} <= codigos or ruta == "/health", f"{metodo} {ruta}: {codigos}"
            assert "summary" in op and op.get("tags"), f"{metodo} {ruta} sin summary/tags"


def test_error_schema_comun(app):
    esquemas = app.openapi()["components"]["schemas"]
    assert {"ErrorRespuesta", "ErrorCuerpo"} <= set(esquemas)
    assert set(esquemas["ErrorCuerpo"]["required"]) == {"codigo", "mensaje", "request_id"}


def test_idempotency_key_documentada(app):
    post = app.openapi()["paths"]["/partidos/{partido_id}/comentarios"]["post"]
    cabeceras = [p for p in post["parameters"] if p["in"] == "header"]
    assert cabeceras and cabeceras[0]["name"] == "Idempotency-Key" and cabeceras[0]["required"] is True
    assert {"200", "201", "409"} <= set(post["responses"])
