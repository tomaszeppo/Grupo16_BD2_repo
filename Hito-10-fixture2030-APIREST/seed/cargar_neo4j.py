from neo4j import GraphDatabase

from app.config.settings import Settings
from seed import datos

CONSTRAINTS = [
    "CREATE CONSTRAINT equipo_codigo IF NOT EXISTS FOR (e:Equipo) REQUIRE e.codigo IS UNIQUE",
    "CREATE CONSTRAINT partido_id IF NOT EXISTS FOR (p:Partido) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT estadio_id IF NOT EXISTS FOR (e:Estadio) REQUIRE e.id IS UNIQUE",
    "CREATE CONSTRAINT evento_id IF NOT EXISTS FOR (e:Evento) REQUIRE e.id IS UNIQUE",
]


def cargar(s: Settings) -> str:
    with GraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password)) as drv, drv.session(
        database=s.neo4j_db
    ) as ses:
        for c in CONSTRAINTS:
            ses.run(c)
        for codigo, nombre in datos.EQUIPOS:
            ses.run("MERGE (e:Equipo {codigo:$c}) SET e.nombre=$n", c=codigo, n=nombre)
        for id_, nombre, ciudad in datos.ESTADIOS:
            ses.run("MERGE (e:Estadio {id:$i}) SET e.nombre=$n, e.ciudad=$c", i=id_, n=nombre, c=ciudad)
        for p in datos.PARTIDOS:
            ses.run(
                """MERGE (p:Partido {id:$id}) SET p.fecha=$fecha, p.fase=$fase
                   WITH p MATCH (l:Equipo {codigo:$local}), (v:Equipo {codigo:$vis}), (est:Estadio {id:$est})
                   MERGE (l)-[:PARTICIPA_EN]->(p) MERGE (v)-[:PARTICIPA_EN]->(p) MERGE (p)-[:SE_JUEGA_EN]->(est)""",
                id=p["id"], fecha=p["fecha"], fase=p["fase"], local=p["local"], vis=p["visitante"], est=p["estadio"],
            )
        for pid, (g, per, gg, gp) in datos.RESULTADOS.items():
            ses.run(
                "MATCH (p:Partido {id:$id}) SET p.equipoGanador=$g, p.equipoPerdedor=$p, p.golesGanador=$gg, "
                "p.golesPerdedor=$gp, p.origenResultado='SIMULADO'",
                id=pid, g=g, p=per, gg=gg, gp=gp,
            )
        for pid, eventos in datos.EVENTOS.items():
            for tipo, minuto in eventos:
                ses.run(
                    "MATCH (p:Partido {id:$pid}) MERGE (ev:Evento {id:$eid}) SET ev.tipo=$t, ev.minuto=$m "
                    "MERGE (ev)-[:OCURRE_EN]->(p)",
                    pid=pid, eid=f"EV-{pid}-{tipo.upper()}", t=tipo, m=minuto,
                )
        n = ses.run("MATCH (p:Partido) RETURN count(p) AS n").single()["n"]
    return f"{n} partidos"
