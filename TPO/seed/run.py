"""Carga los datos de laboratorio en MongoDB y Neo4j.

    python -m seed.run                      carga (o recarga) sin mover el calendario ya cargado
    python -m seed.run --inicio 2030-06-13T15:00:00+00:00
    python -m seed.run --dias-hasta-inicio 3
    python -m seed.run --verificar          carga dos veces y falla si los totales cambian
    python -m seed.run --reiniciar          BORRA los datos de laboratorio (MongoDB, Neo4j, los comentarios de
                                            Cassandra y lo que cuenta la audiencia en Redis) y carga de nuevo
"""
import argparse
import sys
from datetime import datetime, timedelta, timezone

from neo4j import GraphDatabase
from pymongo import MongoClient

from app.config.settings import Settings
from seed import cargar_mongo, cargar_neo4j, datos


COLECCIONES = ["usuarios", "prodes", "pronosticos", "resultados", "puntajes", "rankings_historicos",
               "equipos", "jugadores", "contadores",
               "simulaciones"]  # estado de cada simulación: sin borrarlo, un partido reiniciado no se puede volver a simular


# Lo que la audiencia y los comentarios dejan en Redis por partido. Las sesiones no se tocan.
PREFIJOS_DE_PARTIDO = ("unicos:", "paises:", "audiencia:", "cuenta:", "visto:", "lento:", "prode:ranking")


def borrar_audiencia_de_redis(redis) -> int:
    """Sin esto, volver a simular un partido sumaría los espectadores únicos de la corrida anterior."""
    claves = [c for prefijo in PREFIJOS_DE_PARTIDO for c in redis.scan_iter(match=f"{prefijo}*")]
    for desde in range(0, len(claves), 1000):
        redis.delete(*claves[desde:desde + 1000])
    return len(claves)


TABLAS_DE_COMENTARIOS = ("comentarios_por_partido_pais", "paises_por_partido")


def borrar_comentarios_de_cassandra(ejecutar) -> None:
    """Sin esto, volver a jugar un partido mostraría en su historial los comentarios de la vez anterior.
    `ejecutar` recibe el texto CQL. TRUNCATE necesita que respondan las dos regiones."""
    for tabla in TABLAS_DE_COMENTARIOS:
        ejecutar(f"TRUNCATE fixture2030.{tabla}")


def _inicio(args, driver, base: str) -> datetime:
    if args.inicio:
        inicio = datetime.fromisoformat(args.inicio)
        return inicio if inicio.tzinfo else inicio.replace(tzinfo=timezone.utc)
    if args.dias_hasta_inicio is None:
        cargado = cargar_neo4j.inicio_cargado(driver, base)
        if cargado:
            return cargado
    dias = 3 if args.dias_hasta_inicio is None else args.dias_hasta_inicio
    return (datetime.now(timezone.utc) + timedelta(days=dias)).replace(minute=0, second=0, microsecond=0)


def main() -> int:
    parser = argparse.ArgumentParser(description="Carga de datos de laboratorio del prode 2030")
    parser.add_argument("--inicio", help="fecha y hora (ISO) del primer partido sin jugar, P-03")
    parser.add_argument("--dias-hasta-inicio", type=int, help="ubica P-03 a esta cantidad de días desde ahora")
    parser.add_argument("--semilla", type=int, default=2030)
    parser.add_argument("--verificar", action="store_true", help="carga dos veces y compara los totales")
    parser.add_argument("--reiniciar", action="store_true",
                        help="borra usuarios, prodes, pronósticos, resultados, puntajes y el grafo antes de cargar")
    args = parser.parse_args()

    s = Settings()
    cliente = MongoClient(s.mongo_uri, w="majority", tz_aware=True)
    db = cliente[s.mongo_db]
    with GraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password)) as driver:
        if args.reiniciar:
            for nombre in COLECCIONES:
                db.drop_collection(nombre)
            with driver.session(database=s.neo4j_db) as sesion:
                sesion.run("MATCH (n) DETACH DELETE n").consume()
            from app.adapters.redis import RedisAdapter

            borradas = borrar_audiencia_de_redis(RedisAdapter(s).cli)
            print(f"Datos de laboratorio borrados (base {s.mongo_db} de MongoDB, grafo de Neo4j y {borradas} claves "
                  "de audiencia en Redis).")
            try:
                from app.adapters.cassandra import CassandraAdapter

                sesion = CassandraAdapter(s)._sesion("america")
                borrar_comentarios_de_cassandra(lambda cql: sesion.execute(cql, timeout=60))
                print("Comentarios de Cassandra borrados.")
            except Exception as exc:
                print(f"AVISO: no se pudieron borrar los comentarios de Cassandra ({type(exc).__name__}). "
                      "Hacen falta las dos regiones levantadas; los comentarios anteriores siguen ahí.", file=sys.stderr)
        inicio = _inicio(args, driver, s.neo4j_db)
        fixture = datos.generar(inicio, args.semilla)
        print(f"Primer partido sin jugar (P-03): {inicio.isoformat()}")

        corridas = []
        for numero in (1, 2) if args.verificar else (1,):
            cargar_mongo.preparar(db)
            totales = {"mongodb": cargar_mongo.cargar(db, fixture),
                       "neo4j": cargar_neo4j.cargar(driver, s.neo4j_db, fixture)}
            corridas.append(totales)
            print(f"Carga {numero}:")
            for base, valores in totales.items():
                print(f"  {base}: " + ", ".join(f"{k}={v}" for k, v in valores.items()))
    cliente.close()

    if args.verificar:
        if corridas[0] != corridas[1]:
            print("ERROR: los totales cambiaron entre la primera y la segunda carga.", file=sys.stderr)
            return 1
        print("Verificado: la segunda carga dejó exactamente los mismos totales.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
