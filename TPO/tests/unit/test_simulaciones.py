from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from app.routes import simulaciones


def test_recientes_consulta_ventanas_y_limita_por_region(monkeypatch):
    llamadas = []
    fila = SimpleNamespace(comentario_id="abc", usuario_nombre="Ana", contenido="gol", creado_en=datetime.now(timezone.utc))
    class Session:
        def execute(self, query, params):
            llamadas.append(params)
            return [fila] if len(llamadas) == 1 else []
    monkeypatch.setattr(simulaciones, "cassandra", lambda: Session())
    resultado = simulaciones.recientes("P-03", "ARG")
    assert resultado["items"][0]["contenido"] == "gol"
    assert all(p[:2] == ("P-03", "ARG") for p in llamadas)
    assert len(llamadas) == 2
    assert (llamadas[0][2] - llamadas[1][2]).total_seconds() == 1800


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


def test_endpoint_fastapi_filtra_pais(cliente, monkeypatch):
    llamadas = []
    class Session:
        def execute(self, query, params):
            llamadas.append(params)
            return []
    monkeypatch.setattr(simulaciones, "cassandra", lambda: Session())
    respuesta = cliente.get("/partidos/P-03/comentarios/recientes?pais=ARG")
    assert respuesta.status_code == 200
    assert respuesta.json()["pais"] == "ARG"
    assert respuesta.json()["items"] == []
    assert all(p[:2] == ("P-03", "ARG") for p in llamadas)
    assert cliente.get("/partidos/P-03/comentarios/recientes?pais=arg").status_code == 422


def test_comentar_usa_usuario_y_region_de_sesion(cliente, monkeypatch):
    guardados = []
    def guardar(partido, pais, nombre, contenido):
        guardados.append((partido, pais, nombre, contenido))
        return {"comentario_id":"c1", "usuario_nombre":nombre, "contenido":contenido, "creado_en":"2026-01-01T00:00:00Z"}
    monkeypatch.setattr(simulaciones, "guardar_comentario", guardar)
    usuario = cliente.post("/usuarios", json={"nombre":"Ana", "pais":"ARG"}).json()["usuario"]
    headers = {"X-Usuario-Id":usuario["id"]}
    assert cliente.post("/partidos/P-03/comentarios", headers=headers, json={"contenido":"hola"}).status_code == 409
    assert cliente.post("/partidos/P-03/estado", headers={"X-Admin-Clave":"clave-de-prueba"}, json={"estado":"En juego"}).status_code == 200
    respuesta = cliente.post("/partidos/P-03/comentarios", headers=headers, json={"contenido":"  Vamos!  "})
    assert respuesta.status_code == 201
    assert guardados == [("P-03", "ARG", "Ana", "Vamos!")]
    assert cliente.post("/partidos/P-03/comentarios", headers=headers, json={"contenido":"   "}).status_code == 422
    assert cliente.post("/partidos/P-03/comentarios", json={"contenido":"hola"}).status_code == 401
    assert cliente.post("/partidos/P-03/comentarios", headers=headers, json={"contenido":"hola", "pais":"BRA"}).status_code == 422


def test_comentarios_de_gol_usan_textos_de_gol(monkeypatch):
    guardados = []
    monkeypatch.setattr(simulaciones, "guardar_comentario", lambda *args: guardados.append(args))
    monkeypatch.setattr(simulaciones.random, "choice", lambda opciones: opciones[0])
    simulaciones.escribir("P-03", "ARG", 23)
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
