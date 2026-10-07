#!/usr/bin/env python3
"""Generador determinista de line protocol para el Fixture 2030."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Iterator, List, Tuple

TEAMS = [
    "ARG","FRA","ESP","BRA","URU","CHI","COL","MEX",
    "USA","CAN","ECU","PER","PAR","BOL","VEN","CRC",
    "ENG","POR","NED","GER","ITA","BEL","CRO","DEN",
    "SUI","SRB","POL","CZE","AUT","TUR","GRE","ROU",
    "MAR","SEN","GHA","NGA","CMR","ALG","EGY","TUN",
    "JPN","KOR","IRN","AUS","NZL","CHN","KSA","QAT",
    "RSA","CIV","GAB","COD","MLI","GUI","KEN","UGA",
    "GEO","UKR","SWE","NOR","FIN","ISL","IRL","SCO",
]

VENUES = [
    "Buenos_Aires","Cordoba","Rosario","Mendoza","La_Plata",
    "Montevideo","Santiago","Lima","Bogota","Quito",
    "Sao_Paulo","Rio_de_Janeiro","Mexico_City","Madrid","Barcelona",
    "Lisbon","Paris","Berlin","Rome","London",
]

SOURCES = [
    "scouting","tracking","broadcast","telemetria",
    "analitica","arbitraje","app","estadistica",
]

BASE_TIME = datetime(2030, 6, 15, 18, 30, 0, tzinfo=timezone.utc)
SECONDS_PER_MATCH = 5000

@dataclass(frozen=True)
class MatchInfo:
    match_id: str
    home: str
    away: str
    venue: str
    phase: str


def phase_for_index(idx: int) -> str:
    # 96 group + 16 R32 + 8 R16 + 4 QF + 2 SF + 1 final = 127.
    if idx <= 96:
        return "grupo"
    if idx <= 112:
        return "ronda_32"
    if idx <= 120:
        return "octavos"
    if idx <= 124:
        return "cuartos"
    if idx <= 126:
        return "semifinal"
    return "final"


def match_info(idx: int) -> MatchInfo:
    # Parejas deterministas; un identificador de partido nunca depende del nombre del estadio.
    home_idx = ((idx - 1) * 2) % len(TEAMS)
    away_idx = (home_idx + 1) % len(TEAMS)
    return MatchInfo(
        match_id=f"M{idx:03d}",
        home=TEAMS[home_idx],
        away=TEAMS[away_idx],
        venue=VENUES[(idx - 1) % len(VENUES)],
        phase=phase_for_index(idx),
    )


def iter_match_points(idx: int, start_time: datetime = BASE_TIME) -> Iterator[str]:
    """Genera 2 equipos x 8 fuentes x 5000 instantes = 80.000 puntos por partido."""
    info = match_info(idx)
    # 2 x 8 x 5000 = 80.000 puntos por partido.
    # Con 127 partidos: 10.160.000 puntos.
    for second in range(SECONDS_PER_MATCH):
        ts = int((start_time + timedelta(seconds=second + (idx - 1) * 7000)).timestamp())
        for team_offset, team in enumerate((info.home, info.away)):
            base = (idx * 17 + second * 7 + team_offset * 13)
            possession = 35.0 + ((base * 37) % 3000) / 100.0
            possession = min(65.0, possession)
            velocity = 4.5 + ((base * 11) % 160) / 10.0
            for source_offset, source in enumerate(SOURCES):
                seed = base + source_offset * 101
                passes = seed % 4
                shots = 1 if seed % 53 == 0 else 0
                recoveries = 1 if seed % 17 == 0 else 0
                source_possession = min(65.0, max(35.0, possession + ((source_offset - 3) * 0.7)))
                source_velocity = round(max(3.0, velocity + source_offset * 0.2), 1)
                yield (
                    f"estadisticas_partido,partido_id={info.match_id},"
                    f"equipo_id={team},sede={info.venue},fuente={source},fase={info.phase} "
                    f"posesion_pct={source_possession:.2f},pases_completados={passes}i,"
                    f"tiros={shots}i,recuperaciones={recoveries}i,velocidad_kmh={source_velocity:.1f} {ts}"
                )


def iter_users_points(matches: int) -> Iterator[str]:
    """Genera una serie corta de usuarios activos: 12 puntos/minuto por partido."""
    regions = ["AMBA", "Centro", "NOA", "NEA", "Patagonia"]
    for idx in range(1, matches + 1):
        info = match_info(idx)
        start = BASE_TIME + timedelta(seconds=(idx - 1) * 7000)
        for minute in range(12):
            ts = int((start + timedelta(minutes=minute)).timestamp())
            for region_offset, region in enumerate(regions):
                users = 12000 + ((idx * 137 + minute * 311 + region_offset * 503) % 18000)
                yield (
                    f"usuarios_conectados,partido_id={info.match_id},region={region} "
                    f"usuarios_activos={users}i {ts}"
                )


def iter_all_points(matches: int) -> Iterator[str]:
    for idx in range(1, matches + 1):
        yield from iter_match_points(idx)
    yield from iter_users_points(matches)


def chunked(iterable: Iterable[str], size: int) -> Iterator[List[str]]:
    batch: List[str] = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch
