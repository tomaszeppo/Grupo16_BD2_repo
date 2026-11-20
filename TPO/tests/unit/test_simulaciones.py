from datetime import datetime, timezone
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


def test_simulacion_escribe_antes_de_iniciar_y_finaliza(monkeypatch):
    acciones = []
    col = Mock()
    mongo = SimpleNamespace(db=SimpleNamespace(simulaciones=col, jugadores=PlantelFalso()))
    partido = {"id":"P-03", "fase": "Fase de grupos", "local": {"codigo": "ARG"}, "visitante": {"codigo": "BRA"}}
    admin = SimpleNamespace(_partido=lambda id: partido, poner_en_juego=lambda id: acciones.append("iniciar") or partido)
    monkeypatch.setattr(simulaciones, "obtener_o_crear", lambda *args: {"jugadas":[{"tipo":"Gol", "minuto":23, "equipo_id":"ARG", "jugador":"J-ARG-09"},{"tipo":"Gol", "minuto":75, "equipo_id":"BRA", "jugador":"J-BRA-09"}]})
    puntuacion = SimpleNamespace(cerrar=Mock(), ejecutar=Mock())
    monkeypatch.setattr(simulaciones, "escribir", lambda id, pais, minuto, *args: acciones.append((pais, minuto)))
    monkeypatch.setattr(simulaciones, "_influx", lambda: SimpleNamespace(guardar_jugadores=lambda *args: None))
    monkeypatch.setattr(simulaciones.time, "sleep", lambda n: None)
    simulaciones._ejecutar("P-03", mongo, admin, puntuacion)
    assert acciones[:5] == [("ARG", 0), ("BRA", 0), ("ESP", 0), ("URU", 0), "iniciar"]
    puntuacion.cerrar.assert_called_once_with("P-03", 1, 1, None)
    puntuacion.ejecutar.assert_called_once_with("P-03")
    assert col.update_one.call_args_list[-1].args[1]["$set"]["estado_simulacion"] == "completa"


def test_falla_de_comentarios_marca_error_sin_iniciar(monkeypatch):
    col = Mock()
    mongo = SimpleNamespace(db=SimpleNamespace(simulaciones=col))
    admin = SimpleNamespace(_partido=lambda id: {"id":"P-03"}, poner_en_juego=Mock())
    monkeypatch.setattr(simulaciones, "obtener_o_crear", lambda *args: {"jugadas":[]})
    def fallar(*args): raise RuntimeError("fallo")
    monkeypatch.setattr(simulaciones, "escribir", fallar)
    simulaciones._ejecutar("P-03", mongo, admin, Mock())
    admin.poner_en_juego.assert_not_called()
    assert col.update_one.call_args.args[1]["$set"]["estado_simulacion"] == "fallida"


def test_comentarios_de_gol_usan_textos_de_gol(monkeypatch):
    guardados = []
    servicio = SimpleNamespace(publicar_automatico=lambda *args: guardados.append(args))
    monkeypatch.setattr(simulaciones, "_comentarios", lambda: servicio)
    monkeypatch.setattr(simulaciones.random, "choice", lambda opciones: opciones[0])
    simulaciones.escribir("P-03", "ARG", 23)
    assert guardados[0][:2] == ("P-03", "ARG")
    assert guardados[0][3] in simulaciones.GOLES
    assert len(simulaciones.COMENTARIOS) >= 10


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


def test_simulacion_respeta_gol_definido_en_guion(monkeypatch):
    col = Mock()
    mongo = SimpleNamespace(db=SimpleNamespace(simulaciones=col, jugadores=PlantelFalso()))
    partido = {"id":"P-03", "fase":"Fase de grupos", "local":{"codigo":"ARG"}, "visitante":{"codigo":"BRA"}}
    admin = SimpleNamespace(_partido=lambda _:partido, poner_en_juego=lambda _:partido)
    goles = [{"tipo":"Gol", "minuto":42, "equipo_id":"ARG", "jugador":"J-ARG-09"}]
    monkeypatch.setattr(simulaciones, "obtener_o_crear", lambda *args:{"jugadas":goles})
    monkeypatch.setattr(simulaciones, "escribir", lambda *args:None)
    monkeypatch.setattr(simulaciones, "archivar_estadisticas", lambda *args:None)
    monkeypatch.setattr(simulaciones.time, "sleep", lambda _:None)
    influx = SimpleNamespace(guardar_jugadores=Mock())
    monkeypatch.setattr(simulaciones, "_influx", lambda:influx)
    puntuacion = SimpleNamespace(cerrar=Mock(), ejecutar=Mock())
    simulaciones._ejecutar("P-03", mongo, admin, puntuacion)
    puntuacion.cerrar.assert_called_once_with("P-03", 1, 0, None)
    muestra_42 = influx.guardar_jugadores.call_args_list[42].args
    assert muestra_42[1] == 42 and muestra_42[3][0]["jugador"] == "J-ARG-09"


def test_simulacion_comenta_en_los_paises_que_miran_y_cierra_cada_minuto(monkeypatch, sin_redis):
    sin_redis.paises.add("JPN")
    acciones = []
    col = Mock()
    mongo = SimpleNamespace(db=SimpleNamespace(simulaciones=col, jugadores=PlantelFalso()))
    partido = {"id": "P-03", "fase": "Fase de grupos", "local": {"codigo": "ARG"}, "visitante": {"codigo": "BRA"}}
    admin = SimpleNamespace(_partido=lambda _: partido, poner_en_juego=lambda _: partido)
    monkeypatch.setattr(simulaciones, "obtener_o_crear", lambda *args: {"jugadas": []})
    monkeypatch.setattr(simulaciones, "escribir", lambda id, pais, minuto, *args: acciones.append((pais, minuto)))
    monkeypatch.setattr(simulaciones, "_influx", lambda: SimpleNamespace(guardar_jugadores=lambda *args: None))
    monkeypatch.setattr(simulaciones, "archivar_estadisticas", lambda *args: None)
    monkeypatch.setattr(simulaciones.time, "sleep", lambda _: None)
    simulaciones._ejecutar("P-03", mongo, admin, SimpleNamespace(cerrar=Mock(), ejecutar=Mock()), tipo="carga")
    assert ("JPN", 0) in acciones and ("JPN", 45) in acciones
    assert [m for m, _, _ in sin_redis.minutos] == list(range(91))
    assert {t for _, t, _ in sin_redis.minutos} == {"carga"}
    assert sin_redis.finales == [("carga", {"local": 0, "visitante": 0})]


def test_audiencia_incompleta_queda_marcada(monkeypatch, sin_redis):
    sin_redis.cerrar_minuto = lambda *args: {"incompleto": True}
    col = Mock()
    mongo = SimpleNamespace(db=SimpleNamespace(simulaciones=col, jugadores=PlantelFalso()))
    partido = {"id": "P-03", "fase": "Fase de grupos", "local": {"codigo": "ARG"}, "visitante": {"codigo": "BRA"}}
    admin = SimpleNamespace(_partido=lambda _: partido, poner_en_juego=lambda _: partido)
    monkeypatch.setattr(simulaciones, "obtener_o_crear", lambda *args: {"jugadas": []})
    monkeypatch.setattr(simulaciones, "escribir", lambda *args: None)
    monkeypatch.setattr(simulaciones, "_influx", lambda: SimpleNamespace(guardar_jugadores=lambda *args: None))
    monkeypatch.setattr(simulaciones, "archivar_estadisticas", lambda *args: None)
    monkeypatch.setattr(simulaciones.time, "sleep", lambda _: None)
    simulaciones._ejecutar("P-03", mongo, admin, SimpleNamespace(cerrar=Mock(), ejecutar=Mock()))
    marcas = [c.args[1]["$set"] for c in col.update_one.call_args_list if "audiencia_incompleta" in c.args[1].get("$set", {})]
    assert marcas and col.update_one.call_args_list[-1].args[1]["$set"]["estado_simulacion"] == "completa"


def test_redis_caido_a_mitad_del_partido_no_corta_la_simulacion(monkeypatch):
    """Con los servicios reales (no reemplazados): el comentario automático se guarda en Cassandra aunque
    Redis no pueda repartirlo, la audiencia queda marcada incompleta y el partido termina (revisión final, hallazgo 1)."""
    from app.config.settings import Settings
    from app.services.audiencia import Audiencia
    from app.services.comentarios import ComentariosService
    from tests.falsos import CassandraFalso, RedisFalso

    redis, cassandra = RedisFalso(), CassandraFalso()
    redis.caida = True
    servicio = ComentariosService(cassandra, redis, None, None, lambda: datetime.now(timezone.utc), 5.0)
    influx = SimpleNamespace(guardar_jugadores=lambda *a: None, guardar_audiencia=lambda *a: None,
                             guardar_resumen_audiencia=lambda *a: None)
    monkeypatch.setattr(simulaciones, "_audiencia", lambda: Audiencia(redis, influx, Settings(_env_file=None)))
    monkeypatch.setattr(simulaciones, "_comentarios", lambda: servicio)
    monkeypatch.setattr(simulaciones, "_influx", lambda: influx)
    monkeypatch.setattr(simulaciones, "archivar_estadisticas", lambda *args: None)
    monkeypatch.setattr(simulaciones, "obtener_o_crear", lambda *args: {"jugadas": []})
    monkeypatch.setattr(simulaciones.time, "sleep", lambda _: None)
    col = Mock()
    mongo = SimpleNamespace(db=SimpleNamespace(simulaciones=col, jugadores=PlantelFalso()))
    partido = {"id": "P-03", "fase": "Fase de grupos", "local": {"codigo": "ARG"}, "visitante": {"codigo": "BRA"}}
    admin = SimpleNamespace(_partido=lambda _: partido, poner_en_juego=lambda _: partido)
    simulaciones._ejecutar("P-03", mongo, admin, SimpleNamespace(cerrar=Mock(), ejecutar=Mock()))
    cambios = [c.args[1]["$set"] for c in col.update_one.call_args_list]
    assert cambios[-1]["estado_simulacion"] == "completa"
    assert any(c.get("audiencia_incompleta") for c in cambios)
    assert len(cassandra.filas) == 4 * 90  # los comentarios automáticos se guardaron igual
