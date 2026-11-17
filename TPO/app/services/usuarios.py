from app.errors import NoEncontrado
from app.reloj import Reloj


class UsuariosService:
    def __init__(self, mongo, reloj: Reloj):
        self._mongo = mongo
        self._reloj = reloj

    def crear(self, nombre: str, pais: str) -> dict:
        return self._mongo.crear_usuario(nombre, pais, self._reloj())

    def obtener(self, usuario_id: str) -> dict:
        usuario = self._mongo.obtener_usuario(usuario_id)
        if usuario is None:
            raise NoEncontrado(f"No existe el usuario {usuario_id}.")
        return usuario


class EquiposService:
    """Catálogo de equipos y planteles. Es la ficha que sirve MongoDB; las relaciones están en Neo4j."""

    def __init__(self, mongo):
        self._mongo = mongo

    def listar(self) -> list[dict]:
        return self._mongo.listar_equipos()

    def jugadores(self, codigo: str, posicion: str | None, limit: int, offset: int) -> tuple[list[dict], int]:
        if self._mongo.obtener_equipo(codigo) is None:
            raise NoEncontrado(f"No existe el equipo {codigo}.")
        return self._mongo.listar_jugadores(codigo, posicion, limit, offset)
