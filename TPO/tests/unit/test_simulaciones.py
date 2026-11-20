from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.routes import simulaciones


class AudienciaQueAnota:
    def __init__(self, paises=("ARG", "BRA", "ESP", "URU")):
        self.paises, self.minutos, self.finales = set(paises), [], []

    def paises_de(self, partido_id):
        return set(self.paises)

    def cerrar_minuto(self, partido_id, minuto, corrida_id, tipo, instante, marcador, estado):
        self.minutos.append((minuto, tipo, marcador))
        return {}

    def cerrar_partido(self, partido_id, corrida_id, tipo, instante, marcador=None):
        self.finales.append((tipo, marcador))


@pytest.fixture(autouse=True)
def sin_redis(monkeypatch):
    audiencia = AudienciaQueAnota()
    monkeypatch.setattr(simulaciones, "_audiencia", lambda: audiencia)
    return audiencia


class PlantelFalso:
    def find(self, filtro, proyeccion):
        equipo = filtro["equipo"]
        class Cursor:
            def sort(self, campo, orden):
                return [{"_id": f"J-{equipo}-{n:02d}", "dorsal": n} for n in range(1, 27)]
        return Cursor()


class ClienteFalso:
    """La API vista por el simulador: anota cada pedido y responde lo mínimo. `fallar` decide qué rutas fallan."""

    def __init__(self, partido, fallar=lambda url: False):
        self.partido, self.fallar, self.pedidos = partido, fallar, []
        self.cookies = SimpleNamespace(clear=lambda: None)

    def __call__(self, **kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def put(self, url, **kwargs):
        self.pedidos.append((url, kwargs))
        return SimpleNamespace(status_code=201, raise_for_status=lambda: None)

    def post(self, url, **kwargs):
        self.pedidos.append((url, kwargs))
        if self.fallar(url):
            import httpx
            def error():
                raise httpx.HTTPStatusError("falla", request=None, response=None)
            return SimpleNamespace(status_code=503, raise_for_status=error, json=lambda: {})
        if url == "/administracion/hinchas-demo":
            cantidad = kwargs["json"]["cantidad"]
            body = {"usuarios": {p: [f"{p}{n:02d}" for n in range(cantidad)] for p in kwargs["json"]["paises"]}}
        elif url == "/sesiones":
            body = {"token": "t-" + kwargs["json"]["usuario_id"]}
        elif url.endswith("/estado"):
            body = {"partido": self.partido}
        elif url.endswith("/muestras"):
            body = {"marcador": {"local": int(kwargs["json"]["minuto"] >= 42), "visitante": 0}}
        else:
            body = {}
        return SimpleNamespace(status_code=201, raise_for_status=lambda: None, json=lambda: body)


def _simular(monkeypatch, fallar=lambda url: False, paises=("ARG", "BRA", "ESP", "URU")):
    col = Mock()
    mongo = SimpleNamespace(db=SimpleNamespace(simulaciones=col, jugadores=PlantelFalso()))
    partido = {"id": "P-03", "fase": "Fase de grupos", "local": {"codigo": "ARG"}, "visitante": {"codigo": "BRA"}}
    monkeypatch.setattr(simulaciones, "obtener_o_crear", lambda *args: {"jugadas": [{"tipo": "Gol", "minuto": 42, "equipo_id": "ARG", "jugador": "J-ARG-09"}]})
    monkeypatch.setattr(simulaciones, "get_settings", lambda: SimpleNamespace(simulador_api_url="http://api", admin_clave="clave", influx_raw_db="fixture2030_raw", simulador_comentarios_por_region_segundo=4))
    monkeypatch.setattr(simulaciones.time, "sleep", lambda _: None)
    simulaciones._audiencia().paises = set(paises)
    cliente = ClienteFalso(partido, fallar)
    monkeypatch.setattr(simulaciones.httpx, "Client", cliente)
    simulaciones._ejecutar("P-03", mongo, SimpleNamespace(_partido=lambda _: partido), Mock(), tipo="carga")
    return cliente.pedidos, col


def test_simulador_maneja_el_partido_por_la_api_con_hinchas_con_sesion(monkeypatch, sin_redis):
    pedidos, col = _simular(monkeypatch)
    assert sum(url.endswith("/muestras") for url, _ in pedidos) == 91
    comentarios = [kw for url, kw in pedidos if url.endswith("/comentarios")]
    assert len(comentarios) == 90 * 4 * 4  # 90 minutos, 4 países, 4 por segundo
    assert all(kw["headers"]["X-Sesion"].startswith("t-") and kw["json"]["comentario_id"] for kw in comentarios)
    assert len({kw["json"]["comentario_id"] for kw in comentarios}) == len(comentarios)
    pronosticos = [kw for url, kw in pedidos if url.endswith("/pronostico")]
    assert pronosticos and all("X-Sesion" in kw["headers"] for kw in pronosticos)
    assert next(kw["json"] for url, kw in pedidos if url.endswith("/resultado"))["goles_local"] == 1
    assert sin_redis.finales == [("carga", {"local": 1, "visitante": 0})]
    assert col.update_one.call_args.args[1]["$set"]["estado_simulacion"] == "completa"


def test_ningun_hincha_comenta_antes_del_modo_lento(monkeypatch, sin_redis):
    """Con 4 comentarios por segundo y país, cada hincha tiene que esperar más de 5 s entre uno y otro."""
    pedidos, _ = _simular(monkeypatch)
    segundo, ultimo = -1, {}
    for url, kw in pedidos:
        if url.endswith("/muestras"):
            segundo = kw["json"]["minuto"]
        elif url.endswith("/comentarios"):
            hincha = kw["headers"]["X-Sesion"]
            assert segundo - ultimo.get(hincha, -99) > 5, f"{hincha} comentó a los {segundo - ultimo[hincha]} s"
            ultimo[hincha] = segundo


def test_los_hinchas_tambien_son_de_los_paises_que_miran(monkeypatch, sin_redis):
    pedidos, _ = _simular(monkeypatch, paises=("ARG", "BRA", "ESP", "URU", "JPN"))
    pedido = next(kw["json"] for url, kw in pedidos if url == "/administracion/hinchas-demo")
    assert "JPN" in pedido["paises"] and pedido["cantidad"] == simulaciones.HINCHAS_POR_PAIS


def test_en_el_minuto_del_gol_se_comenta_el_gol(monkeypatch, sin_redis):
    pedidos, _ = _simular(monkeypatch)
    segundo = -1
    for url, kw in pedidos:
        if url.endswith("/muestras"):
            segundo = kw["json"]["minuto"]
        elif url.endswith("/comentarios") and segundo == 42:
            assert kw["json"]["contenido"] in simulaciones.GOLES


def test_comentarios_y_minutos_que_fallan_no_cortan_el_partido(monkeypatch, sin_redis):
    """Redis o Cassandra caídos a mitad del partido: la API responde 503 a comentarios y minutos, y el partido
    termina igual, marcado como incompleto (revisión final, hallazgo 1, con el simulador por la API)."""
    pedidos, col = _simular(monkeypatch, fallar=lambda url: url.endswith("/comentarios") or url.endswith("/muestras"))
    cambios = [c.args[1]["$set"] for c in col.update_one.call_args_list]
    assert cambios[-1]["estado_simulacion"] == "completa"
    assert any(c.get("comentarios_incompletos") for c in cambios)
    assert any(c.get("audiencia_incompleta") for c in cambios)
    assert next(kw["json"] for url, kw in pedidos if url.endswith("/resultado"))["goles_local"] == 1


def test_registrar_muestra_usa_datos_de_la_corrida_y_cierra_la_audiencia(sin_redis):
    inicio = datetime(2026, 1, 1, tzinfo=timezone.utc)
    col = Mock()
    col.find_one.return_value = {"estado_simulacion": "en_curso", "tipo": "demo", "partido": {"local": {"codigo": "ARG"}, "visitante": {"codigo": "BRA"}},
        "jugadas": [{"tipo": "Gol", "minuto": 42, "equipo_id": "ARG"}], "plantel_estadisticas": {}, "inicio_estadisticas": inicio, "corrida_id": "abc"}
    mongo = SimpleNamespace(db=SimpleNamespace(simulaciones=col))
    influx = SimpleNamespace(guardar_jugadores=Mock())
    respuesta = simulaciones.registrar_muestra("P-03", simulaciones.MinutoSimulado(minuto=42), mongo, influx)
    assert respuesta["marcador"] == {"local": 1, "visitante": 0}
    assert influx.guardar_jugadores.call_args.args[4] == inicio + timedelta(seconds=42)
    assert sin_redis.minutos == [(42, "demo", {"local": 1, "visitante": 0})]


def test_registrar_muestra_con_influx_caido_marca_y_sigue(sin_redis):
    col = Mock()
    col.find_one.return_value = {"estado_simulacion": "en_curso", "partido": {"local": {"codigo": "ARG"}, "visitante": {"codigo": "BRA"}},
        "jugadas": [], "plantel_estadisticas": {}, "inicio_estadisticas": datetime(2026, 1, 1, tzinfo=timezone.utc), "corrida_id": "abc"}
    mongo = SimpleNamespace(db=SimpleNamespace(simulaciones=col))
    def caer(*args):
        raise RuntimeError("influx caído")
    respuesta = simulaciones.registrar_muestra("P-03", simulaciones.MinutoSimulado(minuto=5), mongo,
                                               SimpleNamespace(guardar_jugadores=caer))
    assert respuesta["minuto"] == 5
    assert col.update_one.call_args.args[1]["$set"]["estadisticas_incompletas"] is True
    assert sin_redis.minutos  # la audiencia del minuto se cerró igual


def test_endpoint_muestras_exige_administrador_y_valida_minuto(cliente):
    ruta = "/administracion/simulaciones/P-03/muestras"
    assert cliente.post(ruta, json={"minuto": 1}).status_code == 401
    headers = {"X-Admin-Clave": "clave-de-prueba"}
    assert cliente.post(ruta, headers=headers, json={"minuto": 91}).status_code == 422


def preparar_archivo():
    partido = {"local":{"codigo":"ARG"}, "visitante":{"codigo":"BRA"}}
    documento = {"estado":"Finalizado", "partido":partido, "marcador":{"local":1, "visitante":1},
                 "jugadas":[{"id":"SIM-P-03-001", "tipo":"Gol", "minuto":23, "orden":1, "equipo_id":"ARG", "jugador":"J-ARG-09", "influido_por":[]},
                            {"id":"SIM-P-03-002", "tipo":"Gol", "minuto":75, "orden":2, "equipo_id":"BRA", "jugador":"J-BRA-09", "influido_por":[]}]}
    col = Mock(); col.find_one.return_value = documento
    mongo = SimpleNamespace(db=SimpleNamespace(simulaciones=col))
    campos = {"posesion_pct":50.0,"tiros":0,"tiros_arco":0,"pases_completados":1,"pases_intentados":1,"faltas":0,"corners":0,"time":"2026-01-01T00:00:00Z"}
    muestras = [{**campos,"equipo_id":equipo,"minuto":minuto,"goles":int(minuto == (23 if equipo == "ARG" else 75)), "tiros":int(minuto == (23 if equipo == "ARG" else 75))}
                for equipo in ("ARG","BRA") for minuto in range(91)]
    influx = SimpleNamespace(muestras_partido=Mock(return_value=muestras), resumen_partido=Mock(return_value=[{"equipo_id":"ARG"},{"equipo_id":"BRA"}]))
    return mongo, col, Mock(), influx


def test_archivar_requiere_muestras_completas_y_guarda_en_neo():
    mongo, col, neo, influx = preparar_archivo()
    resultado = simulaciones.archivar_estadisticas("P-03", mongo, neo, influx)
    assert resultado["muestras"] == 182
    neo.archivar_estadisticas.assert_called_once()
    assert col.update_one.call_args.args[1]["$set"]["archivo_estado"] == "completo"


def test_archivar_no_guarda_si_falta_un_minuto(monkeypatch):
    import pytest
    from app.errors import Conflicto
    mongo, col, neo, influx = preparar_archivo()
    influx.muestras_partido.return_value.pop()
    monkeypatch.setattr(simulaciones.time, "sleep", lambda _: None)
    with pytest.raises(Conflicto): simulaciones.archivar_estadisticas("P-03", mongo, neo, influx)
    neo.archivar_estadisticas.assert_not_called()


def test_archivar_rechaza_marcador_inconsistente():
    import pytest
    from app.errors import Conflicto
    mongo, col, neo, influx = preparar_archivo()
    mongo.db.simulaciones.find_one.return_value["marcador"]["local"] = 2
    with pytest.raises(Conflicto): simulaciones.archivar_estadisticas("P-03", mongo, neo, influx)
    neo.archivar_estadisticas.assert_not_called()


def test_archivar_rechaza_gol_en_minuto_distinto():
    import pytest
    from app.errors import Conflicto
    mongo, col, neo, influx = preparar_archivo()
    mongo.db.simulaciones.find_one.return_value["jugadas"][0]["minuto"] = 24
    with pytest.raises(Conflicto, match="no coinciden"):
        simulaciones.archivar_estadisticas("P-03", mongo, neo, influx)
    neo.archivar_estadisticas.assert_not_called()


def test_archivar_rechaza_id_duplicado():
    import pytest
    from app.errors import Conflicto
    mongo, col, neo, influx = preparar_archivo()
    jugadas = mongo.db.simulaciones.find_one.return_value["jugadas"]
    jugadas[1]["id"] = jugadas[0]["id"]
    with pytest.raises(Conflicto, match="duplicadas"):
        simulaciones.archivar_estadisticas("P-03", mongo, neo, influx)
    neo.archivar_estadisticas.assert_not_called()
