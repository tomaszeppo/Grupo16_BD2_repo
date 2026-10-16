from datetime import datetime

import pytest

from app.adapters.influx import construir_sql
from app.config.settings import Settings
from app.deps import get_estadisticas_service
from app.errors import ValidacionError
from app.services.estadisticas import EstadisticasService

DESDE, HASTA = "2030-06-15T18:30:00Z", "2030-06-15T18:35:00Z"
RAW = {"time": "2030-06-15T18:30:00Z", "equipo_id": "ARG", "fuente": "broadcast", "posesion_pct": 58.4,
       "pases_completados": 12, "tiros": 1, "recuperaciones": 3, "velocidad_kmh": 7.2}
AGG = {"ventana": "2030-06-15T18:30:00Z", "equipo_id": "ARG", "fuente": "broadcast", "posesion_pct_prom": 58.0,
       "pases_completados": 120, "tiros": 4, "recuperaciones": 30, "velocidad_kmh_prom": 7.1, "velocidad_kmh_max": 9.9}


class RepoFalso:
    def __init__(self, filas=None):
        self.llamadas, self.filas = [], filas if filas is not None else [AGG]

    def consultar_estadisticas(self, partido_id, desde, hasta, equipo, agregacion, limite):
        self.llamadas.append((partido_id, desde, hasta, equipo, agregacion, limite))
        return self.filas[:limite]


@pytest.fixture
def repo(app):
    r = RepoFalso()
    app.dependency_overrides[get_estadisticas_service] = lambda: EstadisticasService(r, Settings(_env_file=None))
    return r


def test_ventana_valida_agregada(client, repo, documentado):
    r = client.get("/partidos/P-01/estadisticas",
                   params={"desde": DESDE, "hasta": HASTA, "agregacion": "1m", "equipo": "ARG"})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["agregacion"] == "1m" and cuerpo["truncado"] is False and cuerpo["max_puntos"] == 500
    assert cuerpo["puntos"][0]["ventana"] == "2030-06-15T18:30:00Z"
    assert repo.llamadas[0][3] == "ARG" and repo.llamadas[0][5] == 501  # pide max+1 para detectar truncado
    documentado(r, "get", "/partidos/{partido_id}/estadisticas")


def test_raw_truncado(client, app):
    app.dependency_overrides[get_estadisticas_service] = lambda: EstadisticasService(
        RepoFalso([RAW] * 600), Settings(_env_file=None))
    r = client.get("/partidos/P-01/estadisticas", params={"desde": DESDE, "hasta": HASTA, "agregacion": "raw"})
    cuerpo = r.json()
    assert r.status_code == 200 and cuerpo["truncado"] is True and len(cuerpo["puntos"]) == 500


def test_sin_puntos_es_200_vacio(client, app):
    app.dependency_overrides[get_estadisticas_service] = lambda: EstadisticasService(
        RepoFalso([]), Settings(_env_file=None))
    r = client.get("/partidos/P-05/estadisticas", params={"desde": DESDE, "hasta": HASTA})
    assert r.status_code == 200 and r.json()["puntos"] == []


@pytest.mark.parametrize("params", [
    {"hasta": HASTA},                                                             # falta desde
    {"desde": DESDE},                                                             # falta hasta
    {"desde": "2030-06-15T18:30:00", "hasta": HASTA},                             # sin zona
    {"desde": HASTA, "hasta": DESDE},                                             # invertidas
    {"desde": DESDE, "hasta": DESDE},                                             # iguales
    {"desde": DESDE, "hasta": "2030-06-15T21:00:00Z"},                            # > 120 min
    {"desde": "2030-13-40T00:00:00Z", "hasta": HASTA},                            # imposible
    {"desde": DESDE, "hasta": HASTA, "agregacion": "1h"},
    {"desde": DESDE, "hasta": HASTA, "equipo": "arg"},
    {"desde": DESDE, "hasta": HASTA, "equipo": "ARG' OR 1=1"},
])
def test_parametros_invalidos_no_consultan(client, repo, params, documentado):
    r = client.get("/partidos/P-01/estadisticas", params=params)
    assert r.status_code == 422 and repo.llamadas == []
    documentado(r, "get", "/partidos/{partido_id}/estadisticas")


def test_construir_sql_raw_y_agregado():
    d, h = datetime(2030, 6, 15, 18, 30), datetime(2030, 6, 15, 18, 35)
    sql = construir_sql("P-01", d, h, "ARG", "raw", 501)
    assert "partido_id = 'P-01'" in sql and "equipo_id = 'ARG'" in sql
    assert "time >= '2030-06-15T18:30:00Z'" in sql and "time < '2030-06-15T18:35:00Z'" in sql
    assert sql.endswith("LIMIT 501")
    agg = construir_sql("P-01", d, h, None, "5m", 501)
    assert "DATE_BIN(INTERVAL '5 minutes'" in agg and "AVG(posesion_pct)" in agg and "GROUP BY 1, 2, 3" in agg


@pytest.mark.parametrize("partido,equipo", [("P-01'; DROP", None), ("P-01", "ARG'"), ("x", None)])
def test_construir_sql_revalida_entradas(partido, equipo):
    with pytest.raises(ValidacionError):
        construir_sql(partido, datetime(2030, 6, 15, 18, 30), datetime(2030, 6, 15, 18, 35), equipo, "raw", 10)
