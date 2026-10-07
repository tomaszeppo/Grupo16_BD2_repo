#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
from generador import iter_all_points  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera line protocol reproducible para el Fixture 2030")
    parser.add_argument("--matches", type=int, default=1, help="Cantidad de partidos a generar (1..127)")
    parser.add_argument("--output", default="generated/muestra.lp", help="Archivo de salida")
    args = parser.parse_args()
    if not 1 <= args.matches <= 127:
        parser.error("--matches debe estar entre 1 y 127")
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out.open("w", encoding="utf-8") as fh:
        for line in iter_all_points(args.matches):
            fh.write(line + "\n")
            count += 1
    print(f"Generados: {count} puntos")
    print(f"Archivo: {out}")
    print(f"Partidos: {args.matches}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
