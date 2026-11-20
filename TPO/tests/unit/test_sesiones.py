"""Sesiones en Redis: crear, usar por encabezado o cookie, cerrar, vencer."""
from tests.apoyo import entrar


def _usuario(cliente, nombre="Ana", pais="ARG") -> str:
    return cliente.post("/usuarios", json={"nombre": nombre, "pais": pais}).json()["usuario"]["id"]


def test_crear_sesion_devuelve_token_y_cookie(cliente):
    u = _usuario(cliente)
    resp = cliente.post("/sesiones", json={"usuario_id": u})
    assert resp.status_code == 201, resp.text
    cuerpo = resp.json()
    assert cuerpo["fuente"] == "redis"
    assert len(cuerpo["token"]) >= 40
    assert cuerpo["usuario"]["id"] == u and cuerpo["usuario"]["pais"] == "ARG"
    cookie = resp.headers["set-cookie"]
    assert "sesion=" in cookie and "HttpOnly" in cookie and "SameSite=strict" in cookie.replace("Strict", "strict")


def test_sesion_de_usuario_inexistente_404(cliente):
    assert cliente.post("/sesiones", json={"usuario_id": "U0000099"}).status_code == 404
    assert cliente.post("/sesiones", json={"usuario_id": "juan"}).status_code == 422


def test_ruta_protegida_acepta_encabezado_y_cookie(cliente):
    u = _usuario(cliente)
    assert cliente.post("/prodes", json={"nombre": "Oficina"}, headers=entrar(cliente, u)).status_code == 201
    cliente.post("/sesiones", json={"usuario_id": u})  # deja la cookie en el cliente
    assert cliente.post("/prodes", json={"nombre": "Casa"}).status_code == 201


def test_x_usuario_id_ya_no_alcanza(cliente):
    u = _usuario(cliente)
    resp = cliente.post("/prodes", json={"nombre": "Oficina"}, headers={"X-Usuario-Id": u})
    assert resp.status_code == 401


def test_sesion_cerrada_o_inventada_da_401(cliente):
    u = _usuario(cliente)
    como = entrar(cliente, u)
    assert cliente.delete("/sesiones/actual", headers=como).status_code == 204
    assert cliente.post("/prodes", json={"nombre": "Oficina"}, headers=como).status_code == 401
    assert cliente.post("/prodes", json={"nombre": "Oficina"}, headers={"X-Sesion": "x" * 43}).status_code == 401


def test_cerrar_sesion_borra_la_cookie(cliente):
    u = _usuario(cliente)
    cliente.post("/sesiones", json={"usuario_id": u})
    resp = cliente.delete("/sesiones/actual")
    assert resp.status_code == 204
    assert 'sesion=""' in resp.headers["set-cookie"] or "Max-Age=0" in resp.headers["set-cookie"]


def test_usar_la_sesion_renueva_su_vida(cliente, redis):
    u = _usuario(cliente)
    cliente.post("/prodes", json={"nombre": "Oficina"}, headers=entrar(cliente, u))
    assert 86400 in redis.renovaciones


def test_sesion_vencida_da_401(cliente, redis):
    ahora = [1000.0]
    redis.reloj = lambda: ahora[0]
    u = _usuario(cliente)
    como = entrar(cliente, u)
    ahora[0] += 86401
    assert cliente.post("/prodes", json={"nombre": "Oficina"}, headers=como).status_code == 401


def test_redis_caido_da_503(cliente, redis):
    u = _usuario(cliente)
    como = entrar(cliente, u)
    redis.caida = True
    assert cliente.post("/sesiones", json={"usuario_id": u}).status_code == 503
    assert cliente.post("/prodes", json={"nombre": "Oficina"}, headers=como).status_code == 503
