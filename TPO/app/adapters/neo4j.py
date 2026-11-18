from app.adapters.base import operacion
from app.config.settings import Settings
from app.errors import ApiError, DependenciaNoDisponible, DependenciaTimeout

FUENTE = "neo4j"


# Cypher fijo y con parámetros: quien llama a la API nunca aporta texto de consulta.
_PARTIDO_COMPLETO = """
OPTIONAL MATCH (l:Equipo)-[:PARTICIPA_EN {condicion: 'local'}]->(p)
OPTIONAL MATCH (v:Equipo)-[:PARTICIPA_EN {condicion: 'visitante'}]->(p)
OPTIONAL MATCH (p)-[:SE_JUEGA_EN]->(est:Estadio)
RETURN p.id AS id, p.fecha_hora AS fecha_hora, p.fase AS fase, p.estado AS estado,
       l {.codigo, .nombre} AS local, v {.codigo, .nombre} AS visitante,
       est {.id, .nombre, .ciudad} AS estadio,
       p.goles_local AS goles_local, p.goles_visitante AS goles_visitante, p.inicio_real AS inicio_real
ORDER BY p.fecha_hora, p.id
"""

CYPHER_PARTIDOS = """
MATCH (p:Partido)
WHERE ($fase IS NULL OR p.fase = $fase)
  AND ($estado IS NULL OR p.estado = $estado)
  AND ($desde IS NULL OR (p.fecha_hora >= $desde AND p.fecha_hora < $hasta))
""" + _PARTIDO_COMPLETO

CYPHER_PARTIDO = "MATCH (p:Partido {id: $id})" + _PARTIDO_COMPLETO

_EVENTO = """{id: ev.id, tipo: ev.tipo, minuto: ev.minuto, orden: ev.orden,
              jugador: CASE WHEN j IS NULL THEN null
                            ELSE {id: j.id, nombre: j.nombre, apellido: j.apellido, equipo: eq.codigo} END}"""

CYPHER_EVENTOS = """
MATCH (p:Partido {id: $id})
OPTIONAL MATCH (ev:Evento)-[:OCURRE_EN]->(p)
OPTIONAL MATCH (j:Jugador)-[:PROTAGONIZA]->(ev)
OPTIONAL MATCH (j)-[:PERTENECE_A]->(eq:Equipo)
WITH p, ev, j, eq ORDER BY ev.minuto, ev.orden, ev.id
RETURN p.id AS partido, collect(CASE WHEN ev IS NULL THEN null ELSE """ + _EVENTO + """ END)[..$limit] AS eventos
"""

# Todo lo que llevó a una jugada: se recorre INFLUYE_EN hacia atrás, sin saber de antemano cuántos pasos hay.
CYPHER_CADENA = """
MATCH (fin:Evento {id: $evento})-[:OCURRE_EN]->(:Partido {id: $partido})
OPTIONAL MATCH (previo:Evento)-[:INFLUYE_EN*1..10]->(fin)
WITH fin, collect(DISTINCT previo) AS previos
UNWIND previos + [fin] AS ev
OPTIONAL MATCH (j:Jugador)-[:PROTAGONIZA]->(ev)
OPTIONAL MATCH (j)-[:PERTENECE_A]->(eq:Equipo)
WITH ev, j, eq ORDER BY ev.minuto, ev.orden, ev.id
RETURN """ + _EVENTO + """ AS evento
"""

CYPHER_PARTIDOS_DE_EQUIPO = """
MATCH (e:Equipo {codigo: $codigo})
OPTIONAL MATCH (e)-[r:PARTICIPA_EN]->(p:Partido)
OPTIONAL MATCH (rival:Equipo)-[:PARTICIPA_EN]->(p) WHERE rival <> e
WITH e, r, p, rival ORDER BY p.fecha_hora, p.id
RETURN e {.codigo, .nombre} AS equipo,
       collect(CASE WHEN p IS NULL THEN null ELSE {
           id: p.id, fecha_hora: p.fecha_hora, fase: p.fase, estado: p.estado, condicion: r.condicion,
           rival: rival {.codigo, .nombre}, goles_local: p.goles_local, goles_visitante: p.goles_visitante} END) AS partidos
"""

# Desde el último partido de eliminatorias del equipo, los partidos que le quedarían si sigue ganando.
CYPHER_CAMINO_A_LA_FINAL = """
MATCH (:Equipo {codigo: $codigo})-[:PARTICIPA_EN]->(p:Partido)
WHERE p.fase <> 'Fase de grupos'
WITH p ORDER BY p.fecha_hora DESC LIMIT 1
MATCH camino = (p)-[:CLASIFICA_A*]->(:Partido {fase: 'Final'})
WHERE all(r IN relationships(camino) WHERE r.como = 'ganador')
UNWIND nodes(camino)[1..] AS q
RETURN q.id AS id, q.fase AS fase, q.fecha_hora AS fecha_hora, q.estado AS estado
"""

# Participar en un gol es haberlo hecho o haber protagonizado una jugada que llevó a él.
CYPHER_PARTICIPACION = """
MATCH (g:Evento {tipo: 'Gol'})
MATCH (j:Jugador)-[:PROTAGONIZA]->(ev:Evento)-[:INFLUYE_EN*0..10]->(g)
WITH j, count(DISTINCT g) AS participaciones, count(DISTINCT CASE WHEN ev = g THEN g END) AS goles
MATCH (j)-[:PERTENECE_A]->(eq:Equipo)
RETURN j {.id, .nombre, .apellido} AS jugador, eq.codigo AS equipo, goles, participaciones
ORDER BY participaciones DESC, goles DESC, j.id
LIMIT $limit
"""


# --- escrituras de la operación del partido ---
# El orden de los SET importa: primero se fija el inicio real mirando el estado anterior, después se cambia el estado.
CYPHER_INICIAR = """
MATCH (p:Partido {id: $id})
SET p.inicio_real = CASE WHEN p.estado = 'Programado' THEN $ahora ELSE p.inicio_real END,
    p.estado = CASE WHEN p.estado = 'Programado' THEN 'En juego' ELSE p.estado END
RETURN p.id AS id
"""

CYPHER_ASIGNAR_EQUIPOS = """
MATCH (p:Partido {id: $id})
WHERE p.estado = 'Programado' AND p.fase <> 'Fase de grupos'
MATCH (l:Equipo {codigo: $local}), (v:Equipo {codigo: $visitante})
OPTIONAL MATCH (:Equipo)-[anterior:PARTICIPA_EN]->(p)
DELETE anterior
WITH DISTINCT p, l, v
MERGE (l)-[:PARTICIPA_EN {condicion: 'local'}]->(p)
MERGE (v)-[:PARTICIPA_EN {condicion: 'visitante'}]->(p)
RETURN p.id AS id
"""

CYPHER_EQUIPOS_EXISTEN = "MATCH (e:Equipo) WHERE e.codigo IN $codigos RETURN collect(e.codigo) AS codigos"

CYPHER_REVISAR_EVENTO = """
MATCH (p:Partido {id: $partido})
OPTIONAL MATCH (ev:Evento {id: $id})
OPTIONAL MATCH (ev)-[:OCURRE_EN]->(de:Partido)
OPTIONAL MATCH (autor:Jugador)-[:PROTAGONIZA]->(ev)
OPTIONAL MATCH (j:Jugador {id: $jugador})-[:PERTENECE_A]->(:Equipo)-[:PARTICIPA_EN]->(p)
WITH p, ev, de, autor, j
OPTIONAL MATCH (previa:Evento)-[:OCURRE_EN]->(p) WHERE previa.id IN $influido_por
WITH p, ev, de, autor, j, collect(DISTINCT previa.id) AS previas_ok
OPTIONAL MATCH (origen:Evento)-[:INFLUYE_EN]->(ev)
RETURN p.estado AS estado,
       CASE WHEN ev IS NULL THEN null ELSE {tipo: ev.tipo, minuto: ev.minuto, orden: ev.orden, partido: de.id,
                                              jugador: autor.id} END AS existente,
       j.id AS jugador_ok, previas_ok, collect(DISTINCT origen.id) AS influido_por_existente
"""

CYPHER_REGISTRAR_EVENTO = """
MATCH (p:Partido {id: $partido})
MERGE (ev:Evento {id: $id})
ON CREATE SET ev.tipo = $tipo, ev.minuto = $minuto, ev.orden = $orden
MERGE (ev)-[:OCURRE_EN]->(p)
WITH ev
OPTIONAL MATCH (j:Jugador {id: $jugador})
FOREACH (_ IN CASE WHEN j IS NULL THEN [] ELSE [1] END | MERGE (j)-[:PROTAGONIZA]->(ev))
WITH DISTINCT ev
OPTIONAL MATCH (previa:Evento) WHERE previa.id IN $influido_por
FOREACH (_ IN CASE WHEN previa IS NULL THEN [] ELSE [1] END | MERGE (previa)-[:INFLUYE_EN]->(ev))
RETURN DISTINCT ev.id AS id
"""

CYPHER_GOLES = """
MATCH (ev:Evento {tipo: 'Gol'})-[:OCURRE_EN]->(:Partido {id: $id})
OPTIONAL MATCH (j:Jugador)-[:PROTAGONIZA]->(ev)
OPTIONAL MATCH (j)-[:PERTENECE_A]->(eq:Equipo)
RETURN eq.codigo AS equipo, count(ev) AS goles
"""

CYPHER_FINALIZAR = """
MATCH (p:Partido {id: $id})
SET p.estado = 'Finalizado', p.goles_local = $goles_local, p.goles_visitante = $goles_visitante
RETURN p.id AS id
"""


def _nativo(valor):
    """Las fechas de Neo4j llegan con un tipo propio del driver; la API trabaja con datetime."""
    if isinstance(valor, dict):
        return {k: _nativo(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_nativo(v) for v in valor]
    return valor.to_native() if hasattr(valor, "to_native") else valor


def _traducir(exc: Exception) -> ApiError | None:
    from neo4j.exceptions import DriverError, Neo4jError

    if "TimedOut" in str(getattr(exc, "code", "")):
        return DependenciaTimeout(FUENTE)
    if isinstance(exc, (DriverError, Neo4jError)):
        return DependenciaNoDisponible(FUENTE)
    return None


class Neo4jAdapter:
    """Grafo del fixture: Equipo, Jugador, Estadio, Partido, Evento y sus relaciones."""

    fuente = FUENTE

    def __init__(self, settings: Settings):
        self._s = settings
        self._driver = None

    def _drv(self):
        if self._driver is None:
            from neo4j import GraphDatabase

            t = self._s.timeout_segundos
            self._driver = GraphDatabase.driver(
                self._s.neo4j_uri,
                auth=(self._s.neo4j_user, self._s.neo4j_password),
                # Con el servidor inalcanzable estos tiempos se suman: se reparten para que el pedido
                # falle (503) más o menos dentro de `timeout_segundos` y no varias veces ese valor.
                connection_timeout=t / 2,
                connection_acquisition_timeout=t,
                max_transaction_retry_time=t / 3,
            )
        return self._driver

    def _ejecutar(self, cypher: str, escritura: bool, params: dict) -> list[dict]:
        from neo4j import unit_of_work

        # El servidor aborta la transacción al vencer. Las escrituras son operaciones de administración,
        # pocas y fuera del camino de los pronósticos: se les da más margen que a las lecturas.
        limite = self._s.timeout_segundos * (2.5 if escritura else 1)

        @unit_of_work(timeout=limite)
        def trabajo(tx):
            return [_nativo(dict(r)) for r in tx.run(cypher, **params)]

        with self._drv().session(database=self._s.neo4j_db) as sesion:
            return sesion.execute_write(trabajo) if escritura else sesion.execute_read(trabajo)

    def _leer(self, cypher: str, **params) -> list[dict]:
        return self._ejecutar(cypher, False, params)

    def _escribir(self, cypher: str, **params) -> list[dict]:
        return self._ejecutar(cypher, True, params)

    # --- lecturas del fixture ---
    def listar_partidos(self, fase: str | None = None, fecha=None, estado: str | None = None) -> list[dict]:
        from datetime import datetime, time, timedelta, timezone

        desde = datetime.combine(fecha, time.min, tzinfo=timezone.utc) if fecha else None
        hasta = desde + timedelta(days=1) if desde else None
        with operacion(FUENTE, "listar_partidos", _traducir):
            return self._leer(CYPHER_PARTIDOS, fase=fase, estado=estado, desde=desde, hasta=hasta)

    def obtener_partido(self, partido_id: str) -> dict | None:
        with operacion(FUENTE, "obtener_partido", _traducir):
            filas = self._leer(CYPHER_PARTIDO, id=partido_id)
            return filas[0] if filas else None

    def listar_eventos(self, partido_id: str, limit: int) -> list[dict] | None:
        with operacion(FUENTE, "listar_eventos", _traducir):
            filas = self._leer(CYPHER_EVENTOS, id=partido_id, limit=limit)
            return filas[0]["eventos"] if filas else None

    def cadena_de_evento(self, partido_id: str, evento_id: str) -> list[dict] | None:
        with operacion(FUENTE, "cadena_de_evento", _traducir):
            filas = self._leer(CYPHER_CADENA, partido=partido_id, evento=evento_id)
            return [f["evento"] for f in filas] if filas else None

    def camino_de_equipo(self, codigo: str) -> dict | None:
        with operacion(FUENTE, "camino_de_equipo", _traducir):
            filas = self._leer(CYPHER_PARTIDOS_DE_EQUIPO, codigo=codigo)
            if not filas:
                return None
            return {"equipo": filas[0]["equipo"], "partidos": filas[0]["partidos"],
                    "camino_a_la_final": self._leer(CYPHER_CAMINO_A_LA_FINAL, codigo=codigo)}

    def participacion_en_goles(self, limit: int) -> list[dict]:
        with operacion(FUENTE, "participacion_en_goles", _traducir):
            return self._leer(CYPHER_PARTICIPACION, limit=limit)

    # --- operación del partido ---
    def iniciar_partido(self, partido_id: str, ahora) -> bool:
        """Pasa de "Programado" a "En juego" y fija el inicio real. Repetirlo no cambia nada."""
        with operacion(FUENTE, "iniciar_partido", _traducir):
            return bool(self._escribir(CYPHER_INICIAR, id=partido_id, ahora=ahora))

    def asignar_equipos(self, partido_id: str, local: str, visitante: str) -> bool:
        with operacion(FUENTE, "asignar_equipos", _traducir):
            return bool(self._escribir(CYPHER_ASIGNAR_EQUIPOS, id=partido_id, local=local, visitante=visitante))

    def equipos_existentes(self, codigos: list[str]) -> set[str]:
        with operacion(FUENTE, "equipos_existentes", _traducir):
            return set(self._leer(CYPHER_EQUIPOS_EXISTEN, codigos=codigos)[0]["codigos"])

    def revisar_evento(self, partido_id: str, evento: dict) -> dict | None:
        """Lo necesario para decidir si la jugada se puede cargar. None si el partido no existe."""
        with operacion(FUENTE, "revisar_evento", _traducir):
            filas = self._leer(CYPHER_REVISAR_EVENTO, partido=partido_id, id=evento["id"],
                               jugador=evento.get("jugador"), influido_por=evento.get("influido_por") or [])
            return filas[0] if filas else None

    def registrar_evento(self, partido_id: str, evento: dict) -> None:
        with operacion(FUENTE, "registrar_evento", _traducir):
            self._escribir(CYPHER_REGISTRAR_EVENTO, partido=partido_id, id=evento["id"], tipo=evento["tipo"],
                           minuto=evento["minuto"], orden=evento["orden"], jugador=evento.get("jugador"),
                           influido_por=evento.get("influido_por") or [])

    def contar_goles(self, partido_id: str) -> dict[str, int]:
        """Goles cargados como jugadas, por equipo del jugador que los hizo."""
        with operacion(FUENTE, "contar_goles", _traducir):
            return {f["equipo"]: f["goles"] for f in self._leer(CYPHER_GOLES, id=partido_id)}

    def finalizar_partido(self, partido_id: str, goles_local: int, goles_visitante: int) -> None:
        with operacion(FUENTE, "finalizar_partido", _traducir):
            self._escribir(CYPHER_FINALIZAR, id=partido_id, goles_local=goles_local, goles_visitante=goles_visitante)

    def archivar_estadisticas(self, partido_id: str, resumen: list[dict], muestras: list[dict], jugadas: list[dict]) -> None:
        """Guarda una versión completa e idempotente en una sola transacción."""
        cypher = """
        MATCH (p:Partido {id: $partido, estado: 'Finalizado'})
        MATCH (equipo:Equipo)-[:PARTICIPA_EN]->(p)
        WHERE equipo.codigo IN $codigos
        WITH p, count(DISTINCT equipo) AS cantidad
        WHERE cantidad = 2
        SET p.id = p.id
        WITH p
        CALL (p) {
            UNWIND $jugadas AS fila
            OPTIONAL MATCH (j:Jugador {id: fila.jugador})-[:PERTENECE_A]->(:Equipo {codigo: fila.equipo_id})-[:PARTICIPA_EN]->(p)
            OPTIONAL MATCH (existente:Evento {id: fila.id})
            OPTIONAL MATCH (existente)-[:OCURRE_EN]->(de:Partido)
            OPTIONAL MATCH (autor:Jugador)-[:PROTAGONIZA]->(existente)
            WITH fila, j, existente, de, autor, p
            RETURN count(DISTINCT CASE WHEN j IS NOT NULL AND
                (existente IS NULL OR (de = p AND autor = j AND existente.tipo = fila.tipo
                AND existente.minuto = fila.minuto AND existente.orden = fila.orden))
                THEN fila.id ELSE null END) AS validas
        }
        WITH p, validas WHERE validas = size($jugadas)
        SET p.archivo_estadisticas_version = 1
        WITH p
        CALL (p) {
            UNWIND $resumen AS fila
            MATCH (e:Equipo {codigo: fila.equipo_id})-[:PARTICIPA_EN]->(p)
            MERGE (p)-[r:RESUMEN_ESTADISTICO]->(e)
            SET r += fila
            RETURN count(r) AS resumenes
        }
        CALL (p) {
            UNWIND $muestras AS fila
            MATCH (e:Equipo {codigo: fila.equipo_id})-[:PARTICIPA_EN]->(p)
            MERGE (p)-[r:ESTADISTICA_MINUTO {minuto: fila.minuto}]->(e)
            SET r += fila
            RETURN count(r) AS puntos
        }
        CALL (p) {
            UNWIND $jugadas AS fila
            MATCH (j:Jugador {id: fila.jugador})-[:PERTENECE_A]->(:Equipo {codigo: fila.equipo_id})-[:PARTICIPA_EN]->(p)
            MERGE (ev:Evento {id: fila.id})
            ON CREATE SET ev.tipo = fila.tipo, ev.minuto = fila.minuto, ev.orden = fila.orden
            MERGE (ev)-[:OCURRE_EN]->(p)
            MERGE (j)-[:PROTAGONIZA]->(ev)
            RETURN count(DISTINCT ev) AS eventos
        }
        CALL (p) {
            UNWIND $enlaces AS enlace
            MATCH (anterior:Evento {id: enlace.anterior})-[:OCURRE_EN]->(p)
            MATCH (siguiente:Evento {id: enlace.siguiente})-[:OCURRE_EN]->(p)
            MERGE (anterior)-[r:INFLUYE_EN]->(siguiente)
            RETURN count(r) AS relaciones
        }
        RETURN resumenes, puntos, eventos, relaciones
        """
        enlaces = [{"anterior": previa, "siguiente": j["id"]} for j in jugadas for previa in j.get("influido_por", [])]
        with operacion(FUENTE, "archivar_estadisticas", _traducir):
            filas = self._escribir(cypher, partido=partido_id, codigos=[r["equipo_id"] for r in resumen], resumen=resumen, muestras=muestras, jugadas=jugadas, enlaces=enlaces)
            if not filas or filas[0]["resumenes"] != len(resumen) or filas[0]["puntos"] != len(muestras) or filas[0]["eventos"] != len(jugadas) or filas[0]["relaciones"] != len(enlaces):
                from app.errors import Conflicto
                raise Conflicto("No se pudo archivar: revisá los equipos, jugadores y conflictos de IDs en Neo4j.")

    def leer_estadisticas_archivadas(self, partido_id: str) -> dict | None:
        cypher = """
        MATCH (p:Partido {id: $partido})-[r:RESUMEN_ESTADISTICO]->(e:Equipo)
        WITH p, collect(properties(r)) AS equipos
        OPTIONAL MATCH (p)-[m:ESTADISTICA_MINUTO]->(equipo:Equipo)
        WITH equipos, m ORDER BY m.minuto, m.equipo_id
        RETURN equipos, collect(properties(m)) AS muestras
        """
        with operacion(FUENTE, "leer_estadisticas_archivadas", _traducir):
            filas = self._leer(cypher, partido=partido_id)
            return filas[0] if filas else None

    def preparar_consultas(self) -> int:
        """Hace que Neo4j planifique todas las consultas de la API sin ejecutarlas (EXPLAIN).

        La primera vez que Neo4j ve una consulta tiene que armar su plan, y en este laboratorio eso puede
        tardar más que el tiempo de espera de un pedido. Con esto el plan ya está guardado cuando llega el
        primer pedido real. Devuelve cuántas consultas preparó.
        """
        consultas = [valor for nombre, valor in globals().items() if nombre.startswith("CYPHER_")]
        parametros = dict.fromkeys(
            ("id", "partido", "evento", "codigo", "local", "visitante", "jugador", "fase", "estado", "desde",
             "hasta", "ahora", "tipo"), None) | {"limit": 1, "codigos": [], "influido_por": [], "minuto": 0,
                                                 "orden": 0, "goles_local": 0, "goles_visitante": 0}
        with self._drv().session(database=self._s.neo4j_db) as sesion:
            for cypher in consultas:
                sesion.run("EXPLAIN " + cypher, parametros).consume()
        return len(consultas)

    def ping(self) -> None:
        with operacion(FUENTE, "ping", _traducir):
            self._drv().verify_connectivity()
