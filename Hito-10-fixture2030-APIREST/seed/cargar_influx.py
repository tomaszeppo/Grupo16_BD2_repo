import math
from datetime import datetime, timezone

import httpx

from app.config.settings import Settings
from seed import datos

INICIO = datetime(2030, 6, 15, 18, 30, tzinfo=timezone.utc)
SEGUNDOS = 600
FUENTES = ("broadcast", "scouting")


def _lineas(partido: dict):
    base = int(INICIO.timestamp())
    sede = next(e[1] for e in datos.ESTADIOS if e[0] == partido["estadio"]).replace(" ", "_")
    for seg in range(SEGUNDOS):
        for k, equipo in enumerate((partido["local"], partido["visitante"])):
            for f, fuente in enumerate(FUENTES):
                posesion = round(50 + (8 if k == 0 else -8) * math.sin(seg / 60) + f * 0.3, 1)
                yield (
                    f"estadisticas_partido,partido_id={partido['id']},equipo_id={equipo},sede={sede},"
                    f"fuente={fuente},fase=grupo "
                    f"posesion_pct={posesion},pases_completados={(seg * 7 + k * 3 + f) % 5}i,"
                    f"tiros={1 if seg % 97 == 0 else 0}i,recuperaciones={(seg + k) % 3 // 2}i,"
                    f"velocidad_kmh={round(5 + (seg * 13 + k * 7) % 80 / 10, 1)} {base + seg}"
                )


def cargar(s: Settings) -> str:
    total = 0
    with httpx.Client(base_url=s.influx_url, headers={"Authorization": f"Bearer {s.influx_token}"}, timeout=60) as c:
        for p in datos.PARTIDOS[:2]:  # P-01 y P-02 tienen estadísticas
            lineas = list(_lineas(p))
            for i in range(0, len(lineas), 2000):
                r = c.post(
                    "/api/v3/write_lp", params={"db": s.influx_db, "precision": "second"},
                    content=("\n".join(lineas[i:i + 2000]) + "\n").encode(),
                )
                r.raise_for_status()
            total += len(lineas)
    return f"{total} puntos (P-01 y P-02, 2030-06-15 18:30–18:40 UTC; reescribir los mismos timestamps no duplica)"
