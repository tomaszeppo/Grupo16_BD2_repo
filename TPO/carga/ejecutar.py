"""Corre un escenario de carga contra la API y guarda la evidencia.

    python -m carga.ejecutar pico_pronosticos   --usuarios 100000 --concurrencia 50 --duracion 60
    python -m carga.ejecutar lecturas_fixture   --concurrencia 50 --duracion 60
    python -m carga.ejecutar pico_mixto         --usuarios 100000 --concurrencia 50 --duracion 60
    python -m carga.ejecutar posicion_ranking   --usuarios 100000 --concurrencia 20 --duracion 30
    python -m carga.ejecutar cierre_partido     --partido P-05
    python -m carga.ejecutar caida              --usuarios 100000 --concurrencia 20 --duracion 90 --etiqueta primario
    python -m carga.ejecutar vivo               --espectadores 2000 --comentan 0.05 --partido P-07

Los usuarios tienen que existir antes (python -m carga.poblar). Cada corrida deja dos archivos en evidencia/:
<escenario>_<fecha>_<hora>.jsonl (un pedido por línea) y <escenario>_<fecha>_<hora>_resumen.json.
"""
import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.dominio.ids import id_usuario
from carga import cliente
from carga.resumen import linea_de_tiempo, resumir

EVIDENCIA = Path(__file__).resolve().parent.parent / "evidencia"
EVENTOS_DE_MUESTRA = ("EV-P-01-0002", "EV-P-01-0004", "EV-P-02-0003")


def _pronostico(rng: random.Random, tokens: list[str], partido: str) -> dict:
    """Pronóstico de un usuario al azar, con su sesión (el token i es del usuario i+1, ver carga/sesiones.py)."""
    return {"ruta": "PUT /partidos/{id}/pronostico", "metodo": "PUT", "url": f"/partidos/{partido}/pronostico",
            "json": {"goles_local": rng.randint(0, 4), "goles_visitante": rng.randint(0, 4)},
            "headers": {"X-Sesion": rng.choice(tokens)}}


def _lectura(rng: random.Random) -> dict:
    tirada = rng.random()
    if tirada < 0.25:
        return {"ruta": "GET /partidos", "metodo": "GET", "url": "/partidos?fase=Fase%20de%20grupos"}
    if tirada < 0.70:
        return {"ruta": "GET /partidos/{id}", "metodo": "GET", "url": f"/partidos/P-{rng.randint(1, 104):02d}"}
    if tirada < 0.90:
        return {"ruta": "GET /partidos/{id}/eventos", "metodo": "GET", "url": f"/partidos/P-0{rng.randint(1, 2)}/eventos"}
    evento = rng.choice(EVENTOS_DE_MUESTRA)
    return {"ruta": "GET /partidos/{id}/eventos/{id}/cadena", "metodo": "GET",
            "url": f"/partidos/{evento[3:7]}/eventos/{evento}/cadena"}


def _ranking(rng: random.Random, usuarios: int) -> dict:
    if rng.random() < 0.8:
        return {"ruta": "GET /ranking/usuarios/{id}", "metodo": "GET",
                "url": f"/ranking/usuarios/{id_usuario(rng.randint(1, usuarios))}"}
    return {"ruta": "GET /ranking", "metodo": "GET", "url": "/ranking?limit=100"}


def _sesiones(usuarios: int) -> list[str]:
    from app.adapters.redis import RedisAdapter
    from app.config.settings import get_settings
    from carga.sesiones import preparar

    return preparar(RedisAdapter(get_settings()), usuarios)


def _fabrica(args) -> tuple:
    """Devuelve (función que arma el próximo pedido, estados que no se consideran error)."""
    rngs = [random.Random(args.semilla * 1000 + n) for n in range(args.concurrencia)]
    tokens = _sesiones(args.usuarios) if args.escenario in ("pico_pronosticos", "caida", "pico_mixto") else []
    if args.escenario in ("pico_pronosticos", "caida"):
        return (lambda n: _pronostico(rngs[n], tokens, args.partido)), {200, 201}
    if args.escenario == "lecturas_fixture":
        return (lambda n: _lectura(rngs[n])), {200}
    if args.escenario == "pico_mixto":
        return (lambda n: _pronostico(rngs[n], tokens, args.partido) if rngs[n].random() < 0.7
                else _lectura(rngs[n])), {200, 201}
    if args.escenario == "posicion_ranking":
        return (lambda n: _ranking(rngs[n], args.usuarios)), {200}
    raise SystemExit(f"Escenario desconocido: {args.escenario}")


def _entorno(base_url: str) -> dict:
    """Lo que se sabe del entorno. Los límites salen de las mismas variables que usa el Compose."""
    entorno = {k.lower(): os.environ.get(k) for k in (
        "API_PROCESOS", "API_MEMORIA", "API_CPUS", "MONGO_MEMORIA", "MONGO_CPUS", "NEO4J_MEMORIA", "NEO4J_CPUS",
        "CALENDARIO_TTL_SEGUNDOS")}
    entorno["nodos_de_mongodb"] = 3
    entorno["generador"] = "contenedor de herramientas en el mismo equipo y la misma red que la API, sin límite propio"
    try:
        entorno["dependencias"] = httpx.get(f"{base_url}/health/dependencias", timeout=10).json()
    except httpx.HTTPError:
        entorno["dependencias"] = "la API no respondió antes de empezar"
    return entorno


def _guardar(nombre: str, resumen: dict, filas: list[dict] | None) -> Path:
    EVIDENCIA.mkdir(exist_ok=True)
    if filas is not None:
        with open(EVIDENCIA / f"{nombre}.jsonl", "w", encoding="utf-8") as archivo:
            for fila in filas:
                archivo.write(json.dumps(fila) + "\n")
    ruta = EVIDENCIA / f"{nombre}_resumen.json"
    ruta.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta


def _vivo(args, base_url: str) -> tuple[dict, list[dict], int]:
    """Partido en vivo: abre las conexiones, inicia la simulación (tipo carga) y la sigue hasta el final."""
    from carga.vivo import correr_vivo, resumir_vivo

    admin = {"X-Admin-Clave": os.environ["ADMIN_CLAVE"]}
    tokens = _sesiones(args.espectadores)

    def iniciar():
        r = httpx.post(f"{base_url}/administracion/simulaciones/{args.partido}", params={"tipo": "carga"},
                       headers=admin, timeout=30)
        if r.status_code != 202:
            raise SystemExit(f"No se pudo iniciar la simulación de {args.partido}: {r.status_code} {r.text}")

    eventos, procesos = correr_vivo(base_url, args.partido, tokens, args.comentan, args.duracion, args.semilla, iniciar)
    for _ in range(60):  # después del minuto 90 la simulación puntúa y archiva: se espera su estado final
        simulacion = httpx.get(f"{base_url}/administracion/simulaciones/{args.partido}", headers=admin, timeout=30).json()
        if simulacion.get("estado_simulacion") in ("completa", "fallida"):
            break
        time.sleep(1)
    medicion = resumir_vivo(eventos, args.espectadores)
    medicion["simulacion"] = {k: simulacion.get(k) for k in ("estado_simulacion", "minuto", "audiencia_incompleta",
                                                              "estadisticas_incompletas", "archivo_estado")}
    return medicion, eventos, procesos


def _cierre_de_partido(args, base_url: str) -> dict:
    """Pone el partido en juego, lo cierra y espera a que termine la puntuación. Después repite el cierre."""
    admin = {"X-Admin-Clave": os.environ["ADMIN_CLAVE"]}
    marcador = {"goles_local": args.goles_local, "goles_visitante": args.goles_visitante}
    with httpx.Client(base_url=base_url, timeout=30, headers=admin) as http:
        en_juego = http.post(f"/partidos/{args.partido}/estado", json={"estado": "En juego"})
        if en_juego.status_code != 200:
            raise SystemExit(f"No se pudo poner en juego {args.partido}: {en_juego.status_code} {en_juego.text}")
        t0 = time.perf_counter()
        cierre = http.post(f"/partidos/{args.partido}/resultado", json=marcador)
        respuesta_ms = round((time.perf_counter() - t0) * 1000, 1)
        if cierre.status_code != 202:
            raise SystemExit(f"No se pudo cerrar {args.partido}: {cierre.status_code} {cierre.text}")
        puntuacion = cierre.json()["puntuacion"]
        while puntuacion["estado"] not in ("completa", "fallida"):
            time.sleep(0.5)
            puntuacion = http.get(f"/partidos/{args.partido}/puntuacion").json()["puntuacion"]
        total_ms = round((time.perf_counter() - t0) * 1000, 1)
        ranking_antes = http.get("/ranking?limit=100").json()["ranking"]
        repeticion = http.post(f"/partidos/{args.partido}/resultado", json=marcador)
        time.sleep(2)
        ranking_despues = http.get("/ranking?limit=100").json()["ranking"]
    return {
        "partido": args.partido, "marcador": marcador,
        "respuesta_del_cierre_ms": respuesta_ms,
        "hasta_puntuacion_completa_ms": total_ms,
        "puntuacion": puntuacion,
        "repeticion_del_cierre": {"estado_http": repeticion.status_code,
                                  "ranking_sin_cambios": ranking_antes == ranking_despues},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Pruebas de carga del prode 2030")
    parser.add_argument("escenario", choices=["pico_pronosticos", "lecturas_fixture", "pico_mixto", "posicion_ranking",
                                              "cierre_partido", "caida", "vivo"])
    parser.add_argument("--usuarios", type=int, default=1000, help="usuarios ya creados con carga.poblar")
    parser.add_argument("--concurrencia", type=int, default=20, help="usuarios virtuales pidiendo a la vez")
    parser.add_argument("--duracion", type=float, default=30, help="segundos")
    parser.add_argument("--partido", default="P-03")
    parser.add_argument("--goles-local", type=int, default=2)
    parser.add_argument("--goles-visitante", type=int, default=1)
    parser.add_argument("--semilla", type=int, default=2030)
    parser.add_argument("--espectadores", type=int, default=200, help="vivo: conexiones abiertas, un usuario distinto cada una")
    parser.add_argument("--comentan", type=float, default=0.05, help="vivo: parte de los espectadores que comenta")
    parser.add_argument("--etiqueta", default="", help="texto libre que queda en el resumen y en el nombre del archivo")
    parser.add_argument("--nota", action="append", default=[], help="aclaración para el resumen (se puede repetir)")
    args = parser.parse_args()

    base_url = os.environ.get("API_URL", "http://127.0.0.1:8010")
    inicio = datetime.now(timezone.utc)
    nombre = "_".join(p for p in (args.escenario, args.etiqueta, inicio.strftime("%Y%m%d_%H%M%S")) if p)
    resumen = {
        "escenario": args.escenario, "etiqueta": args.etiqueta, "inicio": inicio.isoformat(),
        "commit": os.environ.get("COMMIT", "sin commit"),
        "parametros": {k: v for k, v in vars(args).items() if k not in ("escenario", "etiqueta", "nota")},
        "entorno": _entorno(base_url),
        "preparacion": "usuarios, pronósticos y puntajes de volumen cargados directo en MongoDB con carga.poblar; "
                       "todos los pedidos medidos pasan por la API",
        "notas": args.nota,
    }

    if args.escenario == "cierre_partido":
        resumen["medicion"] = _cierre_de_partido(args, base_url)
        filas = None
    elif args.escenario == "vivo":
        if args.duracion < 95:
            args.duracion = 95  # el partido dura 90 s; unos segundos más para el cierre
        resumen["parametros"]["duracion"] = args.duracion
        resumen["medicion"], filas, procesos = _vivo(args, base_url)
        resumen["entorno"]["generador"] += f"; {procesos} procesos con conexiones asincrónicas"
    else:
        siguiente, esperados = _fabrica(args)
        filas, duracion, procesos = cliente.correr(base_url, siguiente, args.concurrencia, args.duracion)
        resumen["entorno"]["generador"] += f"; {procesos} procesos y {args.concurrencia} hilos"
        resumen["duracion_real_segundos"] = round(duracion, 2)
        resumen["medicion"] = resumir(filas, duracion, esperados)
        if args.escenario == "caida":
            resumen["linea_de_tiempo"] = linea_de_tiempo(filas, esperados)
    resumen["fin"] = datetime.now(timezone.utc).isoformat()

    ruta = _guardar(nombre, resumen, filas)
    medicion = resumen["medicion"]
    if args.escenario == "vivo":
        print(json.dumps(medicion, ensure_ascii=False, indent=2))
    elif filas is None:
        print(json.dumps(medicion, ensure_ascii=False, indent=2))
    else:
        print(f"{args.escenario}: {medicion['total']} pedidos, {medicion['por_segundo']}/s, "
              f"p50 {medicion['p50_ms']} ms, p95 {medicion['p95_ms']} ms, p99 {medicion['p99_ms']} ms, "
              f"errores {medicion['errores']} ({medicion['porcentaje_de_error']} %) {medicion['errores_por_estado']}")
    print(f"evidencia: {ruta.relative_to(EVIDENCIA.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
