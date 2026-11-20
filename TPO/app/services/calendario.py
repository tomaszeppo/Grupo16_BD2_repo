import threading
from datetime import datetime, timedelta

from app.errors import ApiError
from app.reloj import Reloj

REINTENTO_SEGUNDOS = 5  # con Neo4j caído se reintenta cada tanto, no en cada pedido


class Calendario:
    """Copia en memoria del calendario (128 partidos), una por proceso de la API.

    Neo4j gobierna el calendario, pero validar un pronóstico solo necesita horario, estado y equipos del
    partido. Con esta copia Neo4j queda fuera del camino del pico de pronósticos, y si se cae se sigue
    pronosticando con el último calendario conocido. El costo: un cambio tarda hasta `ttl_segundos` en verse
    en los demás procesos (ver docs/decisiones.md).

    Renovar la copia nunca frena a los demás pedidos: mientras un pedido consulta a Neo4j, el resto sigue con
    la copia que hay. Y cuando ya se sabe que Neo4j no contesta, los reintentos corren aparte y ningún pedido
    los espera. Solo se espera a Neo4j cuando todavía no hay ninguna copia.
    """

    def __init__(self, neo4j, ttl_segundos: float, reloj: Reloj):
        self._neo4j = neo4j
        self._ttl = ttl_segundos
        self._reloj = reloj
        self._candado = threading.Lock()  # una sola renovación a la vez
        self._partidos: dict[str, dict] | None = None
        self._cargado_en: datetime | None = None
        self._proximo_intento: datetime | None = None
        self._desactualizado = True
        self._fallando = False  # el último intento de renovación falló
        self._reintento: threading.Thread | None = None

    def partido(self, partido_id: str) -> dict | None:
        if self._ttl <= 0:  # sin copia: se usa solo para medir cuánto ahorra tenerla
            return self._neo4j.obtener_partido(partido_id)
        return self._copia().get(partido_id)

    def listar(self, fase: str | None, fecha, estado: str | None) -> list[dict]:
        """El fixture filtrado, desde la copia. Es el listado más pedido y el más caro de armar en Neo4j."""
        if self._ttl <= 0:
            return self._neo4j.listar_partidos(fase, fecha, estado)
        elegidos = [p for p in self._copia().values()
                    if (fase is None or p["fase"] == fase) and (estado is None or p["estado"] == estado)
                    and (fecha is None or p["fecha_hora"].date() == fecha)]
        return [dict(p) for p in sorted(elegidos, key=lambda p: (p["fecha_hora"], p["id"]))]

    def invalidar(self) -> None:
        """La próxima lectura de este proceso vuelve a Neo4j. Los demás procesos se enteran al vencer su copia."""
        with self._candado:
            self._proximo_intento = None
            self._fallando = False
            if self._cargado_en is not None:
                self._cargado_en = self._reloj() - timedelta(seconds=self._ttl + 1)

    def refrescar(self) -> None:
        """Intenta renovar si corresponde, sin propagar el error. Lo usa el chequeo de salud."""
        if self._ttl > 0:
            try:
                self._copia()
            except ApiError:
                pass

    def estado(self) -> dict:
        antiguedad = (self._reloj() - self._cargado_en).total_seconds() if self._cargado_en else None
        if antiguedad is not None and not self._desactualizado:
            antiguedad = max(0.0, antiguedad)
        return {"cargado": self._partidos is not None, "antiguedad_segundos": antiguedad,
                "desactualizado": self._desactualizado}

    def esperar_renovacion(self, segundos: float = 5) -> None:
        """Espera a que termine un reintento en curso. Para las pruebas y para un apagado ordenado."""
        hilo = self._reintento
        if hilo is not None:
            hilo.join(segundos)

    # --- interno ---
    def _copia(self) -> dict[str, dict]:
        ahora = self._reloj()
        if self._vigente(ahora):
            return self._partidos
        if self._partidos is None:
            with self._candado:  # sin copia no hay con qué responder: se espera a Neo4j
                if self._partidos is None:
                    self._renovar(self._reloj())
            return self._partidos
        if self._proximo_intento is not None and ahora < self._proximo_intento:
            return self._partidos  # Neo4j falló hace instantes
        if not self._candado.acquire(blocking=False):
            return self._partidos  # otro pedido ya está renovando: se sigue con la copia
        if self._fallando:
            # Ya se sabe que Neo4j no contesta: el reintento va por su cuenta y nadie lo espera.
            self._reintento = threading.Thread(target=self._renovar_y_soltar, daemon=True)
            self._reintento.start()
            return self._partidos
        try:
            if not self._vigente(self._reloj()):
                try:
                    self._renovar(self._reloj())
                except ApiError:
                    pass  # hay copia: se sigue con ella
        finally:
            self._candado.release()
        return self._partidos

    def _renovar_y_soltar(self) -> None:
        try:
            self._renovar(self._reloj())
        except Exception:
            pass
        finally:
            self._candado.release()

    def _renovar(self, ahora: datetime) -> None:
        """Consulta a Neo4j. Hay que llamarla con el candado tomado."""
        try:
            partidos = self._neo4j.listar_partidos()
        except ApiError:
            self._desactualizado = True
            self._fallando = True
            self._proximo_intento = ahora + timedelta(seconds=REINTENTO_SEGUNDOS)
            raise
        self._partidos = {p["id"]: p for p in partidos}
        self._cargado_en = self._reloj()
        self._proximo_intento = None
        self._desactualizado = False
        self._fallando = False

    def _vigente(self, ahora: datetime) -> bool:
        return (self._partidos is not None and self._cargado_en is not None
                and (ahora - self._cargado_en).total_seconds() < self._ttl)
