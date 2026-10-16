from app.errors import NoEncontrado


class PartidosIrisService:
    def __init__(self, repo):
        self._repo = repo

    def detalle(self, codigo: str) -> dict:
        partido = self._repo.obtener_partido(codigo)
        if partido is None:
            raise NoEncontrado(f"No existe el partido '{codigo}'.")
        return partido

    def cambiar_estado(self, codigo: str, nuevo: str) -> dict:
        actual = self.detalle(codigo)
        if actual["estado"] == nuevo:  # idempotente: ya está en el estado pedido, no se escribe
            return actual
        self._repo.cambiar_estado(codigo, nuevo)
        return self.detalle(codigo)
