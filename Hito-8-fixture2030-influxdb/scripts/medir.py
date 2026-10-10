#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(f"Comando falló: {' '.join(cmd)}\n{p.stdout}\n{p.stderr}")
    return p.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description="Mide una carga real y una consulta real del laboratorio")
    parser.add_argument("--matches", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=2000)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()

    started = time.perf_counter()
    load_out = run([
        sys.executable, "scripts/carga_lotes.py",
        "--matches", str(args.matches),
        "--batch-size", str(args.batch_size),
        "--workers", str(args.workers),
    ])
    load_elapsed = time.perf_counter() - started

    token_file = ROOT / ".secrets" / "influxdb_admin_token"
    token = token_file.read_text(encoding="utf-8").strip()
    query = (
        "SELECT equipo_codigo, AVG(posesion_pct) AS promedio "
        "FROM estadisticas_partido "
        "WHERE partido_codigo = 'P-01' "
        "AND time >= '2030-06-15T18:30:00Z' "
        "AND time < '2030-06-15T18:40:00Z' "
        "GROUP BY equipo_codigo ORDER BY equipo_codigo"
    )
    q_start = time.perf_counter()
    query_out = run([
        "docker", "compose", "exec", "-T", "influxdb", "influxdb3", "query",
        "--database", "fixture2030_metrics", "--token", token,
        "--format", "csv", query,
    ])
    query_elapsed = time.perf_counter() - q_start

    print("=== MEDICIÓN REAL ===")
    print(f"Fecha UTC: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    print(f"Partidos: {args.matches}")
    print(f"Batch size: {args.batch_size}")
    print(f"Workers: {args.workers}")
    print(f"Tiempo carga (s): {load_elapsed:.3f}")
    print(f"Tiempo consulta agregada (s): {query_elapsed:.3f}")
    print("--- Salida carga ---")
    print(load_out)
    print("--- Salida consulta ---")
    print(query_out)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
