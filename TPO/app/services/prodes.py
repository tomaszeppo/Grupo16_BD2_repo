from app.errors import Conflicto, NoEncontrado
from app.reloj import Reloj


class ProdesService:
    """Prodes privados. El prode general no se guarda: son todos los usuarios."""

    def __init__(self, mongo, reloj: Reloj, maximo: int):
        self._mongo = mongo
        self._reloj = reloj
        self._maximo = maximo

    def crear(self, nombre: str, dueno: str) -> dict:
        return self._mongo.crear_prode(nombre, dueno, self._reloj())

    def unirse(self, codigo: str, usuario_id: str) -> tuple[str, dict]:
        resultado, prode = self._mongo.unir_a_prode(codigo, usuario_id, self._maximo)
        if resultado == "no_existe":
            raise NoEncontrado("No existe un prode con ese código de invitación.")
        if resultado == "lleno":
            raise Conflicto(f"El prode ya tiene {self._maximo} integrantes, que es el máximo.")
        return resultado, prode

    def de_usuario(self, usuario_id: str) -> list[dict]:
        return self._mongo.prodes_de(usuario_id)
