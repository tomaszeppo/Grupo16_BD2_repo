#!/usr/bin/env python3
"""Carga reproducible por lotes en InfluxDB 3 Core, particionada por partido."""
from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
from generador import chunked, iter_match_points, iter_users_points  # noqa: E402

HOST = "http://127.0.0.1:8181"
DB = "fixture2030_metrics"


def load_token() -> str:
    token_file = ROOT / ".secrets" / "influxdb_admin_token"
    if not token_file.exists():
        raise SystemExit("No existe .secrets/influxdb_admin_token. Ejecutá scripts/inicializacion.sh primero.")
    return token_file.read_text(encoding="utf-8").strip()


def send_batch(lines: Sequence[str], token: str, precision: str, retries: int) -> int:
    body = ("\n".join(lines) + "\n").encode("utf-8")
    query = urlencode({"db": DB, "precision": precision, "accept_partial": "false"})
    url = f"{HOST}/api/v3/write_lp?{query}"
    last_error = None
    for attempt in range(retries + 1):
        req = Request(
            url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "text/plain; charset=utf-8",
            },
        )
        try:
            with urlopen(req, timeout=120) as resp:
                if resp.status not in (200, 204):
                    raise RuntimeError(f"HTTP {resp.status}")
                return len(lines)
        except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Fallo permanente de lote de {len(lines)} puntos: {last_error}")


def load_one_match(idx: int, batch_size: int, token: str, precision: str, retries: int) -> int:
    count = 0
    for batch in chunked(iter_match_points(idx), batch_size):
        count += send_batch(batch, token, precision, retries)
    return count


def load_users(matches: int, batch_size: int, token: str, precision: str, retries: int) -> int:
    count = 0
    for batch in chunked(iter_users_points(matches), batch_size):
        count += send_batch(batch, token, precision, retries)
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Carga reproducible por lotes en InfluxDB 3 Core")
    parser.add_argument("--matches", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=2000)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--precision", default="second", choices=["second", "millisecond", "microsecond", "nanosecond"])
    args = parser.parse_args()
    if not 1 <= args.matches <= 127:
        parser.error("--matches debe estar entre 1 y 127")
    if args.batch_size < 100 or args.batch_size > 20000:
        parser.error("--batch-size debe estar entre 100 y 20000")
    if args.workers < 1 or args.workers > min(16, args.matches):
        parser.error("--workers debe estar entre 1 y la cantidad de partidos (máx. 16)")

    token = load_token()
    expected_stats = args.matches * 2 * 8 * 5000
    expected_users = args.matches * 12 * 5
    print("=== Carga InfluxDB 3 Core ===")
    print(f"Partidos: {args.matches}")
    print(f"Batch size: {args.batch_size}")
    print(f"Workers: {args.workers}")
    print(f"Puntos deportivos esperados: {expected_stats}")
    print(f"Puntos de usuarios esperados: {expected_users}")
    print(f"Puntos totales esperados: {expected_stats + expected_users}")
    print(f"Precisión: {args.precision}")
    print("Particionado: un worker procesa partidos completos para no mezclar la misma serie entre workers.")

    started = time.perf_counter()
    loaded_stats = 0
    completed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(load_one_match, idx, args.batch_size, token, args.precision, args.retries): idx
            for idx in range(1, args.matches + 1)
        }
        for fut in as_completed(futures):
            idx = futures[fut]
            loaded = fut.result()
            loaded_stats += loaded
            completed += 1
            elapsed = time.perf_counter() - started
            print(f"Partido {idx:03d} completado: {loaded} puntos | {completed}/{args.matches} | {elapsed:.2f}s")

    loaded_users = load_users(args.matches, args.batch_size, token, args.precision, args.retries)
    elapsed = time.perf_counter() - started
    loaded_total = loaded_stats + loaded_users
    rate = loaded_total / elapsed if elapsed else 0.0
    print("=== Resultado ===")
    print(f"Puntos deportivos cargados: {loaded_stats}")
    print(f"Puntos usuarios cargados: {loaded_users}")
    print(f"Puntos totales cargados: {loaded_total}")
    print(f"Tiempo observado (s): {elapsed:.3f}")
    print(f"Puntos/s observados: {rate:.2f}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
