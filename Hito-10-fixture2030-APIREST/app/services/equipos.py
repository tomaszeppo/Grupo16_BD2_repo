from app.errors import NoEncontrado


class EquiposService:
    def __init__(self, repo):
        self._repo = repo

    def obtener_equipo(self, codigo: str) -> dict:
        equipo = self._repo.obtener_equipo(codigo)
        if equipo is None:
            raise NoEncontrado(f"No existe el equipo '{codigo}'.")
        return equipo

    def listar_jugadores(self, codigo: str, posicion: str | None, limit: int, offset: int) -> dict:
        self.obtener_equipo(codigo)  # distingue equipo inexistente (404) de equipo sin jugadores (200 vacío)
        total = self._repo.contar_jugadores(codigo, posicion)
        items = self._repo.listar_jugadores(codigo, posicion, limit, offset) if total > offset else []
        return {"equipo": codigo, "total": total, "limit": limit, "offset": offset, "items": items}
