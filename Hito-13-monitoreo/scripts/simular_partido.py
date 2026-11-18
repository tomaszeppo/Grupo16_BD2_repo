"""Simulación de laboratorio: un minuto de partido por segundo real."""
import argparse
import time
import uuid
import httpx

PAISES = ("ARG", "BRA", "ESP", "URU")


def ejecutar(api, partido):
    corrida = uuid.uuid4().hex
    with httpx.Client(base_url=api, timeout=10) as cliente:
        def pedir(metodo, ruta, **kwargs):
            r = cliente.request(metodo, ruta, **kwargs)
            r.raise_for_status()
            return r.json()

        detalle = pedir("GET", f"/partidos/{partido}/detalle")
        if detalle["estado"] != "Programado":
            raise ValueError("El partido debe estar programado.")
        # Cassandra crea las particiones al escribir; no hay que crear grupos vacíos.
        def comentarios(minuto):
            for pais in PAISES:
                pedir("POST", f"/partidos/{partido}/comentarios",
                      headers={"Idempotency-Key": f"sim-{corrida}-{minuto}-{pais}"},
                      json={"pais": pais, "usuario_id": "U001", "usuario_nombre": "Hincha simulado",
                            "contenido": f"Minuto {minuto}: ¡vamos {pais}!"})

        comentarios(0)
        print("Comentarios iniciales creados por región.", flush=True)
        pedir("POST", f"/partidos/{partido}/estado", json={"estado": "En juego"})
        inicio = time.monotonic()
        for minuto in range(91):
            espera = inicio + minuto - time.monotonic()
            if espera > 0:
                time.sleep(espera)
            local, visitante = int(minuto >= 23), int(minuto >= 75)
            pedir("PUT", f"/partidos/{partido}/simulacion",
                  json={"minuto": minuto, "local": local, "visitante": visitante})
            if minuto and minuto < 90:
                comentarios(minuto)
            if minuto % 10 == 0:
                print(f"Minuto {minuto}: {local}-{visitante}", flush=True)
        pedir("POST", f"/partidos/{partido}/estado", json={"estado": "Finalizado"})
        print("Partido finalizado.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True)
    parser.add_argument("--partido", required=True)
    args = parser.parse_args()
    ejecutar(args.api, args.partido)
