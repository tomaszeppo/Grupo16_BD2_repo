from app.errors import NoEncontrado


class PartidosMongoService:
    def __init__(self, repo):
        self._repo = repo

    def detalle(self, codigo: str) -> dict:
        partido = self._repo.obtener_partido_detalle(codigo)
        if partido is None:
            raise NoEncontrado(f"No existe el partido '{codigo}'.")
        return partido

    def cambiar_estado(self, codigo: str, nuevo: str) -> dict:
        actual = self.detalle(codigo)
        if actual["estado"] == nuevo:
            return actual
        self._repo.cambiar_estado_partido(codigo, nuevo)
        return self.detalle(codigo)
