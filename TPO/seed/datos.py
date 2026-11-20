"""Datos de laboratorio del Mundial 2030. Todo es sintético y sale igual con la misma semilla.

Los equipos llevan nombres de países reales para que el fixture se lea fácil; grupos, planteles,
horarios, estadios y resultados son inventados.
"""
import random
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.dominio.ids import id_partido

# 64 selecciones en cuatro bombos de 16. El grupo g toma el equipo g de cada bombo, así que los seis
# anfitriones (primeros del bombo 1) encabezan los grupos A a F y nunca se cruzan en la fase de grupos.
_BOMBOS = [
    [("ARG", "Argentina"), ("ESP", "España"), ("POR", "Portugal"), ("URU", "Uruguay"), ("MAR", "Marruecos"),
     ("PAR", "Paraguay"), ("BRA", "Brasil"), ("FRA", "Francia"), ("ENG", "Inglaterra"), ("GER", "Alemania"),
     ("NED", "Países Bajos"), ("BEL", "Bélgica"), ("ITA", "Italia"), ("CRO", "Croacia"), ("COL", "Colombia"),
     ("USA", "Estados Unidos")],
    [("MEX", "México"), ("SUI", "Suiza"), ("DEN", "Dinamarca"), ("JPN", "Japón"), ("SEN", "Senegal"),
     ("ECU", "Ecuador"), ("AUT", "Austria"), ("KOR", "Corea del Sur"), ("POL", "Polonia"), ("SRB", "Serbia"),
     ("SWE", "Suecia"), ("CAN", "Canadá"), ("NOR", "Noruega"), ("IRN", "Irán"), ("CHI", "Chile"),
     ("AUS", "Australia")],
    [("PER", "Perú"), ("NGA", "Nigeria"), ("EGY", "Egipto"), ("CIV", "Costa de Marfil"), ("TUN", "Túnez"),
     ("ALG", "Argelia"), ("CMR", "Camerún"), ("GHA", "Ghana"), ("TUR", "Turquía"), ("UKR", "Ucrania"),
     ("CZE", "Chequia"), ("SCO", "Escocia"), ("KSA", "Arabia Saudita"), ("QAT", "Catar"), ("CRC", "Costa Rica"),
     ("PAN", "Panamá")],
    [("JAM", "Jamaica"), ("RSA", "Sudáfrica"), ("UZB", "Uzbekistán"), ("NZL", "Nueva Zelanda"), ("WAL", "Gales"),
     ("IRL", "Irlanda"), ("GRE", "Grecia"), ("HUN", "Hungría"), ("ROU", "Rumania"), ("SVK", "Eslovaquia"),
     ("BOL", "Bolivia"), ("VEN", "Venezuela"), ("HON", "Honduras"), ("MLI", "Malí"), ("IRQ", "Irak"),
     ("CHN", "China")],
]
GRUPOS = "ABCDEFGHIJKLMNOP"
# En el orden de los grupos: los cuatro primeros son el grupo A, los cuatro siguientes el B, y así.
EQUIPOS = [_BOMBOS[bombo][g] for g in range(len(GRUPOS)) for bombo in range(4)]
ANFITRIONES = ("ARG", "ESP", "POR", "URU", "MAR", "PAR")

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


PARTIDOS_DE_GRUPOS = 6 * len(GRUPOS)  # 96
ELIMINATORIAS = [("Dieciseisavos", 16), ("Octavos", 8), ("Cuartos", 4), ("Semifinal", 2), ("Tercer puesto", 1),
                 ("Final", 1)]


def _partidos(equipos: list[dict], estadios: list[dict], inicio: datetime) -> tuple[list[dict], list[tuple]]:
    cruces = []
    for jornada in _JORNADAS:
        for g in range(len(GRUPOS)):
            del_grupo = [e["codigo"] for e in equipos[g * 4:g * 4 + 4]]
            for a, b in jornada:
                cruces.append(("Fase de grupos", del_grupo[a], del_grupo[b]))
    for fase, cantidad in ELIMINATORIAS:
        cruces += [(fase, None, None)] * cantidad

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

    enlazar(97, 113, 8)  # dieciseisavos → octavos
    enlazar(113, 121, 4)  # octavos → cuartos
    enlazar(121, 125, 2)  # cuartos → semifinales
    enlazar(125, 128, 1)  # semifinales → final
    cuadro += [("P-125", "P-127", "perdedor"), ("P-126", "P-127", "perdedor")]
    return partidos, cuadro


TURNOS_POR_DIA = 4  # horarios de inicio por día, cada tres horas


def _fecha(indice: int, inicio: datetime) -> datetime:
    """Horario de cada partido.

    Fase de grupos: los dos partidos de un grupo en cada jornada empiezan a la misma hora, en simultáneo, y hay
    cuatro horarios por día (ocho partidos). Eliminatorias: un partido por horario y un día libre entre rondas.
    P-01 y P-02 son la muestra: se jugaron, en simultáneo, el día anterior a `inicio`.
    """
    if indice < 2:
        return inicio - timedelta(days=1)
    if indice < PARTIDOS_DE_GRUPOS:
        turno = (indice - 2) // 2
        return inicio + timedelta(days=turno // TURNOS_POR_DIA, hours=3 * (turno % TURNOS_POR_DIA))
    turnos_de_grupos = (PARTIDOS_DE_GRUPOS - 2) // 2
    dia = -(-turnos_de_grupos // TURNOS_POR_DIA)  # primer día después de la fase de grupos
    restante = indice - PARTIDOS_DE_GRUPOS
    for _, cantidad in ELIMINATORIAS:
        dia += 1  # día libre antes de cada ronda
        if restante < cantidad:
            return inicio + timedelta(days=dia + restante // TURNOS_POR_DIA, hours=3 * (restante % TURNOS_POR_DIA))
        dia += -(-cantidad // TURNOS_POR_DIA)  # días que ocupa la ronda
        restante -= cantidad
    raise ValueError("Índice de partido fuera del torneo.")


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
