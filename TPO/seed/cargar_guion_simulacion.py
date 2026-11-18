"""Guion editable de jugadas: MongoDB conserva el plan por partido sin sobrescribirlo."""
import argparse
import json
from pathlib import Path

from app.adapters.mongo import MongoAdapter
from app.adapters.neo4j import Neo4jAdapter
from app.config.settings import Settings
from app.errors import Conflicto, NoEncontrado

PLANTILLA = Path(__file__).with_name("guion_simulacion.json")
TIPOS = {"Pase", "Tiro", "Gol", "Falta", "Tarjeta amarilla", "Tarjeta roja", "Cambio"}


def construir_guion(partido, db, ruta=PLANTILLA):
    codigo = partido["id"]
    equipos = {lado: partido[lado]["codigo"] for lado in ("local", "visitante")}
    plantillas = json.loads(Path(ruta).read_text(encoding="utf-8-sig"))
    if not isinstance(plantillas, list) or not plantillas:
        raise Conflicto("El guion debe contener una lista de jugadas.")
    jugadas = []
    for numero, fila in enumerate(plantillas, 1):
        lado, tipo, minuto, dorsal, previa = (fila.get(k) for k in ("equipo", "tipo", "minuto", "dorsal", "previa"))
        if lado not in equipos or tipo not in TIPOS or type(minuto) is not int or not 1 <= minuto <= 90 or type(dorsal) is not int or not 1 <= dorsal <= 26:
            raise Conflicto(f"Jugada {numero}: equipo, tipo, minuto o dorsal inválidos.")
        if numero > 1 and minuto < jugadas[-1]["minuto"]:
            raise Conflicto(f"Jugada {numero}: el guion debe estar ordenado por minuto.")
        if previa is not None and (type(previa) is not int or not 1 <= previa < numero):
            raise Conflicto(f"Jugada {numero}: la jugada previa debe ser anterior.")
        jugador = db.jugadores.find_one({"equipo": equipos[lado], "dorsal": dorsal}, {"_id": 1})
        if not jugador:
            raise NoEncontrado(f"Falta el jugador {equipos[lado]} dorsal {dorsal} en MongoDB; cargar el fixture primero.")
        jugadas.append({"id":f"SIM-{codigo}-{numero:03d}", "tipo":tipo, "minuto":minuto, "orden":numero,
                        "equipo_id":equipos[lado], "jugador":jugador["_id"],
                        "influido_por": [jugadas[previa - 1]["id"]] if previa else []})
    if sum(j["tipo"] == "Gol" for j in jugadas) == 0:
        raise Conflicto("El guion debe incluir al menos un gol para la demostración.")
    return {"_id":codigo, "equipos":equipos, "jugadas":jugadas}


def obtener_o_crear(partido, db, ruta=PLANTILLA):
    codigo = partido["id"]
    guardado = db.guiones_simulacion.find_one({"_id": codigo})
    equipos = {lado: partido[lado]["codigo"] for lado in ("local", "visitante")}
    if guardado is None:
        nuevo = construir_guion(partido, db, ruta)
        db.guiones_simulacion.update_one({"_id":codigo}, {"$setOnInsert":nuevo}, upsert=True)
        guardado = db.guiones_simulacion.find_one({"_id":codigo})
    if not guardado or guardado.get("equipos") != equipos:
        raise Conflicto("El guion guardado no coincide con los equipos actuales del partido.")
    return guardado


def main():
    parser = argparse.ArgumentParser(description="Preparar un guion simulado en MongoDB sin sobrescribir datos.")
    parser.add_argument("--partido", required=True, help="ID del partido programado, por ejemplo P-12")
    parser.add_argument("--archivo", type=Path, default=PLANTILLA, help="JSON de jugadas; por defecto seed/guion_simulacion.json")
    args = parser.parse_args()
    settings = Settings()
    mongo, neo = MongoAdapter(settings), Neo4jAdapter(settings)
    partido = neo.obtener_partido(args.partido)
    if not partido or not partido["local"] or not partido["visitante"]:
        raise SystemExit("El partido no existe o todavía no tiene ambos equipos definidos.")
    if partido["estado"] != "Programado":
        raise SystemExit("Elegí un partido programado para preparar su guion.")
    guion = obtener_o_crear(partido, mongo.db, args.archivo)
    print(f"Guion disponible para {args.partido}: {len(guion['jugadas'])} jugadas. Un guion existente no se modifica.")


if __name__ == "__main__":
    main()
