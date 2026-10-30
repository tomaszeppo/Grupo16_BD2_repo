"""Genera material local. No conecta a bases ni ejecuta inserciones.

Uso: python scripts/preparar_datos.py --salida datos/preparados/lote_NUEVO
La carpeta de salida debe ser nueva: no se sobreescribe ningún archivo.
"""
import argparse
import csv
import hashlib
import json
import math
import re
import runpy
import subprocess
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAMESPACE = uuid.UUID("234a2aec-1bf2-40b2-8cee-7a18eb79fd23")


def generar(destino: Path):
    if destino.exists():
        raise SystemExit("La salida ya existe. Elegí otra carpeta; no se sobrescribe nada.")
    src = ROOT / "Hito-5-fixture2030-neo4j/queries/carga_partidos.cypher"
    texto = src.read_text(encoding="utf-8")
    pattern = r'\{id: "(P\d{3})", equipoLocal: "([A-Z]{3})", equipoVisitante: "([A-Z]{3})", estadio: "(EST\d{3})", fecha: "([0-9-]+)", fase: "([^"]+)"\}'
    partidos = [dict(zip(("id", "equipoLocal", "equipoVisitante", "estadio", "fecha", "fase"), m)) for m in re.findall(pattern, texto)]
    estadios = [dict(zip(("id", "nombre", "ciudad"), m)) for m in re.findall(r'\{id: "(EST\d{3})", nombre: "([^"]+)", ciudad: "([^"]+)"\}', texto)]
    if len(partidos) != 32 or len(estadios) != 10:
        raise SystemExit("El origen cambió: revisar el parser antes de generar.")
    h10 = runpy.run_path(str(ROOT / "Hito-10-fixture2030-APIREST/seed/datos.py"))
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    destino.mkdir(parents=True, exist_ok=False)
    def write(name, value):
        path = destino / name
        with path.open("x", encoding="utf-8", newline="") as f:
            f.write(value)
    def js(name, value):
        write(name, json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    def csvout(name, rows):
        with (destino / name).open("x", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    def ndjson(name, rows):
        write(name, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    csvout("partidos_h5_main.csv", partidos)
    js("neo4j_parametros.json", {"partidos": partidos, "estadios": estadios})
    js("partidos_h10_laboratorio.json", h10["PARTIDOS"])
    csvout("correspondencias_documentales.csv", [
        {"id_h5_main": p["id"], "id_h10_laboratorio": q["id"], "equipo_local": p["equipoLocal"],
         "equipo_visitante": p["equipoVisitante"], "fecha": p["fecha"], "estadio": p["estadio"],
         "estado": "coincide_en_fuentes_main_no_habilita_importacion", "cassandra_h6": "PENDIENTE", "commit": commit}
        for p in partidos for q in h10["PARTIDOS"]
        if (p["equipoLocal"], p["equipoVisitante"], p["fecha"], p["estadio"]) == (q["local"], q["visitante"], q["fecha"], q["estadio"])
    ])
    # 32 partidos * 2 paises * 2 ventanas * 15 comentarios = 1.920.
    # El horario es inventado para el experimento; la fuente H5 solo trae fecha.
    comentarios = []
    resumen = Counter()
    for p in partidos:
        for pais in ("ARG", "BRA"):
            for ventana_n in range(2):
                inicio = datetime.fromisoformat(p["fecha"]).replace(hour=18, minute=30, tzinfo=timezone.utc) + timedelta(minutes=30 * ventana_n)
                for n in range(15):
                    cid = str(uuid.uuid5(NAMESPACE, f'{p["id"]}/{pais}/{inicio.isoformat()}/{n}'))
                    comentarios.append({"comentario_id": cid, "partido_referencia_h5": p["id"], "partido_id_cassandra": None,
                        "pais": pais, "ventana": inicio.isoformat().replace("+00:00", "Z"),
                        "creado_en": (inicio + timedelta(seconds=n*100+1)).isoformat().replace("+00:00", "Z"),
                        "usuario_id": f"U{1000+n:04d}", "usuario_nombre": f"Usuario sintetico {n:02d}",
                        "contenido": f'H12 muestra sintetica {p["id"]} {pais} {n:02d}', "likes": n % 5,
                        "estado_moderacion": "PUBLICADO", "estado_preparacion": "requiere_correspondencia_y_destino"})
                    resumen[(p["id"], pais, inicio.isoformat().replace("+00:00", "Z"))] += 1
    ndjson("comentarios_propuestos.jsonl", comentarios)
    csvout("datamart_conteos_esperados.csv", [{"partido_referencia_h5": k[0], "pais": k[1], "ventana": k[2], "cantidad": v} for k,v in sorted(resumen.items())])
    # Soporte H10: se mantiene separado del perfil H5 y no exige recargar lo existente.
    ndjson("mongo_equipos_h10.jsonl", [{"codigo": c, "nombre": n} for c,n in h10["EQUIPOS"]])
    ndjson("mongo_jugadores_h10.jsonl", h10["jugadores"]())
    js("iris_partidos_h10.json", [{**p, "estado_inicial": h10["IRIS_ESTADO_INICIAL"].get(p["id"], "Programado"), "eventos": h10["IRIS_EVENTOS"].get(p["id"], [])} for p in h10["PARTIDOS"]])
    base = int(datetime(2030,6,15,18,30,tzinfo=timezone.utc).timestamp())
    sede = {e[0]: e[1].replace(" ", "_") for e in h10["ESTADIOS"]}
    lines = []
    for p in h10["PARTIDOS"][:2]:
        for seg in range(600):
            for k, eq in enumerate((p["local"],p["visitante"])):
                for f, fuente in enumerate(("broadcast", "scouting")):
                    lines.append(f"estadisticas_partido,partido_id={p['id']},equipo_id={eq},sede={sede[p['estadio']]},fuente={fuente},fase=grupo "
                        f"posesion_pct={round(50+(8 if k==0 else -8)*math.sin(seg/60)+f*.3,1)},pases_completados={(seg*7+k*3+f)%5}i,"
                        f"tiros={1 if seg%97==0 else 0}i,recuperaciones={(seg+k)%3//2}i,velocidad_kmh={round(5+(seg*13+k*7)%80/10,1)} {base+seg}")
    write("influx_muestra_h10.lp", "\n".join(lines)+"\n")
    js("redis_politica_propuesta.json", {"autoridad": "Neo4j", "namespace": "f2030:h12:cache:partido:v1:", "ttl_segundos": 15,
        "payload": "Respuesta real validada de Neo4j; no precargar respuestas inventadas", "fallback": "Neo4j con timeout acotado",
        "invalidacion": "pendiente de implementar y verificar; por ahora no se modifica ni elimina ninguna clave"})
    fuente_paths = [src, ROOT / "Hito-10-fixture2030-APIREST/seed/datos.py", ROOT / "Hito-10-fixture2030-APIREST/seed/cargar_influx.py"]
    manifest = {"version":1, "estado":"PREPARADO_NO_INSERTADO", "commit_origen":commit, "sintetico":True,
        "limites": ["Horarios de comentarios sinteticos, no horarios oficiales", "Cassandra sin ID de destino hasta validar correspondencia", "Archivos H10 de apoyo, no reemplazan la reutilizacion de H4-H9", "IDs del perfil H5 aun no aceptados por la API actual"],
        "cantidades":{"partidos_h5":32,"estadios_h5":10,"correspondencias_documentales":8,"comentarios_propuestos":1920,"particiones_propuestas":128,"mongo_equipos_h10":16,"mongo_jugadores_h10":80,"iris_partidos_h10":8,"influx_puntos_h10":4800},
        "fuentes": [{"ruta":str(p.relative_to(ROOT)).replace('\\','/'),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in fuente_paths],
        "archivos": [{"ruta":p.name,"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(destino.iterdir())]}
    js("manifiesto.json", manifest)
    print(json.dumps({"salida":str(destino),"estado":manifest["estado"],"cantidades":manifest["cantidades"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--salida", type=Path, required=True)
    generar(ap.parse_args().salida.resolve())
