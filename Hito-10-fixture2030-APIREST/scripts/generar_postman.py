"""Genera postman/fixture2030_collection.json (Postman Collection v2.1)."""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
V = "2030-06-15T18:30:00Z"
CUERPO = {"pais": "ARG", "usuario_id": "U001", "usuario_nombre": "Facundo", "contenido": "¡Vamos Argentina!"}

# (carpeta, nombre, método, ruta, query, cuerpo, cabeceras, status esperado)
R = [
    ("Sistema", "GET /health (200)", "GET", "/health", {}, None, {}, 200),
    ("MongoDB", "Equipo existente (200)", "GET", "/equipos/ARG", {}, None, {}, 200),
    ("MongoDB", "Equipo inexistente (404)", "GET", "/equipos/ZZZ", {}, None, {}, 404),
    ("MongoDB", "Código inválido (422)", "GET", "/equipos/arg", {}, None, {}, 422),
    ("MongoDB", "Jugadores paginados (200)", "GET", "/equipos/ARG/jugadores", {"limit": 2, "offset": 1}, None, {}, 200),
    ("MongoDB", "Jugadores filtro Delantero (200)", "GET", "/equipos/ARG/jugadores", {"posicion": "Delantero"}, None, {}, 200),
    ("MongoDB", "limit fuera de rango (422)", "GET", "/equipos/ARG/jugadores", {"limit": 101}, None, {}, 422),
    ("Neo4j", "Partido existente (200)", "GET", "/partidos/P-01", {}, None, {}, 200),
    ("Neo4j", "Partido inexistente (404)", "GET", "/partidos/P-99", {}, None, {}, 404),
    ("Neo4j", "ID inválido (422)", "GET", "/partidos/p-01", {}, None, {}, 422),
    ("Neo4j", "Eventos del partido (200)", "GET", "/partidos/P-01/eventos", {}, None, {}, 200),
    ("Neo4j", "Partido sin eventos (200 vacío)", "GET", "/partidos/P-03/eventos", {}, None, {}, 200),
    ("Neo4j", "Eventos de partido inexistente (404)", "GET", "/partidos/P-99/eventos", {}, None, {}, 404),
    ("Cassandra", "Comentarios ARG ventana 18:30 (200)", "GET", "/partidos/P-01/comentarios", {"pais": "ARG", "ventana": V, "limit": 2}, None, {}, 200),
    ("Cassandra", "Partición vacía (200 vacío)", "GET", "/partidos/P-01/comentarios", {"pais": "BRA", "ventana": V}, None, {}, 200),
    ("Cassandra", "Sin ventana (422)", "GET", "/partidos/P-01/comentarios", {"pais": "ARG"}, None, {}, 422),
    ("Cassandra", "Ventana no alineada (422)", "GET", "/partidos/P-01/comentarios", {"pais": "ARG", "ventana": "2030-06-15T18:45:00Z"}, None, {}, 422),
    ("Cassandra", "Crear comentario (201)", "POST", "/partidos/P-01/comentarios", {}, CUERPO, {"Idempotency-Key": "{{idem_key}}"}, 201),
    ("Cassandra", "Repetir con la misma clave (200)", "POST", "/partidos/P-01/comentarios", {}, CUERPO, {"Idempotency-Key": "{{idem_key}}"}, 200),
    ("Cassandra", "Misma clave, otro partido (409)", "POST", "/partidos/P-02/comentarios", {}, CUERPO, {"Idempotency-Key": "{{idem_key}}"}, 409),
    ("Cassandra", "Sin Idempotency-Key (422)", "POST", "/partidos/P-01/comentarios", {}, CUERPO, {}, 422),
    ("Cassandra", "Partido inexistente (404)", "POST", "/partidos/P-99/comentarios", {}, CUERPO, {"Idempotency-Key": "{{idem_key}}-x"}, 404),
    ("Redis", "Sesión vigente (200)", "GET", "/sesiones/U001", {}, None, {}, 200),
    ("Redis", "Sesión cerrada (404)", "GET", "/sesiones/U002", {}, None, {}, 404),
    ("Redis", "Sesión inexistente/expirada (404)", "GET", "/sesiones/U999", {}, None, {}, 404),
    ("Redis", "Invalidar sesión (204)", "DELETE", "/sesiones/U003", {}, None, {}, 204),
    ("Redis", "Invalidar de nuevo, idempotente (204)", "DELETE", "/sesiones/U003", {}, None, {}, 204),
    ("Redis", "Usuario inválido (422)", "GET", "/sesiones/u1", {}, None, {}, 422),
    ("InfluxDB", "Agregado 1m (200)", "GET", "/partidos/P-01/estadisticas", {"desde": V, "hasta": "2030-06-15T18:35:00Z", "agregacion": "1m"}, None, {}, 200),
    ("InfluxDB", "Raw truncado (200)", "GET", "/partidos/P-01/estadisticas", {"desde": V, "hasta": "2030-06-15T18:40:00Z", "agregacion": "raw"}, None, {}, 200),
    ("InfluxDB", "Sin datos (200 vacío)", "GET", "/partidos/P-05/estadisticas", {"desde": V, "hasta": "2030-06-15T18:35:00Z"}, None, {}, 200),
    ("InfluxDB", "Fechas invertidas (422)", "GET", "/partidos/P-01/estadisticas", {"desde": "2030-06-15T18:35:00Z", "hasta": V}, None, {}, 422),
    ("InfluxDB", "Ventana demasiado ancha (422)", "GET", "/partidos/P-01/estadisticas", {"desde": V, "hasta": "2030-06-15T22:30:00Z"}, None, {}, 422),
    ("IRIS", "Detalle del partido (200)", "GET", "/partidos/P-01/detalle", {}, None, {}, 200),
    ("IRIS", "Detalle inexistente (404)", "GET", "/partidos/P-99/detalle", {}, None, {}, 404),
    ("IRIS", "Transición válida (200)", "POST", "/partidos/P-08/estado", {}, {"estado": "En juego"}, {}, 200),
    ("IRIS", "Transición inválida (409)", "POST", "/partidos/P-03/estado", {}, {"estado": "Finalizado"}, {}, 409),
    ("IRIS", "Estado fuera del dominio (422)", "POST", "/partidos/P-01/estado", {}, {"estado": "Suspendido"}, {}, 422),
]


def _item(carpeta, nombre, metodo, ruta, query, cuerpo, cabeceras, status):
    url = {
        "raw": "{{base_url}}" + ruta, "host": ["{{base_url}}"], "path": ruta.strip("/").split("/"),
        "query": [{"key": k, "value": str(v)} for k, v in query.items()],
    }
    req = {"method": metodo, "url": url, "header": [{"key": k, "value": v} for k, v in cabeceras.items()]}
    if cuerpo is not None:
        req["header"].append({"key": "Content-Type", "value": "application/json"})
        req["body"] = {"mode": "raw", "raw": json.dumps(cuerpo, ensure_ascii=False)}
    script = [
        f"pm.test('status {status}', function () {{ pm.response.to.have.status({status}); }});",
        "pm.test('X-Request-ID presente', function () { pm.response.to.have.header('X-Request-ID'); });",
    ]
    if status >= 400:
        script.append(
            "pm.test('formato de error', function () { const e = pm.response.json().error; "
            "pm.expect(e).to.include.all.keys('codigo','mensaje','request_id'); });"
        )
    return {
        "name": nombre, "request": req,
        "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": script}}],
    }


def main():
    carpetas = {}
    for fila in R:
        carpetas.setdefault(fila[0], []).append(_item(*fila))
    coleccion = {
        "info": {
            "name": "Fixture 2030 — API integrada",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "description": "Casos felices y escenarios de error de los seis módulos. Requiere la API levantada (README).",
        },
        "variable": [
            {"key": "base_url", "value": "http://localhost:8000"},
            {"key": "idem_key", "value": "demo-postman-0001"},
        ],
        "item": [{"name": n, "item": items} for n, items in carpetas.items()],
    }
    destino = RAIZ / "postman" / "fixture2030_collection.json"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(json.dumps(coleccion, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"escrito {destino} ({len(R)} requests)")


if __name__ == "__main__":
    main()
