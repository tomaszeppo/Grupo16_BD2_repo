import time

from app import metricas
from app.errors import Conflicto, NoEncontrado, ValidacionError
from app.observability import logger
from app.reloj import Reloj

PASOS = ("puntuar", "sumar", "foto")
MAX_INTENTOS = 5  # tope de reintentos automáticos; repetir el cierre a mano sigue siendo posible


class PuntuacionService:
    """Cierre de un partido y puntuación de sus pronósticos.

    `cerrar` valida, deja registrado el resultado y marca el partido como finalizado. `ejecutar` es el
    trabajo que puntúa; corre después de responder. Los dos se pueden repetir: cada paso escribe el valor
    final o controla que el partido no esté ya aplicado, así que un corte a mitad de camino se arregla
    repitiendo el pedido.
    """

    def __init__(self, mongo, neo4j, calendario, reloj: Reloj, ranking, toma_vencida_segundos: float):
        self._mongo = mongo
        self._neo4j = neo4j
        self._calendario = calendario
        self._reloj = reloj
        self._ranking = ranking
        self._toma_vencida = toma_vencida_segundos

    def cerrar(self, partido_id: str, goles_local: int, goles_visitante: int, clasificado: str | None) -> dict:
        partido = self._neo4j.obtener_partido(partido_id)
        if partido is None:
            raise NoEncontrado(f"No existe el partido {partido_id}.")
        if partido["estado"] == "Programado":
            raise Conflicto("El partido no empezó: primero hay que ponerlo en juego.")
        local, visitante = partido["local"]["codigo"], partido["visitante"]["codigo"]

        if partido["fase"] == "Fase de grupos":
            if clasificado is not None:
                raise ValidacionError("En la fase de grupos no se indica quién clasifica.")
        else:
            ganador = local if goles_local > goles_visitante else visitante if goles_visitante > goles_local else None
            if ganador is None and clasificado not in (local, visitante):
                raise ValidacionError("En una eliminatoria empatada hay que indicar cuál de los dos equipos clasifica.")
            if ganador is not None and clasificado not in (None, ganador):
                raise ValidacionError(f"El marcador dice que clasifica {ganador}.")
            clasificado = clasificado or ganador

        goles = self._neo4j.contar_goles(partido_id)
        if goles and (goles.get(local, 0), goles.get(visitante, 0)) != (goles_local, goles_visitante):
            raise Conflicto(
                f"El marcador {goles_local}-{goles_visitante} no coincide con los goles cargados como jugadas "
                f"({goles.get(local, 0)}-{goles.get(visitante, 0)}).")

        # Primero el resultado en MongoDB (manda para el prode) y después el estado en Neo4j. Si se corta
        # entre los dos, repetir el pedido encuentra el mismo marcador y completa lo que faltaba.
        ahora = self._reloj()
        registrado = self._mongo.registrar_resultado(
            partido_id, goles_local, goles_visitante, clasificado,
            inicio_programado=partido["fecha_hora"], inicio_real=partido["inicio_real"] or partido["fecha_hora"],
            ahora=ahora)
        if registrado["goles_local"] != goles_local or registrado["goles_visitante"] != goles_visitante:
            raise Conflicto(f"El partido ya se cerró {registrado['goles_local']}-{registrado['goles_visitante']}: "
                            "el resultado no se puede cambiar.")
        self._neo4j.finalizar_partido(partido_id, goles_local, goles_visitante)
        self._calendario.invalidar()
        return registrado

    def ejecutar(self, partido_id: str) -> None:
        """Puntúa el partido. Si otro proceso ya lo está haciendo, o ya está hecho, no hace nada."""
        resultado = self._mongo.tomar_puntuacion(partido_id, self._reloj(), self._toma_vencida)
        if resultado is None:
            return
        hechos = resultado["puntuacion"].get("pasos") or {}
        try:
            if hasattr(self._ranking, "puntuar_en_redis"):
                self._ejecutar_redis(partido_id, resultado, hechos)
                return
            for paso in PASOS:
                if paso in hechos:
                    continue  # quedó de un intento anterior
                inicio = time.perf_counter()
                extra = {}
                if paso == "puntuar":
                    extra["pronosticos"] = self._mongo.puntuar_pronosticos(partido_id, resultado)
                elif paso == "sumar":
                    self._mongo.sumar_a_puntajes(partido_id)
                else:
                    self._mongo.guardar_foto(partido_id, self._reloj())
                duracion_ms = round((time.perf_counter() - inicio) * 1000, 1)
                self._marcar(partido_id, paso, duracion_ms, extra)
                self._al_terminar_paso(paso, duracion_ms, extra)
            self._ranking.partido_puntuado(partido_id)
            self._mongo.cerrar_puntuacion(partido_id, "completa", self._reloj())
        except Exception:
            logger.exception("puntuacion_fallo partido=%s", partido_id)
            self._mongo.cerrar_puntuacion(partido_id, "fallida", self._reloj())

    def retomar_pendientes(self) -> list[str]:
        """Retoma las puntuaciones que no terminaron: fallaron, o el proceso que las llevaba murió.

        Lo llama cada proceso de la API cada tanto. Si dos procesos lo hacen a la vez, uno solo toma cada
        partido. Devuelve los partidos que intentó.
        """
        partidos = self._mongo.puntuaciones_por_retomar(self._reloj(), self._toma_vencida, MAX_INTENTOS)
        for partido_id in partidos:
            logger.warning("puntuacion_retomada partido=%s", partido_id)
            self.ejecutar(partido_id)
        return partidos

    def _marcar(self, partido_id: str, paso: str, duracion_ms: float, extra: dict) -> None:
        # Cada paso terminado renueva la toma: el plazo para darla por abandonada corre por paso, no por
        # la puntuación entera, que con muchos pronósticos puede durar más que ese plazo.
        self._mongo.marcar_paso(partido_id, paso, duracion_ms, {**extra, "tomada_en": self._reloj()})

    def _ejecutar_redis(self, partido_id, resultado, hechos):
        inicio = time.perf_counter()
        cantidad = self._ranking.puntuar_en_redis(partido_id, resultado)
        self._marcar(partido_id, "puntuar", round((time.perf_counter() - inicio) * 1000, 1),
                                {"pronosticos": cantidad})
        # El ranking queda disponible en Redis antes de hacer el volcado durable.
        if "sumar" not in hechos:
            time.sleep(self._ranking.demora)
            inicio = time.perf_counter()
            self._ranking.persistir_partido(partido_id)
            self._marcar(partido_id, "sumar", round((time.perf_counter() - inicio) * 1000, 1), {})
        if "foto" not in hechos:
            inicio = time.perf_counter()
            self._mongo.guardar_foto(partido_id, self._reloj())
            self._marcar(partido_id, "foto", round((time.perf_counter() - inicio) * 1000, 1), {})
        self._mongo.cerrar_puntuacion(partido_id, "completa", self._reloj())
        try:
            self._ranking.limpiar_partido(partido_id)
        except Exception:
            logger.exception("limpieza_redis_pendiente partido=%s", partido_id)

    def _al_terminar_paso(self, paso: str, duracion_ms: float, extra: dict) -> None:
        metricas.registrar_paso_de_puntuacion(paso, duracion_ms / 1000, extra.get("pronosticos"))

    def estado(self, partido_id: str) -> dict:
        resultado = self._mongo.obtener_resultado(partido_id)
        if resultado is None:
            raise NoEncontrado(f"El partido {partido_id} no tiene resultado cargado.")
        return resultado
