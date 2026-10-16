import argparse
import importlib

from app.config.settings import Settings

ORDEN = ["mongo", "neo4j", "cassandra", "redis", "influx", "iris"]


def main() -> int:
    ap = argparse.ArgumentParser(description="Siembra datos sintéticos del Fixture 2030 (idempotente).")
    ap.add_argument("--solo", choices=ORDEN, help="Cargar solo una fuente")
    args = ap.parse_args()
    settings = Settings()
    fallos = 0
    for nombre in [args.solo] if args.solo else ORDEN:
        try:
            modulo = importlib.import_module(f"seed.cargar_{nombre}")
            print(f"[ok] {nombre}: {modulo.cargar(settings)}")
        except Exception as exc:  # herramienta de laboratorio: informa y continúa con las demás fuentes
            fallos += 1
            print(f"[ERROR] {nombre}: {type(exc).__name__}: {exc}")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
