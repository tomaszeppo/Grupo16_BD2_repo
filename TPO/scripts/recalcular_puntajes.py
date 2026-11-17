"""Control de la puntuación: recalcula todos los puntajes desde cero y los compara con los guardados.

La API suma los puntajes partido a partido. Este script hace el camino largo (agrupa todos los pronósticos
ya puntuados) y verifica que dé lo mismo. No modifica nada.

    docker compose run --rm herramientas python -m scripts.recalcular_puntajes

Sale con 0 si coinciden y con 1 si hay alguna diferencia.
"""
import sys

from pymongo import MongoClient

from app.config.settings import Settings

CAMPOS = ("puntos", "exactos", "tiempo_seg")


def recalcular(db) -> dict[str, dict]:
    """Puntaje de cada usuario según sus pronósticos puntuados."""
    tuberia = [
        {"$match": {"puntos": {"$exists": True}}},
        {"$group": {"_id": "$usuario_id", "puntos": {"$sum": "$puntos"},
                    "exactos": {"$sum": {"$cond": ["$exacto", 1, 0]}}, "tiempo_seg": {"$sum": "$tiempo_seg"},
                    "aplicados": {"$addToSet": "$partido_id"}}},
    ]
    return {f["_id"]: f for f in db.pronosticos.aggregate(tuberia, allowDiskUse=True)}


def diferencias(db) -> list[str]:
    esperado = recalcular(db)
    salida = []
    vistos = set()
    for guardado in db.puntajes.find():
        usuario = guardado["_id"]
        vistos.add(usuario)
        calculado = esperado.get(usuario)
        if calculado is None:
            salida.append(f"{usuario}: tiene puntaje guardado pero ningún pronóstico puntuado")
            continue
        for campo in CAMPOS:
            if guardado[campo] != calculado[campo]:
                salida.append(f"{usuario}: {campo} guardado={guardado[campo]} recalculado={calculado[campo]}")
        if set(guardado["aplicados"]) != set(calculado["aplicados"]):
            salida.append(f"{usuario}: los partidos aplicados no coinciden con sus pronósticos puntuados")
    for usuario in esperado.keys() - vistos:
        salida.append(f"{usuario}: tiene pronósticos puntuados pero no tiene puntaje guardado")
    return salida


def main() -> int:
    s = Settings()
    cliente = MongoClient(s.mongo_uri, tz_aware=True)
    db = cliente[s.mongo_db]
    encontradas = diferencias(db)
    print(f"Usuarios con puntaje guardado: {db.puntajes.count_documents({})}")
    print(f"Pronósticos puntuados: {db.pronosticos.count_documents({'puntos': {'$exists': True}})}")
    if encontradas:
        print(f"DIFERENCIAS: {len(encontradas)}")
        for linea in encontradas[:50]:
            print("  " + linea)
        return 1
    print("Sin diferencias: la suma partido a partido coincide con el recálculo completo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
