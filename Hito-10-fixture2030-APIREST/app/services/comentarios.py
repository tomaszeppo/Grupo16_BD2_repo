import base64
import binascii
from datetime import datetime, timezone

from app.errors import NoEncontrado, ValidacionError


def normalizar_ventana(dt: datetime) -> datetime:
    """Valida y convierte a UTC naive (lo que espera el driver). Debe tener zona y estar alineada a :00/:30."""
    if dt.tzinfo is None:
        raise ValidacionError("La ventana debe incluir zona horaria (ej. 2030-06-15T18:30:00Z).")
    utc = dt.astimezone(timezone.utc).replace(tzinfo=None)
    if utc.minute not in (0, 30) or utc.second or utc.microsecond:
        raise ValidacionError("La ventana debe comenzar en minuto :00 o :30, sin segundos.")
    return utc


def piso_ventana(dt: datetime) -> datetime:
    minuto = 0 if dt.minute < 30 else 30
    return dt.replace(minute=minuto, second=0, microsecond=0)


def codificar_cursor(estado: bytes | None) -> str | None:
    return None if estado is None else base64.urlsafe_b64encode(estado).decode("ascii")


def decodificar_cursor(cursor: str | None) -> bytes | None:
    if cursor is None:
        return None
    try:  # validate=True rechaza caracteres fuera del alfabeto (b64decode los descartaría en silencio)
        return base64.b64decode(cursor.encode("ascii"), altchars=b"-_", validate=True)
    except (binascii.Error, ValueError, UnicodeEncodeError) as exc:
        raise ValidacionError("El cursor no es válido.") from exc


class ComentariosService:
    def __init__(self, repo, partidos, ahora=None):
        self._repo = repo
        self._partidos = partidos
        self._ahora = ahora or (lambda: datetime.now(timezone.utc))

    def listar(self, partido_id: str, pais: str, ventana: datetime, limit: int, cursor: str | None) -> dict:
        v = normalizar_ventana(ventana)
        estado = decodificar_cursor(cursor)
        items, siguiente = self._repo.listar(partido_id, pais, v, limit, estado)
        return {
            "partido_id": partido_id, "pais": pais, "ventana": v.isoformat() + "Z", "limit": limit,
            "items": items, "next_cursor": codificar_cursor(siguiente),
        }

    def crear(self, partido_id: str, clave: str, datos: dict) -> tuple[dict, bool]:
        if self._partidos.obtener_partido(partido_id) is None:
            raise NoEncontrado(f"No existe el partido '{partido_id}'.")
        ahora = self._ahora().astimezone(timezone.utc).replace(tzinfo=None)
        creado_en = ahora.replace(microsecond=(ahora.microsecond // 1000) * 1000)
        return self._repo.registrar(
            clave=clave, partido_id=partido_id, pais=datos["pais"], ventana=piso_ventana(creado_en),
            creado_en=creado_en, usuario_id=datos["usuario_id"], usuario_nombre=datos["usuario_nombre"],
            contenido=datos["contenido"],
        )
