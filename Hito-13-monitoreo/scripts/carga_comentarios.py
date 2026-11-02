"""Pico de comentarios por país contra la API instrumentada y verificación de lo guardado.

Uso: python scripts/carga_comentarios.py --partido P-01 --cantidad 3000 --tasa 50 --salida evidencia/resultados_sin_secretos

Cada corrida usa claves de idempotencia nuevas (h13-<corrida>-<n>), así que repetirla no choca con las anteriores.
La tasa está acotada para no saturar la notebook (RNF9). Al terminar consulta GET /partidos/{id}/comentarios
por país y ventana y comprueba que cada comentario creado esté guardado una sola vez.
"""
import argparse
import json
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import httpx


def generar_comentarios(corrida: str, cantidad: int, paises: list[str]) -> list[dict]:
    comentarios = []
    for n in range(cantidad):
        pais = paises[n % len(paises)]
        comentarios.append({
            "clave": f"h13-{corrida}-{n:06d}",
            "pais": pais,
            "cuerpo": {
                "pais": pais,
                "usuario_id": f"U{100 + n % 900:03d}",
                "usuario_nombre": f"Hincha {n % 900}",
                "contenido": f"Comentario de prueba H13 #{n} desde {pais}",
            },
        })
    return comentarios


def resumir(resultados: list[dict]) -> dict:
    codigos = Counter(r["codigo"] for r in resultados)
    errores = Counter(
        r.get("error") or str(r["codigo"]) for r in resultados if r["codigo"] not in (200, 201)
    )
    return {
        "enviados": len(resultados),
        "creados_201": codigos[201],
        "reintentos_200": codigos[200],
        "errores": dict(errores),
        "creados_por_pais": dict(Counter(r["pais"] for r in resultados if r["codigo"] == 201)),
    }


def enviar(base_url: str, partido: str, comentarios: list[dict], tasa: float, hilos: int) -> list[dict]:
    """Programa cada pedido en t0 + n/tasa; los hilos solo absorben la latencia, no suben la tasa."""
    t0 = time.perf_counter()
    candado = threading.Lock()
    resultados = []
    cliente = httpx.Client(base_url=base_url, timeout=10)

    def uno(n, c):
        espera = t0 + n / tasa - time.perf_counter()
        if espera > 0:
            time.sleep(espera)
        inicio = time.perf_counter()
        fila = {"n": n, "pais": c["pais"], "codigo": None, "comentario_id": None, "ventana": None}
        try:
            r = cliente.post(f"/partidos/{partido}/comentarios", json=c["cuerpo"],
                             headers={"Idempotency-Key": c["clave"]})
            fila["codigo"] = r.status_code
            if r.status_code in (200, 201):
                cuerpo = r.json()
                fila["comentario_id"], fila["ventana"] = cuerpo["comentario_id"], cuerpo["ventana"]
        except httpx.HTTPError as exc:
            fila["error"] = type(exc).__name__
        fila["duracion_ms"] = round((time.perf_counter() - inicio) * 1000, 2)
        with candado:
            resultados.append(fila)

    with ThreadPoolExecutor(max_workers=hilos) as pool:
        for n, c in enumerate(comentarios):
            pool.submit(uno, n, c)
    cliente.close()
    return sorted(resultados, key=lambda r: r["n"])


def verificar(base_url: str, partido: str, resultados: list[dict]) -> dict:
    """Lee cada partición (país, ventana) tocada y cruza los ids creados con los guardados."""
    creados = {r["comentario_id"] for r in resultados if r["codigo"] in (200, 201)}
    particiones = {(r["pais"], r["ventana"]) for r in resultados if r["ventana"]}
    encontrados = Counter()
    with httpx.Client(base_url=base_url, timeout=30) as cliente:
        for pais, ventana in sorted(particiones):
            cursor = None
            while True:
                params = {"pais": pais, "ventana": ventana, "limit": 100}
                if cursor:
                    params["cursor"] = cursor
                pagina = cliente.get(f"/partidos/{partido}/comentarios", params=params).json()
                encontrados.update(i["comentario_id"] for i in pagina["items"] if i["comentario_id"] in creados)
                cursor = pagina["next_cursor"]
                if not cursor:
                    break
    return {
        "particiones_leidas": len(particiones),
        "ids_creados": len(creados),
        "ids_encontrados": len(encontrados),
        "faltantes": len(creados - set(encontrados)),
        "duplicados": sum(1 for v in encontrados.values() if v > 1),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base-url", default="http://127.0.0.1:8001")
    ap.add_argument("--partido", default="P-01")
    ap.add_argument("--cantidad", type=int, default=3000)
    ap.add_argument("--tasa", type=float, default=50.0, help="pedidos por segundo (tope de seguridad: 200)")
    ap.add_argument("--hilos", type=int, default=16)
    ap.add_argument("--paises", default="ARG,BRA,ESP,MAR")
    ap.add_argument("--salida", default="evidencia/resultados_sin_secretos")
    args = ap.parse_args()
    if not 0 < args.tasa <= 200:
        ap.error("la tasa debe estar entre 0 y 200 pedidos/s para no saturar la notebook")

    corrida = datetime.now().strftime("%Y%m%d_%H%M%S")
    comentarios = generar_comentarios(corrida, args.cantidad, args.paises.split(","))
    inicio_utc = datetime.now(timezone.utc).isoformat()
    t = time.perf_counter()
    resultados = enviar(args.base_url, args.partido, comentarios, args.tasa, args.hilos)
    duracion = time.perf_counter() - t
    # Primero se guarda cada pedido: si la verificación falla (por ejemplo, Cassandra caída), no se pierde la corrida.
    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)
    with open(salida / f"pico_comentarios_{corrida}.jsonl", "w", encoding="utf-8") as f:
        for r in resultados:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    resumen = {
        "corrida": corrida, "inicio_utc": inicio_utc, "fin_utc": datetime.now(timezone.utc).isoformat(),
        "partido": args.partido, "tasa_objetivo_por_s": args.tasa, "hilos": args.hilos,
        "duracion_s": round(duracion, 2), "tasa_real_por_s": round(len(resultados) / duracion, 2),
        **resumir(resultados),
        "verificacion": verificar(args.base_url, args.partido, resultados),
    }
    (salida / f"pico_comentarios_{corrida}_resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resumen, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
