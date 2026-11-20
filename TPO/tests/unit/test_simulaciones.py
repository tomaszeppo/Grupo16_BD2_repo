from datetime import datetime, timedelta, timezone
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


def test_simulador_genera_datos_por_http(monkeypatch):
    col = Mock()
    mongo = SimpleNamespace(db=SimpleNamespace(simulaciones=col, jugadores=PlantelFalso()))
    partido = {"id":"P-03", "fase":"Fase de grupos", "local":{"codigo":"ARG"}, "visitante":{"codigo":"BRA"}}
    admin = SimpleNamespace(_partido=lambda _: partido)
    monkeypatch.setattr(simulaciones, "obtener_o_crear", lambda *args: {"jugadas": [{"tipo":"Gol", "minuto":42, "equipo_id":"ARG", "jugador":"J-ARG-09"}]})
    monkeypatch.setattr(simulaciones, "get_settings", lambda: SimpleNamespace(simulador_api_url="http://api", admin_clave="clave", influx_raw_db="fixture2030_raw", simulador_comentarios_por_region_segundo=4))
    monkeypatch.setattr(simulaciones.time, "sleep", lambda _: None)
    pedidos = []
    class Cliente:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def put(self, url, **kwargs):
            pedidos.append((url, kwargs))
            return SimpleNamespace(status_code=201, raise_for_status=lambda: None)
        def post(self, url, **kwargs):
            pedidos.append((url, kwargs))
            if url == "/administracion/hinchas-demo": body = {"usuarios": {p:[f"U{n:07d}"] for n,p in enumerate(("ARG", "BRA", "ESP", "URU"),1)}}
            elif url.endswith("/estado"): body = {"partido":partido}
            elif url.endswith("/muestras"):
                body = {"marcador":{"local": int(kwargs["json"]["minuto"] >= 42), "visitante":0}}
            else: body = {}
            return SimpleNamespace(raise_for_status=lambda: None, json=lambda: body)
    monkeypatch.setattr(simulaciones.httpx, "Client", Cliente)
    simulaciones._ejecutar("P-03", mongo, admin, Mock())
    assert sum(url.endswith("/muestras") for url, _ in pedidos) == 91
    comentarios = [(url, kw) for url, kw in pedidos if url.endswith("/comentarios")]
    assert len(comentarios) == 1440 and all("X-Usuario-Id" in kw["headers"] for _, kw in comentarios)
    primeros_ocho = []
    for url, kw in pedidos:
        if url.endswith("/muestras") and kw["json"]["minuto"] == 8:
            break
        if url.endswith("/comentarios"):
            primeros_ocho.append(kw)
    assert len(primeros_ocho) == 128  # 32 por región durante los primeros 8 segundos
    assert next(kw["json"] for url, kw in pedidos if url.endswith("/resultado"))["goles_local"] == 1
    assert col.update_one.call_args.args[1]["$set"]["estado_simulacion"] == "completa"


def test_registrar_muestra_usa_datos_de_la_corrida():
    inicio = datetime(2026, 1, 1, tzinfo=timezone.utc)
    col = Mock()
    col.find_one.return_value = {"estado_simulacion":"en_curso", "partido":{"local":{"codigo":"ARG"}, "visitante":{"codigo":"BRA"}},
        "jugadas":[{"tipo":"Gol", "minuto":42, "equipo_id":"ARG"}], "plantel_estadisticas":{}, "inicio_estadisticas":inicio, "corrida_id":"abc"}
    mongo = SimpleNamespace(db=SimpleNamespace(simulaciones=col))
    influx = SimpleNamespace(guardar_jugadores=Mock())
    respuesta = simulaciones.registrar_muestra("P-03", simulaciones.MinutoSimulado(minuto=42), mongo, influx)
    assert respuesta["marcador"] == {"local":1, "visitante":0}
    assert influx.guardar_jugadores.call_args.args[4] == inicio + timedelta(seconds=42)


def test_endpoint_muestras_exige_administrador_y_valida_minuto(cliente):
    ruta = "/administracion/simulaciones/P-03/muestras"
    assert cliente.post(ruta, json={"minuto": 1}).status_code == 401
    headers = {"X-Admin-Clave": "clave-de-prueba"}
    assert cliente.post(ruta, headers=headers, json={"minuto": 91}).status_code == 422


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


def test_historial_recorre_paginas_y_ventanas_sin_perder_comentarios(monkeypatch):
    from datetime import datetime, timezone
    from types import SimpleNamespace
    inicio = datetime(2026, 1, 1, 12, 29, tzinfo=timezone.utc)
    fin = datetime(2026, 1, 1, 13, 1, tzinfo=timezone.utc)
    doc = {"inicio_comentarios":inicio, "fin_comentarios":fin}
    neo = SimpleNamespace(obtener_partido=lambda _: {"estado":"Finalizado"})
    mongo = SimpleNamespace(db=SimpleNamespace(simulaciones=SimpleNamespace(find_one=lambda _:doc)), obtener_resultado=lambda _:None)
    llamadas=[]
    class Sesion:
        def execute(self, sentencia, params, paging_state=None):
            llamadas.append((params[2], paging_state))
            valor = len(llamadas)
            fila = SimpleNamespace(comentario_id=str(valor), usuario_nombre="Ana", contenido=f"mensaje {valor}", creado_en=fin)
            return SimpleNamespace(current_rows=[fila], has_more_pages=valor == 2, paging_state=b"p2" if valor == 2 else None)
    monkeypatch.setattr(simulaciones, "cassandra", lambda:Sesion())
    cursor = None; recibidos=[]
    for _ in range(4):
        pagina = simulaciones.historial_comentarios("P-03", "ARG", cursor, mongo, neo)
        recibidos.extend(p["contenido"] for p in pagina["items"])
        cursor = pagina["next_cursor"]
    assert recibidos == ["mensaje 1", "mensaje 2", "mensaje 3", "mensaje 4"]
    assert [x[0].minute for x in llamadas] == [0, 30, 30, 0]
    assert llamadas[2][1] == b"p2"
    assert cursor is None


def test_historial_rechaza_cursor_fuera_del_partido():
    import pytest
    from datetime import datetime, timezone
    from types import SimpleNamespace
    from app.errors import ValidacionError
    fecha = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    mongo = SimpleNamespace(db=SimpleNamespace(simulaciones=SimpleNamespace(find_one=lambda _:{"inicio_comentarios":fecha,"fin_comentarios":fecha})), obtener_resultado=lambda _:None)
    neo = SimpleNamespace(obtener_partido=lambda _:{"estado":"Finalizado"})
    cursor = simulaciones._cursor_comentarios(fecha - timedelta(hours=1), partido_id="P-03", pais="ARG")
    with pytest.raises(ValidacionError): simulaciones.historial_comentarios("P-03", "ARG", cursor, mongo, neo)
