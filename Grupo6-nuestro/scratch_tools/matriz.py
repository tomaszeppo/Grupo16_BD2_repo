import json

PESOS = [20, 25, 20, 20, 15]
CRITERIOS = ["Capacidad y volumen", "Performance", "Consistencia", "Escalabilidad y almacenamiento", "Consulta y modelado"]
MOTORES = ["MongoDB", "Neo4j", "Redis", "Cassandra", "IRIS", "InfluxDB"]

# Valoraciones de 1 a 5 en el orden de CRITERIOS. Las tres primeras necesidades
# tienen las valoraciones que el grupo ya habia cargado en el Hito 2; las otras
# tres se completan con el mismo criterio.
NECESIDADES = {
    "Logs generados durante el partido": {
        "MongoDB": [4, 4, 4, 4, 4], "Neo4j": [2, 2, 4, 2, 2], "Redis": [3, 5, 4, 4, 3],
        "Cassandra": [5, 5, 3, 5, 3], "IRIS": [3, 4, 4, 3, 5], "InfluxDB": [3, 4, 3, 4, 4]},
    "Partidos y valores en tiempo real": {
        "MongoDB": [4, 5, 4, 4, 4], "Neo4j": [2, 2, 4, 2, 2], "Redis": [3, 5, 4, 4, 5],
        "Cassandra": [4, 4, 3, 5, 3], "IRIS": [4, 4, 4, 4, 3], "InfluxDB": [3, 4, 3, 4, 4]},
    "Partidos finalizados y datos estáticos": {
        "MongoDB": [4, 4, 4, 4, 5], "Neo4j": [3, 3, 4, 3, 4], "Redis": [2, 5, 3, 3, 2],
        "Cassandra": [5, 4, 3, 5, 2], "IRIS": [4, 4, 5, 4, 4], "InfluxDB": [3, 4, 3, 4, 3]},
    "Grupos y puntajes": {
        "MongoDB": [4, 5, 4, 4, 4], "Neo4j": [2, 2, 4, 2, 2], "Redis": [3, 5, 4, 4, 3],
        "Cassandra": [4, 4, 3, 5, 3], "IRIS": [4, 4, 5, 5, 5], "InfluxDB": [3, 4, 3, 4, 4]},
    "Predicciones de usuarios": {
        "MongoDB": [4, 4, 4, 4, 4], "Neo4j": [3, 3, 5, 3, 5], "Redis": [2, 5, 3, 3, 2],
        "Cassandra": [5, 4, 3, 5, 2], "IRIS": [4, 4, 5, 4, 4], "InfluxDB": [3, 4, 3, 4, 3]},
    "Métricas y estadísticas históricas": {
        "MongoDB": [4, 3, 4, 4, 4], "Neo4j": [2, 2, 4, 2, 3], "Redis": [2, 5, 3, 3, 2],
        "Cassandra": [5, 4, 3, 5, 2], "IRIS": [3, 3, 5, 3, 4], "InfluxDB": [4, 5, 3, 4, 4]},
}

ELEGIDO = {
    "Logs generados durante el partido": "Cassandra",
    "Partidos y valores en tiempo real": "Redis",
    "Partidos finalizados y datos estáticos": "MongoDB",
    "Grupos y puntajes": "IRIS",
    "Predicciones de usuarios": "Neo4j",
    "Métricas y estadísticas históricas": "InfluxDB",
}


def total(v):
    return sum(p * s for p, s in zip(PESOS, v)) / 100


def estrellas(n):
    return "★" * n + "☆" * (5 - n)


def tabla(nec):
    filas = ["| Motor | " + " | ".join("%s (%d %%)" % (c, p) for c, p in zip(CRITERIOS, PESOS)) + " | Total ponderado |",
             "| :--- | " + " | ".join(":---:" for _ in CRITERIOS) + " | ---: |"]
    orden = sorted(MOTORES, key=lambda m: -total(NECESIDADES[nec][m]))
    for m in orden:
        v = NECESIDADES[nec][m]
        filas.append("| %s | " % m + " | ".join(str(x) for x in v) + " | **" + ("%.2f" % total(v)).replace(".", ",") + "** |")
    return "\n".join(filas), orden


if __name__ == "__main__":
    resumen = {}
    for nec in NECESIDADES:
        t, orden = tabla(nec)
        resumen[nec] = {"orden": [(m, round(total(NECESIDADES[nec][m]), 2)) for m in orden], "elegido": ELEGIDO[nec]}
    print(json.dumps(resumen, ensure_ascii=False, indent=1))
