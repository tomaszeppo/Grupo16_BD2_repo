from app.errors import NoEncontrado


class PartidosService:
    def __init__(self, repo):
        self._repo = repo

    def obtener_partido(self, partido_id: str) -> dict:
        fila = self._repo.obtener_partido(partido_id)
        if fila is None:
            raise NoEncontrado(f"No existe el partido '{partido_id}'.")
        resultado = None
        if fila.get("ganador") is not None:
            resultado = {
                "ganador": fila["ganador"],
                "perdedor": fila["perdedor"],
                "goles_ganador": fila["goles_ganador"],
                "goles_perdedor": fila["goles_perdedor"],
                "origen": fila.get("origen") or "SIMULADO",
            }
        return {
            "id": fila["id"], "fecha": fila["fecha"], "fase": fila["fase"],
            "estadio": fila["estadio"], "equipos": fila["equipos"], "resultado": resultado,
        }

    def listar_eventos(self, partido_id: str, limit: int) -> dict:
        eventos = self._repo.listar_eventos(partido_id, limit)
        if eventos is None:  # partido inexistente; [] significa partido válido sin eventos
            raise NoEncontrado(f"No existe el partido '{partido_id}'.")
        return {"partido_id": partido_id, "limit": limit, "items": eventos}
