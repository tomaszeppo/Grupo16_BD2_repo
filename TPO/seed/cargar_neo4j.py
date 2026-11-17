"""Carga el fixture en Neo4j. Todo con MERGE: repetirla no duplica nodos ni relaciones."""
from seed.datos import Fixture

RESTRICCIONES = [
    "CREATE CONSTRAINT equipo_codigo IF NOT EXISTS FOR (e:Equipo) REQUIRE e.codigo IS UNIQUE",
    "CREATE CONSTRAINT jugador_id IF NOT EXISTS FOR (j:Jugador) REQUIRE j.id IS UNIQUE",
    "CREATE CONSTRAINT estadio_id IF NOT EXISTS FOR (e:Estadio) REQUIRE e.id IS UNIQUE",
    "CREATE CONSTRAINT partido_id IF NOT EXISTS FOR (p:Partido) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT evento_id IF NOT EXISTS FOR (e:Evento) REQUIRE e.id IS UNIQUE",
    "CREATE INDEX partido_fecha IF NOT EXISTS FOR (p:Partido) ON (p.fecha_hora)",
]

EQUIPOS = "UNWIND $filas AS f MERGE (e:Equipo {codigo: f.codigo}) SET e.nombre = f.nombre, e.grupo = f.grupo"

JUGADORES = """
UNWIND $filas AS f
MERGE (j:Jugador {id: f.id})
SET j.nombre = f.nombre, j.apellido = f.apellido, j.dorsal = f.dorsal, j.posicion = f.posicion
WITH j, f MATCH (e:Equipo {codigo: f.equipo})
MERGE (j)-[:PERTENECE_A]->(e)
"""

ESTADIOS = "UNWIND $filas AS f MERGE (e:Estadio {id: f.id}) SET e.nombre = f.nombre, e.ciudad = f.ciudad"

# Estado, inicio real y marcador solo se escriben al crear el partido: una recarga no pisa lo que pasó después.
# El horario se puede reubicar mientras el partido siga programado.
PARTIDOS = """
UNWIND $filas AS f
MERGE (p:Partido {id: f.id})
ON CREATE SET p.estado = f.estado, p.inicio_real = f.inicio_real,
              p.goles_local = f.goles_local, p.goles_visitante = f.goles_visitante, p.fecha_hora = f.fecha_hora
SET p.fase = f.fase,
    p.fecha_hora = CASE WHEN p.estado = 'Programado' THEN f.fecha_hora ELSE p.fecha_hora END
WITH p, f MATCH (est:Estadio {id: f.estadio})
MERGE (p)-[:SE_JUEGA_EN]->(est)
"""

PARTICIPANTES = """
UNWIND $filas AS f
MATCH (p:Partido {id: f.partido}), (e:Equipo {codigo: f.equipo})
MERGE (e)-[r:PARTICIPA_EN]->(p)
SET r.condicion = f.condicion
"""

CUADRO = """
UNWIND $filas AS f
MATCH (a:Partido {id: f.origen}), (b:Partido {id: f.destino})
MERGE (a)-[r:CLASIFICA_A]->(b)
SET r.como = f.como
"""

EVENTOS = """
UNWIND $filas AS f
MATCH (p:Partido {id: f.partido})
MERGE (ev:Evento {id: f.id})
SET ev.tipo = f.tipo, ev.minuto = f.minuto, ev.orden = f.orden
MERGE (ev)-[:OCURRE_EN]->(p)
WITH ev, f
OPTIONAL MATCH (j:Jugador {id: f.jugador})
FOREACH (_ IN CASE WHEN j IS NULL THEN [] ELSE [1] END | MERGE (j)-[:PROTAGONIZA]->(ev))
"""

INFLUENCIAS = """
UNWIND $filas AS f
MATCH (a:Evento {id: f.origen}), (b:Evento {id: f.destino})
MERGE (a)-[:INFLUYE_EN]->(b)
"""

ETIQUETAS = ["Equipo", "Jugador", "Estadio", "Partido", "Evento"]
RELACIONES = ["PERTENECE_A", "PARTICIPA_EN", "SE_JUEGA_EN", "OCURRE_EN", "PROTAGONIZA", "INFLUYE_EN", "CLASIFICA_A"]


def cargar(driver, base: str, fixture: Fixture) -> dict[str, int]:
    participantes = [
        {"partido": p["id"], "equipo": p[condicion], "condicion": condicion}
        for p in fixture.partidos for condicion in ("local", "visitante") if p[condicion]
    ]
    eventos = [{**e, "partido": pid} for pid, lista in fixture.eventos.items() for e in lista]
    influencias = [{"origen": e["id"], "destino": e["influye_en"]} for e in eventos if e["influye_en"]]
    cuadro = [{"origen": o, "destino": d, "como": como} for o, d, como in fixture.cuadro]

    with driver.session(database=base) as sesion:
        for restriccion in RESTRICCIONES:
            sesion.run(restriccion).consume()
        for cypher, filas in (
            (EQUIPOS, fixture.equipos), (JUGADORES, fixture.jugadores), (ESTADIOS, fixture.estadios),
            (PARTIDOS, fixture.partidos), (PARTICIPANTES, participantes), (CUADRO, cuadro),
            (EVENTOS, eventos), (INFLUENCIAS, influencias),
        ):
            for desde in range(0, len(filas), 500):
                sesion.run(cypher, filas=filas[desde:desde + 500]).consume()
    return totales(driver, base)


def totales(driver, base: str) -> dict[str, int]:
    salida = {}
    with driver.session(database=base) as sesion:
        for etiqueta in ETIQUETAS:
            salida[etiqueta] = sesion.run(f"MATCH (n:{etiqueta}) RETURN count(n) AS n").single()["n"]
        for relacion in RELACIONES:
            salida[relacion] = sesion.run(f"MATCH ()-[r:{relacion}]->() RETURN count(r) AS n").single()["n"]
    return salida


def inicio_cargado(driver, base: str):
    """Hora de P-03 si el fixture ya está cargado: es la referencia de todo el calendario."""
    with driver.session(database=base) as sesion:
        fila = sesion.run("MATCH (p:Partido {id: 'P-03'}) RETURN p.fecha_hora AS f").single()
    return fila["f"].to_native() if fila and fila["f"] else None
