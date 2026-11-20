"""Cada país pertenece a una región: América o Europa."""
from app.dominio import regiones
from seed.datos import EQUIPOS


def test_region_de_cada_pais():
    assert regiones.region_de("ARG") == "america"
    assert regiones.region_de("MEX") == "america"
    assert regiones.region_de("ESP") == "europa"
    assert regiones.region_de("JPN") == "europa"  # simplificación de laboratorio: el resto del mundo va a Europa


def test_todos_los_paises_del_catalogo_tienen_region():
    assert {regiones.region_de(codigo) for codigo, _ in EQUIPOS} == {"america", "europa"}


def test_otra_region():
    assert regiones.otra("america") == "europa" and regiones.otra("europa") == "america"
