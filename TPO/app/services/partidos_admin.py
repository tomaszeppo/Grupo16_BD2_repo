from app.errors import Conflicto, NoEncontrado, ValidacionError
from app.observability import logger
from app.reloj import Reloj


class PartidosAdminService:
    """Operación del partido durante la demostración: ponerlo en juego, definir equipos y cargar jugadas."""

    def __init__(self, neo4j, calendario, reloj: Reloj, publicador):
        self._neo4j = neo4j
        self._calendario = calendario
        self._reloj = reloj
        self._publicador = publicador

    def _partido(self, partido_id: str) -> dict:
        partido = self._neo4j.obtener_partido(partido_id)
        if partido is None:
            raise NoEncontrado(f"No existe el partido {partido_id}.")
        return partido

    def poner_en_juego(self, partido_id: str) -> dict:
        partido = self._partido(partido_id)
        if partido["estado"] == "Finalizado":
            raise Conflicto("El partido ya terminó.")
        if partido["local"] is None or partido["visitante"] is None:
            raise Conflicto("Todavía no están definidos los equipos de este partido.")
        self._neo4j.iniciar_partido(partido_id, self._reloj())
        self._calendario.invalidar()  # en este proceso los pronósticos se cierran ya; en los demás, al vencer su copia
        return self._partido(partido_id)

    def asignar_equipos(self, partido_id: str, local: str, visitante: str) -> dict:
        if local == visitante:
            raise ValidacionError("Un equipo no puede jugar contra sí mismo.")
        partido = self._partido(partido_id)
        if partido["fase"] == "Fase de grupos":
            raise Conflicto("Los equipos de la fase de grupos ya están definidos por el fixture.")
        if partido["estado"] != "Programado":
            raise Conflicto("El partido ya empezó: no se pueden cambiar sus equipos.")
        faltan = {local, visitante} - self._neo4j.equipos_existentes([local, visitante])
        if faltan:
            raise NoEncontrado(f"No existe el equipo {', '.join(sorted(faltan))}.")
        if not self._neo4j.asignar_equipos(partido_id, local, visitante):
            raise Conflicto("El partido cambió de estado mientras se asignaban los equipos.")
        self._calendario.invalidar()
        return self._partido(partido_id)

    def registrar_evento(self, partido_id: str, evento: dict) -> tuple[dict, bool]:
        """Alta de una jugada. Devuelve la jugada y si fue alta; repetir la misma jugada no la duplica."""
        revision = self._neo4j.revisar_evento(partido_id, evento)
        if revision is None:
            raise NoEncontrado(f"No existe el partido {partido_id}.")
        existente = revision["existente"]
        if existente is not None:
            igual = (existente["partido"] == partido_id and existente["tipo"] == evento["tipo"]
                     and existente["minuto"] == evento["minuto"] and existente["orden"] == evento["orden"]
                     and existente["jugador"] == evento.get("jugador")
                     and set(revision["influido_por_existente"]) == set(evento.get("influido_por") or []))
            if not igual:
                raise Conflicto(f"Ya existe una jugada {evento['id']} con otros datos.")
            return evento, False
        if revision["estado"] != "En juego":
            raise Conflicto("Solo se pueden cargar jugadas de un partido en juego.")
        if evento.get("jugador") and revision["jugador_ok"] is None:
            raise Conflicto(f"El jugador {evento['jugador']} no pertenece a ninguno de los equipos de este partido.")
        desconocidas = set(evento.get("influido_por") or []) - set(revision["previas_ok"])
        if desconocidas:
            raise Conflicto(f"Estas jugadas no son de este partido: {', '.join(sorted(desconocidas))}.")
        self._neo4j.registrar_evento(partido_id, evento)
        try:
            self._publicador.publicar(partido_id, evento)
        except Exception:  # el aviso es secundario: la jugada ya quedó guardada
            logger.exception("publicador_de_eventos_fallo partido=%s evento=%s", partido_id, evento["id"])
        return evento, True
