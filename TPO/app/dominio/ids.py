"""Identificadores del proyecto. Son los mismos en todas las bases: nadie traduce ids entre una y otra."""
import re

ID_PARTIDO = r"^P-\d{2,3}$"  # P-01 … P-104
ID_USUARIO = r"^U\d{7}$"  # U0000001
CODIGO_EQUIPO = r"^[A-Z]{3}$"  # código FIFA
ID_PRODE = r"^PR-[0-9a-f]{8}$"
ID_EVENTO = r"^[A-Za-z0-9-]{3,40}$"  # lo elige quien carga la jugada, por ejemplo EV-P-01-0007

_PARTIDO = re.compile(ID_PARTIDO)
_USUARIO = re.compile(ID_USUARIO)
_EQUIPO = re.compile(CODIGO_EQUIPO)


def es_id_partido(valor: str) -> bool:
    return bool(_PARTIDO.fullmatch(valor or ""))


def es_id_usuario(valor: str) -> bool:
    return bool(_USUARIO.fullmatch(valor or ""))


def es_codigo_equipo(valor: str) -> bool:
    return bool(_EQUIPO.fullmatch(valor or ""))


def id_usuario(numero: int) -> str:
    return f"U{numero:07d}"


def id_partido(numero: int) -> str:
    return f"P-{numero:02d}"


def id_pronostico(usuario_id: str, partido_id: str) -> str:
    """Un pronóstico por usuario y partido: la clave misma impide el duplicado."""
    return f"{usuario_id}:{partido_id}"
