"""Conexión en vivo: presencia, comentarios por tribuna, estado y audiencia, y espectadores lentos."""
import asyncio
import json

from app.config.settings import Settings
from app.services.vivo import Transmision, miembro_de
from tests.falsos import RedisAsincronoFalso


def _ajustes():
    return Settings(_env_file=None, presencia_refresco_segundos=0.05, vivo_latido_segundos=0.1)


async def _escuchar(transmision, salida, pais="ARG", alcance="pais", token="token-ana", usuario="U0000001"):
    async for trozo in transmision.escuchar("P-03", pais, alcance, token, usuario):
        salida.append(trozo)


def _eventos(salida, tipo):
    datos = []
    for trozo in salida:
        if trozo.startswith(f"event: {tipo}\n"):
            datos.append(json.loads(trozo.split("data: ", 1)[1]))
    return datos


def _comentario(pais="ARG", texto="Vamos"):
    return json.dumps({"tipo": "comentario", "comentario_id": "c1", "partido_id": "P-03", "pais": pais,
                       "usuario_nombre": "Ana", "contenido": texto, "creado_en": "2030-06-13T15:10:00+00:00",
                       "origen": "usuario", "enviado_en": 0})


def test_conectar_marca_presencia_y_desconectar_la_quita():
    async def caso():
        redis = RedisAsincronoFalso()
        transmision = Transmision(redis, _ajustes())
        salida = []
        tarea = asyncio.create_task(_escuchar(transmision, salida))
        await asyncio.sleep(0.05)
        assert list(redis.zsets["audiencia:P-03:ARG"]) == [miembro_de("token-ana")]
        assert "ARG" in redis.conjuntos["paises:P-03"]
        assert "U0000001" in redis.conjuntos["unicos:P-03:ARG"]
        tarea.cancel()
        await asyncio.gather(tarea, return_exceptions=True)
        assert redis.zsets["audiencia:P-03:ARG"] == {}
        assert transmision.conexiones == 0

    asyncio.run(caso())


def test_el_token_no_se_guarda_tal_cual():
    assert miembro_de("token-ana") != "token-ana" and len(miembro_de("token-ana")) == 16


def test_la_presencia_se_refresca_mientras_la_conexion_sigue_abierta():
    async def caso():
        redis = RedisAsincronoFalso()
        tarea = asyncio.create_task(_escuchar(Transmision(redis, _ajustes()), []))
        await asyncio.sleep(0.02)
        primera = redis.zsets["audiencia:P-03:ARG"][miembro_de("token-ana")]
        await asyncio.sleep(0.2)
        assert redis.zsets["audiencia:P-03:ARG"][miembro_de("token-ana")] > primera
        tarea.cancel()
        await asyncio.gather(tarea, return_exceptions=True)

    asyncio.run(caso())


def test_comentario_publicado_llega_solo_a_su_tribuna():
    async def caso():
        redis = RedisAsincronoFalso()
        transmision = Transmision(redis, _ajustes())
        arg, esp, esp_todos = [], [], []
        tareas = [asyncio.create_task(_escuchar(transmision, arg)),
                  asyncio.create_task(_escuchar(transmision, esp, "ESP", token="t-lola", usuario="U0000002")),
                  asyncio.create_task(_escuchar(transmision, esp_todos, "ESP", "todos", "t-pepe", "U0000003"))]
        await asyncio.sleep(0.05)
        redis.emitir("chat:P-03:ARG", _comentario())
        redis.emitir("chat:P-03:todos", _comentario())
        await asyncio.sleep(0.1)
        for tarea in tareas:
            tarea.cancel()
        await asyncio.gather(*tareas, return_exceptions=True)
        assert [c["contenido"] for c in _eventos(arg, "comentario")] == ["Vamos"]
        assert _eventos(esp, "comentario") == []
        assert [c["pais"] for c in _eventos(esp_todos, "comentario")] == ["ARG"]
        assert len(redis.suscripciones) == 1  # una sola suscripción por proceso, compartida

    asyncio.run(caso())


def test_estado_trae_la_audiencia_del_pais_del_espectador():
    async def caso():
        redis = RedisAsincronoFalso()
        salida = []
        tarea = asyncio.create_task(_escuchar(Transmision(redis, _ajustes()), salida, "ESP"))
        await asyncio.sleep(0.05)
        redis.emitir("estado:P-03", json.dumps({"tipo": "estado", "minuto": 23, "marcador": {"local": 1, "visitante": 0},
                                                "estado": "En juego", "audiencia": {"total": 5, "por_pais": {"ESP": 2, "ARG": 3}}}))
        await asyncio.sleep(0.1)
        tarea.cancel()
        await asyncio.gather(tarea, return_exceptions=True)
        assert _eventos(salida, "estado")[0]["minuto"] == 23
        assert _eventos(salida, "audiencia")[0] == {"total": 5, "mi_pais": 2, "pais": "ESP"}

    asyncio.run(caso())


def test_latido_mantiene_viva_la_conexion():
    async def caso():
        salida = []
        tarea = asyncio.create_task(_escuchar(Transmision(RedisAsincronoFalso(), _ajustes()), salida))
        await asyncio.sleep(0.35)
        tarea.cancel()
        await asyncio.gather(tarea, return_exceptions=True)
        assert sum(trozo.startswith(": latido") for trozo in salida) >= 2

    asyncio.run(caso())


def test_cola_llena_descarta_los_mas_viejos():
    cola = asyncio.Queue(maxsize=2)
    for n in range(4):
        Transmision.entregar(cola, n)
    assert [cola.get_nowait(), cola.get_nowait()] == [2, 3]


def test_redis_caido_cierra_la_conexion_con_aviso():
    async def caso():
        redis = RedisAsincronoFalso()
        redis.caida = True
        salida = []
        await _escuchar(Transmision(redis, _ajustes()), salida)
        assert _eventos(salida, "error")[0]["codigo"] == "DEPENDENCIA_NO_DISPONIBLE"

    asyncio.run(caso())


def test_sesion_invalida_da_401_sin_abrir_flujo(cliente):
    resp = cliente.get("/partidos/P-03/vivo", headers={"X-Sesion": "invalida"})
    assert resp.status_code == 401
    assert resp.json()["error"]["codigo"] == "NO_AUTORIZADO"
    assert not resp.headers["content-type"].startswith("text/event-stream")


def test_partido_inexistente_da_404(cliente):
    from tests.apoyo import entrar

    usuario = cliente.post("/usuarios", json={"nombre": "Ana", "pais": "ARG"}).json()["usuario"]["id"]
    assert cliente.get("/partidos/P-999/vivo", headers=entrar(cliente, usuario)).status_code == 404


def test_al_cortarse_la_conexion_sale_de_la_audiencia_aunque_la_cancelen_varias_veces():
    """Starlette corta el flujo con un ámbito de cancelación de anyio, que vuelve a cancelar en cada espera:
    la limpieza tiene que llegar igual a Redis (revisión final, hallazgo 2)."""
    import anyio

    async def caso():
        redis = RedisAsincronoFalso()
        transmision = Transmision(redis, _ajustes())
        async with anyio.create_task_group() as grupo:
            grupo.start_soon(_escuchar, transmision, [])
            await anyio.sleep(0.05)
            assert redis.zsets["audiencia:P-03:ARG"]
            grupo.cancel_scope.cancel()
        assert redis.zsets["audiencia:P-03:ARG"] == {}
        assert transmision.conexiones == 0

    asyncio.run(caso())


def test_quien_entra_mientras_otro_se_va_sigue_suscripto():
    """Uno se va (su desuscripción tarda) y otro entra al mismo canal: el que entra no puede quedar sin
    suscripción (revisión final, hallazgo 3)."""
    async def caso():
        redis = RedisAsincronoFalso()
        redis.demora_desuscribir = 0.05
        transmision = Transmision(redis, _ajustes())
        primero = asyncio.create_task(_escuchar(transmision, []))
        await asyncio.sleep(0.02)
        primero.cancel()
        await asyncio.sleep(0)  # el primero empezó a desuscribirse
        salida = []
        segundo = asyncio.create_task(_escuchar(transmision, salida, token="otro", usuario="U0000002"))
        await asyncio.sleep(0.15)
        redis.emitir("chat:P-03:ARG", _comentario(texto="llega"))
        await asyncio.sleep(0.1)
        segundo.cancel()
        await asyncio.gather(primero, segundo, return_exceptions=True)
        assert [c["contenido"] for c in _eventos(salida, "comentario")] == ["llega"]

    asyncio.run(caso())


def test_adaptador_traduce_los_errores_de_la_suscripcion():
    """El driver real lanza sus propias excepciones; el adaptador las traduce (revisión final, hallazgo 4)."""
    import redis as driver

    from app.adapters.redis import RedisAdapter
    from app.errors import DependenciaNoDisponible

    class PubSubCaido:
        async def subscribe(self, *canales):
            raise driver.exceptions.ConnectionError("sin conexión")

    async def caso():
        try:
            await RedisAdapter(Settings(_env_file=None)).asuscribir(PubSubCaido(), "chat:P-03:ARG")
        except DependenciaNoDisponible:
            return "traducido"

    assert asyncio.run(caso()) == "traducido"
