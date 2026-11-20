"""Comentarios de los partidos, como el chat de una transmisión en vivo.

Publicar, en este orden:
  1. Repetido: `visto:{comentario_id}` (10 minutos). Si ya estaba, es un reintento del cliente y se devuelve
     lo que se guardó la primera vez. La clave de Cassandra lleva la hora del servidor, así que la tabla sola
     no frena un duplicado; Redis ya es obligatorio para comentar.
  2. Modo lento: `lento:{usuario}` (N segundos). Si existe, 429.
  3. Guardar en Cassandra, en la región del país del usuario.
  4. Repartir por Redis (`chat:{partido}:{pais}` y `chat:{partido}:todos`) a todos los procesos de la API.
  5. Contar para la audiencia (`cuenta:{partido}:{pais}:{origen}`, lo vacía el simulador cada minuto).
Si falla el paso 2 o el 3 se borra la marca de repetido, para que el usuario pueda volver a intentar; si falla
el 3 (Cassandra) también se le devuelve el modo lento, porque la falla no es suya.
"""
import json
import time
import uuid
from datetime import datetime, timedelta, timezone

from app import metricas
from app.dominio.regiones import region_de
from app.errors import Conflicto, DemasiadosPedidos, NoEncontrado
from app.observability import logger

PAISES_SIMULADOR = ("ARG", "BRA", "ESP", "URU")
VENTANAS_HACIA_ATRAS = 6  # tres horas: alcanza para un partido con alargue y la previa
SEGUNDOS_REPETIDO = 600
# El resultado se registra un instante antes de marcar el partido como finalizado: en ese hueco todavía entran comentarios.
MARGEN_TRAS_EL_CIERRE = timedelta(minutes=1)


def ventana(fecha: datetime) -> datetime:
    """Partición de media hora a la que pertenece un instante."""
    return fecha.replace(minute=fecha.minute // 30 * 30, second=0, microsecond=0)


def _utc(fecha: datetime) -> datetime:
    """El driver de Cassandra devuelve fechas sin zona, en UTC."""
    return fecha.replace(tzinfo=timezone.utc) if fecha.tzinfo is None else fecha


def _iso(fecha) -> str:
    return fecha if isinstance(fecha, str) else _utc(fecha).isoformat()


class ComentariosService:
    def __init__(self, cassandra, redis, neo4j, mongo, reloj, segundos_entre_comentarios: float):
        self._cassandra = cassandra
        self._redis = redis
        self._neo4j = neo4j
        self._mongo = mongo
        self._reloj = reloj
        self._lento = segundos_entre_comentarios

    # --- publicar ---
    def publicar(self, partido_id: str, usuario_id: str, comentario_id: uuid.UUID, contenido: str) -> tuple[dict, bool]:
        partido = self._neo4j.obtener_partido(partido_id)
        if partido is None:
            raise NoEncontrado("No existe el partido.")
        if partido["estado"] != "En juego":
            raise Conflicto("Solo se puede comentar mientras el partido está en juego.")
        usuario = self._mongo.obtener_usuario(usuario_id)
        if usuario is None:
            raise NoEncontrado("No existe el usuario.")

        clave_visto = f"visto:{comentario_id}"
        if not self._redis.reservar(clave_visto, "", SEGUNDOS_REPETIDO):
            guardado = self._redis.leer(clave_visto)
            if guardado:
                metricas.VIVO_COMENTARIOS.labels("usuario", "repetido").inc()
                return json.loads(guardado), True
            # El primer intento sigue en curso: se trata como modo lento para que el cliente reintente.
            raise DemasiadosPedidos("Ese comentario se está publicando. Esperá unos segundos.")
        try:
            if not self._redis.reservar(f"lento:{usuario_id}", "", self._lento):
                metricas.VIVO_COMENTARIOS.labels("usuario", "modo_lento").inc()
                raise DemasiadosPedidos(f"Modo lento: un comentario cada {self._lento:g} segundos.")
            try:
                comentario = self._guardar(partido_id, usuario["pais"], usuario["nombre"], contenido, "usuario",
                                           comentario_id)
            except Exception:
                self._redis.borrar(f"lento:{usuario_id}")  # la falla es nuestra: no se le cobra el modo lento
                raise
        except Exception:
            self._redis.borrar(clave_visto)
            raise
        self._redis.guardar(clave_visto, json.dumps(comentario), SEGUNDOS_REPETIDO)
        self._repartir(comentario)
        return comentario, False

    def publicar_automatico(self, partido_id: str, pais: str, nombre: str, contenido: str) -> dict:
        """Comentario del simulador: sin modo lento ni control de estado (lo llama el propio partido en juego).

        Si Redis no puede repartirlo, el comentario ya quedó guardado en Cassandra: se anota y el partido sigue."""
        comentario = self._guardar(partido_id, pais, nombre, contenido, "simulacion", uuid.uuid4())
        try:
            self._repartir(comentario)
        except Exception:
            logger.warning("comentario_automatico_sin_repartir partido=%s pais=%s", partido_id, pais)
        return comentario

    def _guardar(self, partido_id, pais, nombre, contenido, origen, comentario_id) -> dict:
        ahora = self._reloj()
        fila = {"partido_id": partido_id, "pais": pais, "ventana": ventana(ahora), "creado_en": ahora,
                "comentario_id": comentario_id, "usuario_nombre": nombre, "contenido": contenido, "origen": origen}
        try:
            # Primero el país: si el comentario se guardara y el país no, "todos los países" no lo encontraría.
            self._cassandra.registrar_pais(region_de(pais), partido_id, pais)
            region = self._cassandra.guardar_comentario(region_de(pais), fila)
        except Exception:
            metricas.VIVO_COMENTARIOS.labels(origen, "rechazado").inc()
            raise
        return {"comentario_id": str(comentario_id), "partido_id": partido_id, "pais": pais, "usuario_nombre": nombre,
                "contenido": contenido, "creado_en": _iso(ahora), "origen": origen, "region_atendida": region}

    def _repartir(self, comentario: dict) -> None:
        partido, pais = comentario["partido_id"], comentario["pais"]
        mensaje = json.dumps({"tipo": "comentario", **comentario, "enviado_en": time.time()})
        self._redis.publicar(f"chat:{partido}:{pais}", mensaje)
        self._redis.publicar(f"chat:{partido}:todos", mensaje)
        self._redis.incrementar(f"cuenta:{partido}:{pais}:{comentario['origen']}")
        self._redis.agregar_a_conjunto(f"paises:{partido}", pais)
        metricas.VIVO_COMENTARIOS.labels(comentario["origen"], "publicado").inc()

    # --- historial ---
    def historial(self, partido_id: str, pais: str | None, antes_de: datetime | None, limite: int) -> dict:
        """Hacia atrás, ventana por ventana. `pais=None` mezcla todos los países que tuvieron actividad."""
        tope = antes_de or self._tope_inicial(partido_id)
        paises = [pais] if pais else self._paises_con_comentarios(partido_id)
        items, regiones = [], set()
        cortadas = []  # (país, ventana) que devolvieron el máximo pedido: pueden tener más filas
        actual = ventana(tope)
        for _ in range(VENTANAS_HACIA_ATRAS):
            for p in paises:
                filas, region = self._cassandra.comentarios(region_de(p), partido_id, p, actual, tope, limite)
                items.extend(filas)
                regiones.add(region)
                if len(filas) >= limite:
                    cortadas.append((p, actual))
            if len(items) >= limite:
                break
            actual -= timedelta(minutes=30)
        items.sort(key=lambda c: c["creado_en"], reverse=True)
        siguiente = None
        if len(items) >= limite:
            # La página siguiente pide "anteriores a la hora del último". Si el corte cae en medio de varios
            # comentarios con la misma hora, los que quedan afuera no aparecerían nunca: la página se extiende
            # hasta incluirlos a todos (puede traer algunos más que `limite`).
            ultimo = items[limite - 1]["creado_en"]
            vistos = {c["comentario_id"] for c in items if c["creado_en"] == ultimo}
            for p, v in cortadas:
                if v != ventana(_utc(ultimo)):
                    continue
                filas, region = self._cassandra.comentarios_del_instante(region_de(p), partido_id, p, v, ultimo)
                regiones.add(region)
                nuevas = [f for f in filas if f["comentario_id"] not in vistos]
                vistos.update(f["comentario_id"] for f in nuevas)
                items.extend(nuevas)
            items = [c for c in items if c["creado_en"] >= ultimo]
            items.sort(key=lambda c: c["creado_en"], reverse=True)
            siguiente = _iso(ultimo)
        for c in items:
            c["creado_en"] = _iso(c["creado_en"])
        return {"items": items, "siguiente": siguiente, "regiones_atendidas": sorted(regiones)}

    def _paises_con_comentarios(self, partido_id: str) -> list[str]:
        """Las tribunas que hay que leer para "todos los países". Salen de Cassandra, que es donde están los
        comentarios: no dependen de que Redis conserve nada. Los partidos comentados antes de que existiera esa
        tabla no figuran en ella; para esos se usa lo que haya en Redis o los países del simulador."""
        paises = self._cassandra.paises_con_comentarios(partido_id)
        if not paises:
            try:
                paises = self._redis.miembros(f"paises:{partido_id}")
            except Exception:
                paises = set()
        return sorted(paises or PAISES_SIMULADOR)

    def _tope_inicial(self, partido_id: str) -> datetime:
        """Desde dónde se empieza a leer hacia atrás cuando el cliente no lo indica.

        Con el partido en juego, desde ahora. Con el partido cerrado, desde su cierre: si no, pasadas tres
        horas el historial quedaría vacío aunque los comentarios siguen guardados. Si MongoDB no responde se
        lee desde ahora, que es lo correcto para un partido en juego.
        """
        ahora = self._reloj() + timedelta(seconds=1)
        try:
            resultado = self._mongo.obtener_resultado(partido_id)
        except Exception:
            return ahora
        if not resultado or not resultado.get("cerrado_en"):
            return ahora
        return min(ahora, _utc(resultado["cerrado_en"]) + MARGEN_TRAS_EL_CIERRE)
