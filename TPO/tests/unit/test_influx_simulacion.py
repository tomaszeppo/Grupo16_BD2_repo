from datetime import datetime, timezone
import httpx
import pytest
from app.adapters.influx import InfluxAdapter
from app.config.settings import Settings
from app.errors import DependenciaNoDisponible, ValidacionError


def test_guarda_un_punto_por_equipo_con_posesion_complementaria():
    pedidos = []
    def responder(req):
        pedidos.append(req)
        return httpx.Response(204)
    adaptador = InfluxAdapter(Settings(_env_file=None))
    adaptador._http = httpx.Client(base_url="http://influx", transport=httpx.MockTransport(responder))
    adaptador.guardar_minuto("P-03", 23, "ARG", "BRA", datetime(2026, 1, 1, tzinfo=timezone.utc))
    lineas = pedidos[0].content.decode().splitlines()
    assert len(lineas) == 2
    assert "equipo_id=ARG" in lineas[0] and "tiros=1i" in lineas[0]
    assert "equipo_id=BRA" in lineas[1] and "tiros=0i" in lineas[1]
    assert "minuto=23i" in lineas[0]
    assert "precision=nanosecond" in str(pedidos[0].url)


def test_resumen_agrega_por_partido_y_equipo():
    consultas = []
    def responder(req):
        consultas.append(req.read().decode())
        return httpx.Response(200, json=[{"equipo_id":"ARG", "posesion_pct":52.5, "tiros":2}])
    adaptador = InfluxAdapter(Settings(_env_file=None))
    adaptador._http = httpx.Client(base_url="http://influx", transport=httpx.MockTransport(responder))
    assert adaptador.resumen_partido("P-03")[0]["tiros"] == 2
    assert "SUM(tiros)" in consultas[0] and "GROUP BY equipo_id" in consultas[0]
    with pytest.raises(ValidacionError): adaptador.resumen_partido("P-03' OR 1=1")


def test_influx_caido_no_se_hace_pasAR_por_sin_datos():
    adaptador = InfluxAdapter(Settings(_env_file=None))
    adaptador._http = httpx.Client(base_url="http://influx", transport=httpx.MockTransport(lambda req: httpx.Response(503)))
    with pytest.raises(DependenciaNoDisponible): adaptador.resumen_partido("P-03")


def test_acciones_por_minuto_respetan_limites_del_marcador():
    puntos = []
    def responder(req):
        puntos.extend(req.content.decode().splitlines())
        return httpx.Response(204)
    adaptador = InfluxAdapter(Settings(_env_file=None))
    adaptador._http = httpx.Client(base_url="http://influx", transport=httpx.MockTransport(responder))
    for minuto in range(91):
        adaptador.guardar_minuto("P-03", minuto, "ARG", "BRA", datetime(2026, 1, 1, tzinfo=timezone.utc))
    for minuto in range(91):
        for lado, linea in enumerate(puntos[minuto * 2:minuto * 2 + 2]):
            campos = dict(par.split("=", 1) for par in linea.split(" ")[1].split(","))
            numeros = {k: float(v.rstrip("i")) for k, v in campos.items()}
            assert numeros["tiros_arco"] <= numeros["tiros"]
            assert numeros["pases_completados"] <= numeros["pases_intentados"]
            if minuto == (23 if lado == 0 else 75): assert numeros["tiros_arco"] == 1
            if minuto == 0: assert numeros["pases_intentados"] == 0


def test_resumen_funciona_si_la_base_no_tiene_columnas_nuevas():
    consultas = []
    def responder(req):
        consultas.append(req.content.decode())
        return httpx.Response(400) if len(consultas) == 1 else httpx.Response(200, json=[{"equipo_id":"ARG", "tiros":3}])
    adaptador = InfluxAdapter(Settings(_env_file=None))
    adaptador._http = httpx.Client(base_url="http://influx", transport=httpx.MockTransport(responder))
    assert adaptador.resumen_partido("P-03")[0]["tiros"] == 3
    assert "tiros_arco" in consultas[0]
    assert "tiros_arco" not in consultas[1]


def test_contadores_incluyen_jugadas_y_goles_del_guion():
    pedidos = []
    adaptador = InfluxAdapter(Settings(_env_file=None))
    adaptador._http = httpx.Client(base_url="http://influx", transport=httpx.MockTransport(lambda req: pedidos.append(req) or httpx.Response(204)))
    adaptador.guardar_minuto("P-13", 22, "ARG", "BRA", datetime(2026, 1, 1, tzinfo=timezone.utc), (0, 0), ({"Tiro":1}, {}))
    lineas = pedidos[-1].content.decode().splitlines()
    assert "tiros=1i" in lineas[0]
    adaptador.guardar_minuto("P-13", 24, "ARG", "BRA", datetime(2026, 1, 1, tzinfo=timezone.utc), (1, 0), ({"Tiro":1,"Pase":9}, {}))
    linea = pedidos[-1].content.decode().splitlines()[0]
    assert "goles=1i" in linea and "tiros=2i" in linea and "pases_completados=9i" in linea
