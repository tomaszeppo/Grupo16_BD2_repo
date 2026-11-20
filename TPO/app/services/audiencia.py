"""Audiencia del partido: lo que el simulador hace al cerrar cada minuto y al terminar.

Cada minuto simulado (un segundo real):
  1. Cuenta, por país, las conexiones en vivo que dieron señal en los últimos `presencia_vencimiento_segundos`.
  2. Toma y borra los contadores de comentarios del minuto, por país y origen.
  3. Lo escribe en InfluxDB (`audiencia_partido`, `comentarios_partido`).
  4. Avisa el estado (minuto, marcador, audiencia) por `estado:{partido}` a todas las conexiones.
Al terminar, guarda los espectadores únicos por país (`audiencia_resumen`).

Nada de esto puede cortar la simulación: si Redis o InfluxDB fallan, ese minuto queda incompleto y sigue.
"""
import json
import time

from app.observability import logger

PAISES_FIJOS = ("ARG", "BRA", "ESP", "URU")  # los que comenta siempre el simulador
ORIGENES = ("usuario", "simulacion")


class Audiencia:
    def __init__(self, redis, influx, settings, reloj=time.time):
        self._redis = redis
        self._influx = influx
        self._vencimiento = settings.presencia_vencimiento_segundos
        self._reloj = reloj

    def paises_de(self, partido_id: str) -> set[str]:
        return set(PAISES_FIJOS) | self._redis.miembros(f"paises:{partido_id}")

    def cerrar_minuto(self, partido_id: str, minuto: int, corrida_id: str, tipo: str, instante, marcador: dict,
                      estado: str) -> dict:
        incompleto = False
        espectadores: dict[str, int] = {}
        comentarios: dict[tuple[str, str], int] = {}
        try:
            desde = self._reloj() - self._vencimiento
            for pais in sorted(self.paises_de(partido_id)):
                espectadores[pais] = self._redis.contar_desde(f"audiencia:{partido_id}:{pais}", desde)
                for origen in ORIGENES:
                    comentarios[(pais, origen)] = self._redis.tomar_y_borrar(f"cuenta:{partido_id}:{pais}:{origen}")
        except Exception:
            logger.warning("audiencia_minuto_sin_redis partido=%s minuto=%s", partido_id, minuto)
            return {"incompleto": True}
        try:
            self._influx.guardar_audiencia(partido_id, minuto, corrida_id, tipo, espectadores, comentarios, instante)
        except Exception:
            logger.warning("audiencia_minuto_sin_influx partido=%s minuto=%s", partido_id, minuto)
            incompleto = True
        aviso = {"tipo": "estado", "minuto": minuto, "marcador": marcador, "estado": estado,
                 "audiencia": {"total": sum(espectadores.values()), "por_pais": espectadores}}
        try:
            self._redis.publicar(f"estado:{partido_id}", json.dumps(aviso))
        except Exception:
            incompleto = True
        return {**aviso, "incompleto": incompleto}

    def cerrar_partido(self, partido_id: str, corrida_id: str, tipo: str, instante, marcador: dict | None = None) -> None:
        """Avisa el final a quienes miran y guarda los espectadores únicos por país."""
        try:
            self._redis.publicar(f"estado:{partido_id}", json.dumps(
                {"tipo": "estado", "minuto": 90, "marcador": marcador or {}, "estado": "Finalizado"}))
        except Exception:
            logger.warning("audiencia_aviso_final_fallido partido=%s", partido_id)
        try:
            unicos = {pais: self._redis.contar_unicos(f"unicos:{partido_id}:{pais}")
                      for pais in sorted(self.paises_de(partido_id))}
            self._influx.guardar_resumen_audiencia(partido_id, corrida_id, tipo, unicos, instante)
        except Exception:
            logger.warning("audiencia_resumen_fallido partido=%s", partido_id)
