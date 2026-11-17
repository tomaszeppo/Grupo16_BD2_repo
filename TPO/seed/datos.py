"""Datos de laboratorio del Mundial 2030. Todo es sintético y sale igual con la misma semilla.

Los equipos llevan nombres de países reales para que el fixture se lea fácil; grupos, planteles,
horarios, estadios y resultados son inventados.
"""
import random
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.dominio.ids import id_partido

EQUIPOS = [
    ("ARG", "Argentina"), ("BRA", "Brasil"), ("URU", "Uruguay"), ("COL", "Colombia"),
    ("ECU", "Ecuador"), ("PAR", "Paraguay"), ("CHI", "Chile"), ("PER", "Perú"),
    ("ESP", "España"), ("POR", "Portugal"), ("FRA", "Francia"), ("GER", "Alemania"),
    ("ENG", "Inglaterra"), ("ITA", "Italia"), ("NED", "Países Bajos"), ("BEL", "Bélgica"),
    ("CRO", "Croacia"), ("SUI", "Suiza"), ("DEN", "Dinamarca"), ("POL", "Polonia"),
    ("SRB", "Serbia"), ("AUT", "Austria"), ("SWE", "Suecia"), ("NOR", "Noruega"),
    ("MAR", "Marruecos"), ("SEN", "Senegal"), ("NGA", "Nigeria"), ("EGY", "Egipto"),
    ("GHA", "Ghana"), ("CMR", "Camerún"), ("CIV", "Costa de Marfil"), ("TUN", "Túnez"),
    ("ALG", "Argelia"), ("RSA", "Sudáfrica"), ("MEX", "México"), ("USA", "Estados Unidos"),
    ("CAN", "Canadá"), ("CRC", "Costa Rica"), ("PAN", "Panamá"), ("JAM", "Jamaica"),
    ("JPN", "Japón"), ("KOR", "Corea del Sur"), ("AUS", "Australia"), ("IRN", "Irán"),
    ("KSA", "Arabia Saudita"), ("QAT", "Catar"), ("UZB", "Uzbekistán"), ("NZL", "Nueva Zelanda"),
]
GRUPOS = "ABCDEFGHIJKL"

ESTADIOS = [
    ("Estadio del Río", "Buenos Aires"), ("Estadio de la Rambla", "Montevideo"),
    ("Estadio del Lago", "Asunción"), ("Estadio de la Castellana", "Madrid"),
    ("Estadio del Puerto", "Barcelona"), ("Estadio de la Ría", "Bilbao"),
    ("Estadio del Guadalquivir", "Sevilla"), ("Estadio de la Costa", "Málaga"),
    ("Estadio del Ebro", "Zaragoza"), ("Estadio del Tajo", "Lisboa"),
    ("Estadio del Duero", "Oporto"), ("Estadio del Atlas", "Casablanca"),
    ("Estadio de la Medina", "Rabat"), ("Estadio del Estrecho", "Tánger"),
    ("Estadio de las Palmeras", "Marrakech"), ("Estadio del Sur", "Agadir"),
]

_NOMBRES = ["Lucas", "Mateo", "Nicolás", "Diego", "Tomás", "Bruno", "Joaquín", "Martín", "Franco", "Santiago",
            "Emilio", "Rafael", "Iván", "Hugo", "Leandro", "Gael", "Simón", "Dante", "Álvaro", "Julián",
            "Renzo", "Luca", "Ezequiel", "Facundo", "Ignacio", "Valentín"]
_APELLIDOS = ["Acosta", "Benítez", "Cabrera", "Duarte", "Escobar", "Ferreyra", "Giménez", "Herrera", "Ibáñez",
              "Juárez", "Ledesma", "Maidana", "Navarro", "Ojeda", "Paredes", "Quiroga", "Romero", "Sosa",
              "Toledo", "Urquiza", "Vera", "Zárate", "Molina", "Peralta", "Rojas", "Suárez", "Aguirre",
              "Bustos", "Correa", "Domínguez"]
# 26 por plantel: 3 arqueros, 9 defensores, 8 mediocampistas, 6 delanteros
_POSICIONES = ["Arquero"] * 3 + ["Defensor"] * 9 + ["Mediocampista"] * 8 + ["Delantero"] * 6

FASES = ["Fase de grupos", "Dieciseisavos", "Octavos", "Cuartos", "Semifinal", "Tercer puesto", "Final"]
TIPOS_DE_EVENTO = ["Inicio", "Pase", "Tiro", "Gol", "Falta", "Tarjeta amarilla", "Tarjeta roja", "Cambio", "Final"]
PARTIDOS_DE_MUESTRA = ("P-01", "P-02")

# Cruces dentro de un grupo de cuatro, por jornada
_JORNADAS = [((0, 1), (2, 3)), ((0, 2), (1, 3)), ((0, 3), (1, 2))]


@dataclass
class Fixture:
    equipos: list[dict]
    jugadores: list[dict]
    estadios: list[dict]
    partidos: list[dict]
    cuadro: list[tuple[str, str, str]]  # (partido de origen, partido de destino, "ganador" | "perdedor")
    eventos: dict[str, list[dict]]


def generar(inicio: datetime, semilla: int = 2030) -> Fixture:
    """Arma el fixture completo. `inicio` es la hora del primer partido que todavía no se jugó (P-03).

    P-01 y P-02 son la muestra: se jugaron el día anterior y traen sus jugadas y su marcador.
    """
    rng = random.Random(semilla)
    equipos = [{"codigo": c, "nombre": n, "grupo": GRUPOS[i // 4]} for i, (c, n) in enumerate(EQUIPOS)]
    jugadores = _jugadores(rng)
    estadios = [{"id": f"EST{i:02d}", "nombre": n, "ciudad": c} for i, (n, c) in enumerate(ESTADIOS, start=1)]
    partidos, cuadro = _partidos(equipos, estadios, inicio)

    eventos = {}
    plantel = {}
    for j in jugadores:
        plantel.setdefault(j["equipo"], []).append(j["id"])
    for partido in partidos:
        if partido["id"] in PARTIDOS_DE_MUESTRA:
            jugadas, goles_local, goles_visitante = _jugadas(rng, partido, plantel)
            eventos[partido["id"]] = jugadas
            partido.update(estado="Finalizado", inicio_real=partido["fecha_hora"],
                           goles_local=goles_local, goles_visitante=goles_visitante)
    return Fixture(equipos, jugadores, estadios, partidos, cuadro, eventos)


def _jugadores(rng: random.Random) -> list[dict]:
    salida = []
    for codigo, _ in EQUIPOS:
        nombres = rng.sample(_NOMBRES, 26)
        apellidos = [rng.choice(_APELLIDOS) for _ in range(26)]
        for n in range(26):
            salida.append({
                "id": f"J-{codigo}-{n + 1:02d}", "nombre": nombres[n], "apellido": apellidos[n],
                "dorsal": n + 1, "posicion": _POSICIONES[n], "equipo": codigo,
            })
    return salida


def _partidos(equipos: list[dict], estadios: list[dict], inicio: datetime) -> tuple[list[dict], list[tuple]]:
    cruces = []
    for jornada in _JORNADAS:
        for g in range(12):
            del_grupo = [e["codigo"] for e in equipos[g * 4:g * 4 + 4]]
            for a, b in jornada:
                cruces.append(("Fase de grupos", del_grupo[a], del_grupo[b]))
    cruces += [("Dieciseisavos", None, None)] * 16 + [("Octavos", None, None)] * 8 + [("Cuartos", None, None)] * 4
    cruces += [("Semifinal", None, None)] * 2 + [("Tercer puesto", None, None), ("Final", None, None)]

    partidos = []
    for i, (fase, local, visitante) in enumerate(cruces):
        partidos.append({
            "id": id_partido(i + 1), "fecha_hora": _fecha(i, inicio), "fase": fase, "estado": "Programado",
            "local": local, "visitante": visitante, "estadio": estadios[i % len(estadios)]["id"],
            "inicio_real": None, "goles_local": None, "goles_visitante": None,
        })

    cuadro = []

    def enlazar(primer_origen: int, primer_destino: int, cantidad_destinos: int):
        for k in range(cantidad_destinos):
            for origen in (primer_origen + 2 * k, primer_origen + 2 * k + 1):
                cuadro.append((id_partido(origen), id_partido(primer_destino + k), "ganador"))

    enlazar(73, 89, 8)  # dieciseisavos → octavos
    enlazar(89, 97, 4)  # octavos → cuartos
    enlazar(97, 101, 2)  # cuartos → semifinales
    enlazar(101, 104, 1)  # semifinales → final
    cuadro += [("P-101", "P-103", "perdedor"), ("P-102", "P-103", "perdedor")]
    return partidos, cuadro


def _fecha(indice: int, inicio: datetime) -> datetime:
    """Cuatro partidos por día, cada tres horas. Las eliminatorias dejan un día libre entre rondas."""
    if indice < 2:  # la muestra, jugada el día anterior
        return inicio - timedelta(days=1) + timedelta(hours=3 * indice)
    j = indice - 2
    descanso = sum(1 for corte in (70, 86, 94, 98, 100) if j >= corte)  # índice (sin la muestra) donde arranca cada ronda
    return inicio + timedelta(days=j // 4 + descanso, hours=3 * (j % 4))


def _jugadas(rng: random.Random, partido: dict, plantel: dict) -> tuple[list[dict], int, int]:
    """Jugadas de un partido de muestra, con las cadenas que después se recorren en el grafo."""
    local, visitante = partido["local"], partido["visitante"]
    goles = {local: rng.randint(1, 3), visitante: rng.randint(0, 2)}
    minutos = rng.sample(range(3, 89), 12)
    crudas = [{"clave": "inicio", "tipo": "Inicio", "minuto": 0, "orden": 0, "jugador": None, "influye": None}]

    def agregar(clave, tipo, minuto, orden, jugador, influye=None):
        crudas.append({"clave": clave, "tipo": tipo, "minuto": minuto, "orden": orden, "jugador": jugador,
                       "influye": influye})

    n = 0
    for equipo in (local, visitante):
        for _ in range(goles[equipo]):
            minuto = minutos.pop()
            asistente, tirador = rng.sample(plantel[equipo][3:], 2)  # sin arqueros
            agregar(f"pase{n}", "Pase", minuto, 1, asistente, f"tiro{n}")
            agregar(f"tiro{n}", "Tiro", minuto, 2, tirador, f"gol{n}")
            agregar(f"gol{n}", "Gol", minuto, 3, tirador)
            n += 1
    for equipo in (local, visitante):
        minuto = minutos.pop()
        infractor = rng.choice(plantel[equipo][3:])
        agregar(f"falta{equipo}", "Falta", minuto, 1, infractor, f"amarilla{equipo}")
        agregar(f"amarilla{equipo}", "Tarjeta amarilla", minuto, 2, infractor)
        agregar(f"tiro_suelto{equipo}", "Tiro", minutos.pop(), 1, rng.choice(plantel[equipo][12:]))
        agregar(f"cambio{equipo}", "Cambio", minutos.pop(), 1, rng.choice(plantel[equipo][3:]))
    agregar("final", "Final", 90, 99, None)

    crudas.sort(key=lambda e: (e["minuto"], e["orden"]))
    id_de = {e["clave"]: f"EV-{partido['id']}-{i:04d}" for i, e in enumerate(crudas, start=1)}
    jugadas = [{
        "id": id_de[e["clave"]], "tipo": e["tipo"], "minuto": e["minuto"], "orden": e["orden"],
        "jugador": e["jugador"], "influye_en": id_de[e["influye"]] if e["influye"] else None,
    } for e in crudas]
    return jugadas, goles[local], goles[visitante]
