"""Datos sintéticos del Fixture 2030 para la API. Esquemas de `main`; identificadores P-NN y códigos FIFA."""

EQUIPOS = [
    ("ARG", "Argentina"), ("BRA", "Brasil"), ("ESP", "España"), ("FRA", "Francia"),
    ("GER", "Alemania"), ("ENG", "Inglaterra"), ("ITA", "Italia"), ("POR", "Portugal"),
    ("NED", "Países Bajos"), ("BEL", "Bélgica"), ("CRO", "Croacia"), ("URU", "Uruguay"),
    ("MEX", "México"), ("USA", "Estados Unidos"), ("CAN", "Canadá"), ("JPN", "Japón"),
]
_APELLIDOS = ["Alvarez", "Silva", "Garcia", "Dubois", "Muller", "Smith", "Rossi", "Santos",
              "De Jong", "Janssen", "Kovac", "Perez", "Hernandez", "Johnson", "Tremblay", "Sato"]
_NOMBRES = ["Lucas", "Mateo", "Nicolas", "Diego", "Tomas"]
_POSICIONES = ["Portero", "Defensa", "Centrocampista", "Delantero", "Delantero"]

ESTADIOS = [
    ("EST001", "Estadio Monumental", "Buenos Aires"), ("EST002", "Maracaná", "Río de Janeiro"),
    ("EST003", "Camp Nou", "Barcelona"), ("EST004", "Wembley", "Londres"),
    ("EST005", "Stade de France", "París"), ("EST006", "Allianz Arena", "Múnich"),
    ("EST007", "Azteca", "Ciudad de México"), ("EST008", "Lusail Stadium", "Lusail"),
]

PARTIDOS = [
    {"id": f"P-{i:02d}", "local": l, "visitante": v, "estadio": f"EST00{i}",
     "fecha": f"2030-06-{14 + (i + 3) // 4}", "fase": "Fase de grupos"}
    for i, (l, v) in enumerate(
        [("ARG", "BRA"), ("ESP", "FRA"), ("GER", "ENG"), ("ITA", "POR"),
         ("NED", "BEL"), ("CRO", "URU"), ("MEX", "USA"), ("CAN", "JPN")], start=1)
]

EVENTOS = {  # Neo4j: Evento{id,tipo,minuto} -[:OCURRE_EN]-> Partido
    "P-01": [("Inicio", 0), ("Gol", 32), ("Final", 90)],
    "P-02": [("Inicio", 0), ("Final", 90)],
}
RESULTADOS = {"P-01": ("ARG", "BRA", 2, 1), "P-02": ("FRA", "ESP", 1, 0)}  # marcadores simulados (origen SIMULADO)

# IRIS: P-01 en juego con eventos; el resto programado. Minuto >= 1 (regla de Fixture.Partido.AgregarEvento).
IRIS_EVENTOS = {"P-01": [("Gol", 32, "J-ARG-01"), ("Gol", 61, "J-BRA-04")]}
IRIS_ESTADO_INICIAL = {"P-01": "En juego"}

SESIONES = [("U001", "ACTIVA"), ("U002", "CERRADA"), ("U003", "ACTIVA")]  # usuario, estado_acceso


def jugadores() -> list[dict]:
    salida = []
    for idx, (codigo, _) in enumerate(EQUIPOS):
        for n in range(5):
            salida.append({
                "nombre": _NOMBRES[n], "apellido": _APELLIDOS[idx], "dorsal": n + 1,
                "equipo": codigo, "posicion": _POSICIONES[n],
            })
    return salida
