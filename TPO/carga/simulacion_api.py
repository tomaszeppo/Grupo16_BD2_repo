"""Simulación real con pronósticos y consultas exclusivamente por la API.

Crea usuarios y pronósticos persistentes, inicia un partido programado y espera su cierre.
No borra ni reinicia datos. Usar solo con un partido de laboratorio disponible.
"""
import argparse
import json
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.config.settings import Settings
from carga.resumen import resumir

EVIDENCIA = Path(__file__).resolve().parent.parent / "evidencia"


def esperado(pronostico, marcador):
    gl, gv = pronostico
    rl, rv = marcador
    if (gl, gv) == (rl, rv):
        return 3
    return 1 if (gl > gv) - (gl < gv) == (rl > rv) - (rl < rv) else 0


def ejecutar(args):
    base = os.environ.get("API_URL", "http://127.0.0.1:8010")
    clave = Settings().admin_clave
    if not clave:
        raise RuntimeError("Falta ADMIN_CLAVE en el entorno o .env")
    filas, errores, usuarios = [], [], []
    candado = threading.Lock()
    t0 = time.monotonic()
    with httpx.Client(base_url=base, timeout=15, trust_env=False) as http:
        def pedir(metodo, url, ruta, **kwargs):
            inicio = time.perf_counter()
            estado = 0
            try:
                respuesta = http.request(metodo, url, **kwargs)
                estado = respuesta.status_code
                respuesta.raise_for_status()
                return respuesta.json()
            finally:
                fila = {"t": round(time.monotonic() - t0, 3), "ruta": ruta, "estado": estado,
                        "ms": round((time.perf_counter() - inicio) * 1000, 2)}
                with candado:
                    filas.append(fila)
        partido = pedir("GET", f"/partidos/{args.partido}", "GET /partidos/{id}")["partido"]
        if partido["estado"] != "Programado" or not partido.get("local") or not partido.get("visitante"):
            raise RuntimeError("El partido debe estar programado y tener ambos equipos")
        if pedir("GET", "/ranking?limit=1", "GET /ranking")["fuente"] != "redis":
            raise RuntimeError("El ranking no está usando Redis")
        def crear(n):
            usuario = pedir("POST", "/usuarios", "POST /usuarios", json={"nombre": f"Prueba API {args.partido} {n}", "pais": "ARG"})["usuario"]["id"]
            rng = random.Random(2030 + n)
            pronostico = (rng.randint(0, 3), rng.randint(0, 3))
            token = pedir("POST", "/sesiones", "POST /sesiones", json={"usuario_id": usuario})["token"]
            pedir("PUT", f"/partidos/{args.partido}/pronostico", "PUT /partidos/{id}/pronostico",
                  headers={"X-Sesion": token}, json={"goles_local": pronostico[0], "goles_visitante": pronostico[1]})
            return usuario, pronostico
        print(f"Creando {args.usuarios} usuarios y pronósticos mediante la API...", flush=True)
        with ThreadPoolExecutor(max_workers=args.concurrencia) as pool:
            tamano = max(100, args.concurrencia * 4)
            for desde in range(0, args.usuarios, tamano):
                futuros = [pool.submit(crear, n) for n in range(desde, min(desde + tamano, args.usuarios))]
                for futuro in as_completed(futuros):
                    usuarios.append(futuro.result())
        admin = {"X-Admin-Clave": clave}
        print(f"Iniciando simulación de {args.partido}; consultas de ranking: {args.lectores} lectores.", flush=True)
        parar = threading.Event()
        def leer_ranking():
            while not parar.is_set():
                try:
                    datos = pedir("GET", "/ranking?limit=20", "GET /ranking")
                    if datos.get("fuente") != "redis":
                        raise RuntimeError("El ranking dejó de responder desde Redis")
                except Exception as exc:
                    with candado: errores.append(type(exc).__name__)
                parar.wait(args.intervalo)
        lectores = [threading.Thread(target=leer_ranking, daemon=True) for _ in range(args.lectores)]
        try:
            inicio = time.monotonic()
            pedir("POST", f"/administracion/simulaciones/{args.partido}", "POST /administracion/simulaciones/{id}", headers=admin)
            for hilo in lectores: hilo.start()
            limite = inicio + args.timeout
            simulacion = None
            while time.monotonic() < limite:
                simulacion = pedir("GET", f"/administracion/simulaciones/{args.partido}",
                                    "GET /administracion/simulaciones/{id}", headers=admin)
                estado = simulacion.get("estado_simulacion")
                if estado == "fallida": raise RuntimeError("La simulación falló")
                if estado == "completa": break
                time.sleep(2)
            else:
                raise TimeoutError("La simulación no terminó dentro del plazo")
            while time.monotonic() < limite:
                puntuacion = pedir("GET", f"/partidos/{args.partido}/puntuacion", "GET /partidos/{id}/puntuacion", headers=admin)["puntuacion"]
                if puntuacion["estado"] == "fallida": raise RuntimeError("La puntuación falló")
                if puntuacion["estado"] == "completa": break
                time.sleep(2)
            else: raise TimeoutError("La puntuación no terminó dentro del plazo")
            marcador = simulacion["marcador"]
            errores_puntos = []
            for usuario, pronostico in usuarios:
                posicion = pedir("GET", f"/ranking/usuarios/{usuario}", "GET /ranking/usuarios/{id}")
                valor = esperado(pronostico, (marcador["local"], marcador["visitante"]))
                if posicion.get("fuente") != "redis" or posicion.get("puntos") != valor:
                    errores_puntos.append(usuario)
            final = {"marcador": marcador, "archivo_estado": simulacion.get("archivo_estado"),
                     "puntuacion": puntuacion, "usuarios_verificados": len(usuarios), "puntajes_incorrectos": errores_puntos,
                     "duracion_simulacion_y_persistencia_segundos": round(time.monotonic() - inicio, 2)}
        finally:
            parar.set()
            for hilo in lectores:
                if hilo.ident is not None: hilo.join(timeout=20)
    duracion = time.monotonic() - t0
    EVIDENCIA.mkdir(exist_ok=True)
    nombre = f"simulacion_api_{args.partido}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    resumen = {"partido": args.partido, "usuarios": args.usuarios, "concurrencia_preparacion": args.concurrencia,
               "lectores": args.lectores, "intervalo_lectores_segundos": args.intervalo, "resultado": final,
               "medicion_http": resumir(filas, duracion, {200, 201, 202}), "errores_lectores": errores,
               "nota": "Prueba local por HTTP con usuarios nuevos; el generador comparte máquina con el servidor."}
    ruta = EVIDENCIA / f"{nombre}_resumen.json"
    ruta.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    (EVIDENCIA / f"{nombre}.jsonl").write_text("".join(json.dumps(f) + "\n" for f in filas), encoding="utf-8")
    print(json.dumps({"resultado": final, "medicion_http": resumen["medicion_http"], "evidencia": str(ruta)}, ensure_ascii=False, indent=2))
    return 1 if errores or errores_puntos or resumen["medicion_http"]["errores"] else 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--partido", required=True)
    p.add_argument("--usuarios", type=int, default=100)
    p.add_argument("--concurrencia", type=int, default=2)
    p.add_argument("--lectores", type=int, default=2)
    p.add_argument("--intervalo", type=float, default=1)
    p.add_argument("--timeout", type=int, default=240)
    args = p.parse_args()
    if min(args.usuarios, args.concurrencia, args.lectores, args.intervalo, args.timeout) <= 0:
        p.error("Los valores numéricos deben ser positivos")
    try:
        return ejecutar(args)
    except Exception as exc:
        EVIDENCIA.mkdir(exist_ok=True)
        nombre = f"simulacion_api_{args.partido}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_fallida.json"
        ruta = EVIDENCIA / nombre
        ruta.write_text(json.dumps({"partido": args.partido, "usuarios_solicitados": args.usuarios,
                                    "error_tipo": type(exc).__name__, "error": str(exc)},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Prueba fallida: {exc}. Evidencia: {ruta}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
