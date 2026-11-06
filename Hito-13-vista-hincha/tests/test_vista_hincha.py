"""Comportamiento del acceso y del puente a la API, sin bases reales."""
import sys
import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ), str(RAIZ.parent / "Hito-10-fixture2030-APIREST")]
import server
from app.schemas.partidos import PartidoGrafo, EventosPartido
from app.schemas.iris import PartidoIris
from app.schemas.estadisticas import Estadisticas
from app.schemas.comentarios import PaginaComentarios, ComentarioCreado
from app.schemas.equipos import PaginaJugadores


@pytest.fixture
def client():
    server.SESIONES.clear()
    server.demo.COMENTARIOS.clear()
    with TestClient(server.app) as c:
        yield c


def entrar(client, modo="demo"):
    return client.post("/api/sesion", json={"usuario_id": "U001", "nombre": "Facu", "pais": "ARG", "modo": modo})


def vigente():
    return {"usuario_id": "U001", "session_id": "S001", "estado_acceso": "ACTIVA", "ttl_segundos": 900}


def test_no_hay_acceso_sin_sesion(client):
    assert client.get("/api/partidos").status_code == 401
    assert client.get("/api/fixture/partidos/P-01").status_code == 401


def test_demo_cumple_los_contratos_originales(client):
    assert entrar(client).status_code == 200
    modelos = [
        ("partidos/P-01", PartidoGrafo), ("partidos/P-01/detalle", PartidoIris),
        ("partidos/P-01/eventos", EventosPartido), ("equipos/ARG/jugadores", PaginaJugadores),
        ("partidos/P-01/comentarios?ventana=2030-06-15T18:30:00Z", PaginaComentarios),
        ("partidos/P-01/estadisticas?desde=2030-06-15T18:30:00Z&hasta=2030-06-15T18:40:00Z", Estadisticas),
    ]
    for ruta, modelo in modelos:
        r = client.get("/api/fixture/"+ruta)
        assert r.status_code == 200, r.text
        modelo.model_validate(r.json())
    assert len(client.get("/api/partidos").json()["items"]) == 8


def test_demo_no_fabrica_estadisticas_fuera_de_la_ventana(client):
    entrar(client)
    r = client.get("/api/fixture/partidos/P-01/estadisticas?desde=2026-11-06T18:30:00Z&hasta=2026-11-06T18:40:00Z")
    assert r.json()["puntos"] == []


def test_comentario_idempotente_e_identidad_de_la_sesion(client):
    entrar(client)
    ruta, headers = "/api/fixture/partidos/P-01/comentarios", {"Idempotency-Key": "hincha-prueba-001"}
    a = client.post(ruta, json={"contenido": "¡Vamos!"}, headers=headers)
    b = client.post(ruta, json={"contenido": "¡Vamos!"}, headers=headers)
    assert a.status_code == b.status_code == 200
    ComentarioCreado.model_validate(a.json())
    assert a.json()["comentario_id"] == b.json()["comentario_id"]
    assert a.json()["usuario_nombre"] == "Facu"
    assert client.post(ruta, json={"contenido": "Otro"}, headers=headers).status_code == 409
    ventana = a.json()["ventana"]
    data = client.get("/api/fixture/partidos/P-01/comentarios", params={"ventana": ventana}).json()
    assert len(data["items"]) == 1
    # El país de una query no permite saltar la preferencia guardada en sesión.
    assert client.get("/api/fixture/partidos/P-01/comentarios", params={"pais": "BRA", "ventana": ventana}).json()["pais"] == "ARG"


def test_tribuna_demo_compartida_entre_sesiones_del_mismo_pais(client):
    entrar(client)
    r = client.post("/api/fixture/partidos/P-01/comentarios", json={"contenido": "Solo acá"}, headers={"Idempotency-Key": "demo-aislada-001"})
    with TestClient(server.app) as otro:
        entrar(otro)
        data = otro.get("/api/fixture/partidos/P-01/comentarios", params={"ventana": r.json()["ventana"]}).json()
        assert [c["contenido"] for c in data["items"]] == ["Solo acá"]
        otro.post("/api/sesion", json={"usuario_id": "U003", "nombre": "Otro", "pais": "BRA", "modo": "demo"})
        assert otro.get("/api/fixture/partidos/P-01/comentarios", params={"ventana": r.json()["ventana"]}).json()["items"] == []


def test_sesion_vencida_y_logout(client):
    entrar(client)
    server.SESIONES[client.cookies.get(server.COOKIE)]["vence"] = time.time()-1
    assert client.get("/api/sesion").status_code == 401
    assert client.delete("/api/sesion").status_code == 204
    assert not client.cookies.get(server.COOKIE)


def test_login_real_no_reemplaza_falla_con_demo(client, monkeypatch):
    remoto = AsyncMock(side_effect=HTTPException(503, "Redis no disponible"))
    monkeypatch.setattr(server, "consultar", remoto)
    assert entrar(client, "real").status_code == 503
    assert not client.cookies.get(server.COOKIE)
    assert not server.SESIONES


@pytest.mark.parametrize("datos", [dict(vigente(), estado_acceso="CERRADA"), None])
def test_login_real_rechaza_sesion_cerrada_o_ausente(client, monkeypatch, datos):
    remoto = AsyncMock(return_value=datos) if datos else AsyncMock(side_effect=HTTPException(404, "Sesión ausente"))
    monkeypatch.setattr(server, "consultar", remoto)
    assert entrar(client, "real").status_code in (401, 404)
    assert not server.SESIONES


def test_real_revalida_sesion_y_cierra_en_redis(client, monkeypatch):
    remoto = AsyncMock(return_value=vigente())
    monkeypatch.setattr(server, "consultar", remoto)
    r = entrar(client, "real")
    assert r.status_code == 200
    assert "HttpOnly" in r.headers["set-cookie"] and "SameSite=lax" in r.headers["set-cookie"]
    assert r.json()["ttl_segundos"] <= 900
    assert client.get("/api/sesion").status_code == 200
    assert client.delete("/api/sesion").status_code == 204
    remoto.assert_awaited_with("DELETE", "sesiones/U001")


def test_sesion_remota_invalidada(client, monkeypatch):
    remoto = AsyncMock(return_value=vigente())
    monkeypatch.setattr(server, "consultar", remoto)
    entrar(client, "real")
    remoto.side_effect = HTTPException(404, "Sesión ausente")
    assert client.get("/api/partidos").status_code == 401


def test_post_real_toma_la_identidad_de_la_sesion(client, monkeypatch):
    async def consultar(metodo, ruta, **kwargs):
        return {"estado": "En juego"} if ruta.endswith("/detalle") else vigente()
    remoto = AsyncMock(side_effect=consultar)
    monkeypatch.setattr(server, "consultar", remoto)
    entrar(client, "real")
    r = client.post("/api/fixture/partidos/P-01/comentarios", json={"contenido": "¡Vamos!", "usuario_id": "U999"}, headers={"Idempotency-Key": "real-prueba-001"})
    assert r.status_code == 200
    remoto.assert_awaited_with("POST", "partidos/P-01/comentarios", json={"contenido": "¡Vamos!", "usuario_id": "U001", "usuario_nombre": "Facu", "pais": "ARG"}, headers={"Idempotency-Key": "real-prueba-001"})


def test_no_expone_controles_tecnicos_y_rechaza_otro_origen(client):
    entrar(client)
    assert client.get("/api/fixture/health").status_code == 404
    assert client.get("/api/fixture/partidos/P-01/estado").status_code == 404
    assert client.post("/api/sesion", headers={"Origin": "https://otro.test"}, json={}).status_code == 403


def test_catalogo_clasifica_con_estado_de_iris(client):
    entrar(client)
    items = client.get("/api/partidos").json()["items"]
    assert [m["partido"]["id"] for m in items if m["estado"] == "En juego"] == ["P-01"]
    assert [m["partido"]["id"] for m in items if m["estado"] == "Finalizado"] == ["P-02"]
    assert sum(m["estado"] == "Programado" for m in items) == 6


def test_directo_conserva_comentarios_al_cambiar_de_media_hora(client):
    entrar(client)
    s = server.SESIONES[client.cookies.get(server.COOKIE)]
    ahora = datetime(2026, 11, 6, 18, 0, tzinfo=timezone.utc)
    for i, minutos in enumerate([0, -1, -61]):
        creado = ahora+timedelta(minutes=minutos)
        ventana = creado.replace(minute=(creado.minute//30)*30, second=0, microsecond=0)
        server.demo.COMENTARIOS.append({"comentario_id": str(i), "partido_id": "P-01", "pais": "ARG",
            "ventana": ventana.isoformat().replace("+00:00", "Z"), "creado_en": creado.isoformat()})
    items = asyncio.run(server.comentarios_recientes("P-01", s, ahora))
    assert [c["comentario_id"] for c in items] == ["0", "1"]


def test_evento_sse_confirma_consulta_y_valida_expiracion(client):
    entrar(client)
    clave = client.cookies.get(server.COOKIE)
    class Peticion:
        cookies = {server.COOKIE: clave}
        async def is_disconnected(self):
            return False
    async def primera():
        flujo = server.transmitir_comentarios(Peticion(), "P-01")
        evento = await anext(flujo)
        await flujo.aclose()
        return evento
    evento = asyncio.run(primera())
    assert evento.startswith("event: comentarios\n")
    assert "consultado_en" in json.loads(evento.split("data: ")[1])
    server.SESIONES[clave]["vence"] = time.time()-1
    assert '"codigo": 401' in asyncio.run(primera())


@pytest.mark.parametrize("partido", ["P-02", "P-03"])
def test_tribuna_solo_escribe_en_partidos_en_juego(client, partido):
    entrar(client)
    r = client.post(f"/api/fixture/partidos/{partido}/comentarios", json={"contenido": "Prueba"},
                    headers={"Idempotency-Key": "partido-cerrado-001"})
    assert r.status_code == 409
    assert server.demo.COMENTARIOS == []


def test_sse_informa_falla_sin_publicar_sincronizacion_exitosa(client, monkeypatch):
    entrar(client)
    clave = client.cookies.get(server.COOKIE)
    monkeypatch.setattr(server, "comentarios_recientes", AsyncMock(side_effect=HTTPException(503, "Tribuna no disponible")))
    class Peticion:
        cookies = {server.COOKIE: clave}
        async def is_disconnected(self):
            return False
    async def primera():
        flujo = server.transmitir_comentarios(Peticion(), "P-01")
        evento = await anext(flujo)
        await flujo.aclose()
        return evento
    evento = asyncio.run(primera())
    assert evento.startswith("event: estado\n")
    assert '"codigo": 503' in evento
    assert "consultado_en" not in evento
