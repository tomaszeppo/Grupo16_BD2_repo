from datetime import datetime, timezone
from unittest.mock import Mock
import httpx
import pytest
from app.adapters.influx import InfluxAdapter
from app.config.settings import Settings
from app.errors import Conflicto
from app.routes.simulaciones import _agregar_equipos, _validar_jugadores


def test_lote_por_jugador_usa_ids_y_guion():
    requests = []
    adapter = InfluxAdapter(Settings(_env_file=None))
    adapter._http = httpx.Client(base_url='http://influx', transport=httpx.MockTransport(lambda req: requests.append(req) or httpx.Response(204)))
    plantel = {'ARG': ['J-ARG-09', 'J-ARG-08'], 'BRA': ['J-BRA-09']}
    jugadas = [{'minuto': 23, 'jugador': 'J-ARG-09', 'tipo': 'Gol'}]
    adapter.guardar_jugadores('P-03', 23, plantel, jugadas, datetime(2026, 1, 1, tzinfo=timezone.utc))
    lineas = requests[0].content.decode().splitlines()
    assert len(lineas) == 3
    assert 'jugador_id=J-ARG-09' in lineas[0]
    assert 'tiros=1i,tiros_arco=1i,goles=1i' in lineas[0]
    assert sum(int(line.split('posesion_segundos=')[1].split('i')[0]) for line in lineas) == 60


def test_agregacion_suma_y_calcula_posesion_ponderada():
    base = dict(pases_intentados=2, pases_completados=1, tiros=1, tiros_arco=1, goles=1, faltas=0, corners=0)
    filas = [dict(base, equipo_id='ARG', minuto=1, posesion_segundos=40), dict(base, equipo_id='BRA', minuto=1, posesion_segundos=20)]
    equipos = {e['equipo_id']: e for e in _agregar_equipos(filas)}
    assert equipos['ARG']['posesion_pct'] == pytest.approx(100 * 40 / 60)
    assert equipos['BRA']['pases_completados'] == 1
    assert filas[0]['posesion_pct'] == pytest.approx(100 * 40 / 60)


def test_archivo_rechaza_jugador_faltante():
    doc = {'plantel_estadisticas': {'ARG': ['J-ARG-09']}, 'jugadas': []}
    with pytest.raises(Conflicto, match='Faltan muestras'):
        _validar_jugadores(doc, [])


def test_cierre_version_jugador_valida_y_archiva_agregados():
    from types import SimpleNamespace
    from app.routes.simulaciones import archivar_estadisticas
    plantel = {'ARG': ['J-ARG-09'], 'BRA': ['J-BRA-09']}
    jugadas = [{'id':'SIM-P-03-001', 'tipo':'Gol', 'minuto':23, 'orden':1,
                 'equipo_id':'ARG', 'jugador':'J-ARG-09', 'influido_por':[]}]
    doc = {'estadisticas_version':2, 'estado':'Finalizado', 'plantel_estadisticas':plantel,
           'partido':{'local':{'codigo':'ARG'},'visitante':{'codigo':'BRA'}},
           'marcador':{'local':1,'visitante':0}, 'jugadas':jugadas}
    col = Mock(); col.find_one.return_value = doc
    mongo = SimpleNamespace(db=SimpleNamespace(simulaciones=col))
    muestras = []
    for equipo, jugadores in plantel.items():
        for minuto in range(91):
            gol = int(equipo == 'ARG' and minuto == 23)
            muestras.append({'equipo_id':equipo, 'jugador_id':jugadores[0], 'minuto':minuto,
                'pases_intentados':0, 'pases_completados':0, 'tiros':gol, 'tiros_arco':gol,
                'goles':gol, 'faltas':0, 'corners':0, 'posesion_segundos':0 if minuto == 0 else 30})
    minutos = [{k:v for k,v in f.items() if k != 'jugador_id'} for f in muestras]
    jugadores = [{'equipo_id':'ARG','jugador_id':'J-ARG-09','goles':1},
                 {'equipo_id':'BRA','jugador_id':'J-BRA-09','goles':0}]
    influx = SimpleNamespace(muestras_jugadores=Mock(return_value=muestras),
                             agregados_jugadores=Mock(side_effect=lambda _: ([dict(f) for f in minutos], jugadores)))
    neo = Mock()
    resultado = archivar_estadisticas('P-03', mongo, neo, influx)
    assert resultado['muestras'] == 182
    assert neo.archivar_estadisticas.call_args.args[4] == jugadores
    assert neo.archivar_estadisticas.call_args.args[1][0]['posesion_pct'] == 50
    assert col.update_one.call_args.args[1]['$set']['archivo_estado'] == 'completo'


def test_eventos_tienen_categoria_y_timestamp_unico_repetible():
    requests = []
    adapter = InfluxAdapter(Settings(_env_file=None))
    adapter._http = httpx.Client(base_url='http://influx', transport=httpx.MockTransport(lambda req: requests.append(req) or httpx.Response(204)))
    plantel = {'ARG': ['J-ARG-09'], 'BRA': ['J-BRA-09']}
    jugadas = [{'id':'SIM-P-03-001','orden':1,'minuto':23,'jugador':'J-ARG-09','equipo_id':'ARG','tipo':'Pase'},
               {'id':'SIM-P-03-002','orden':2,'minuto':23,'jugador':'J-ARG-09','equipo_id':'ARG','tipo':'Pase'}]
    fecha = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for _ in range(2): adapter.guardar_jugadores('P-03', 23, plantel, jugadas, fecha, 'a'*32)
    assert requests[0].content == requests[1].content
    eventos = [line for line in requests[0].content.decode().splitlines() if line.startswith('jugadas_partido,')]
    assert len(eventos) == 2 and all('categoria=pase' in e for e in eventos)
    assert eventos[0].split()[-1] != eventos[1].split()[-1]
    assert 'evento_id="SIM-P-03-001"' in eventos[0]


def test_agregados_v3_usan_eventos_para_contadores_y_muestras_para_posesion():
    adapter = InfluxAdapter(Settings(_env_file=None))
    adapter.muestras_jugadores = Mock(return_value=[
        {'equipo_id':'ARG','jugador_id':'J-ARG-09','minuto':23,'posesion_segundos':35,'goles':999},
        {'equipo_id':'BRA','jugador_id':'J-BRA-09','minuto':23,'posesion_segundos':25,'goles':999}])
    consultas = []
    def consultar(sql):
        consultas.append(sql)
        return [{'equipo_id':'ARG','jugador_id':'J-ARG-09','minuto':23,'pases_intentados':1,
                 'pases_completados':1,'tiros':1,'tiros_arco':1,'goles':1,'faltas':0}]
    adapter.consultar = consultar
    minutos, jugadores = adapter.agregados_eventos('P-03', 'a'*32)
    assert "FROM jugadas_partido" in consultas[0] and "GROUP BY equipo_id, jugador_id, minuto" in consultas[0]
    por_equipo = {fila['equipo_id']:fila for fila in minutos}
    assert por_equipo['ARG']['goles'] == 1 and por_equipo['BRA']['goles'] == 0
    assert por_equipo['ARG']['posesion_segundos'] == 35
    assert len(jugadores) == 2


def test_cierre_v3_comprueba_eventos_y_guarda_timestamp(monkeypatch):
    from types import SimpleNamespace
    from app.routes import simulaciones
    plantel = {'ARG': ['J-ARG-09'], 'BRA': ['J-BRA-09']}
    jugada = {'id':'SIM-P-03-001', 'tipo':'Gol', 'minuto':23, 'orden':1,
              'equipo_id':'ARG', 'jugador':'J-ARG-09', 'influido_por':[]}
    doc = {'estadisticas_version':3, 'corrida_id':'a'*32, 'estado':'Finalizado',
           'plantel_estadisticas':plantel, 'partido':{'local':{'codigo':'ARG','nombre':'Argentina'},'visitante':{'codigo':'BRA','nombre':'Brasil'}},
           'marcador':{'local':1,'visitante':0}, 'jugadas':[jugada], 'inicio_estadisticas':__import__('datetime').datetime(2026,1,1)}
    col = Mock(); col.find_one.return_value = doc
    mongo = SimpleNamespace(db=SimpleNamespace(simulaciones=col, jugadores=SimpleNamespace(find=Mock(return_value=[{'_id':'J-ARG-09','nombre':'Ana','apellido':'López'}]))))
    muestras = []
    for equipo, ids in plantel.items():
        for minuto in range(91):
            gol = int(equipo == 'ARG' and minuto == 23)
            muestras.append({'equipo_id':equipo,'jugador_id':ids[0], 'minuto':minuto,
                'pases_intentados':0,'pases_completados':0,'tiros':gol,'tiros_arco':gol,
                'goles':gol,'faltas':0,'corners':0,'posesion_segundos':0 if minuto == 0 else 30})
    minutos = [{k:v for k,v in f.items() if k != 'jugador_id'} for f in muestras]
    jugadores = [{'equipo_id':e,'jugador_id':ids[0]} for e,ids in plantel.items()]
    evento = {'evento_id':jugada['id'],'equipo_id':'ARG','jugador_id':'J-ARG-09',
              'minuto':23,'orden':1,'categoria':'gol','time':'2026-01-01T00:00:23.000001Z'}
    influx = SimpleNamespace(muestras_jugadores=Mock(return_value=muestras), eventos_partido=Mock(return_value=[evento]),
        agregados_eventos=Mock(side_effect=lambda *_: ([dict(f) for f in minutos], jugadores)), guardar_resumenes=Mock())
    neo = Mock()
    simulaciones.archivar_estadisticas('P-03', mongo, neo, influx)
    influx.guardar_resumenes.assert_called_once()
    assert col.update_one.call_args.args[1]['$set'] == {'archivo_estado': 'completo'}
    assert neo.archivar_estadisticas.call_args.args[3][0]['timestamp'] == evento['time']
    assert neo.archivar_estadisticas.call_args.args[3][0]['categoria'] == 'Gol'
    influx.eventos_partido.return_value = []
    monkeypatch.setattr(simulaciones.time, 'sleep', lambda _:None)
    neo.reset_mock()
    with pytest.raises(Conflicto, match='no coinciden'):
        simulaciones.archivar_estadisticas('P-03', mongo, neo, influx)
    neo.archivar_estadisticas.assert_not_called()
