"""Datos de muestra aislados por sesión. Nunca escriben en las bases del TPO."""
from datetime import datetime, timezone

EQUIPOS = [("ARG", "Argentina"), ("BRA", "Brasil"), ("ESP", "España"), ("FRA", "Francia"),
           ("GER", "Alemania"), ("ENG", "Inglaterra"), ("ITA", "Italia"), ("POR", "Portugal"),
           ("NED", "Países Bajos"), ("BEL", "Bélgica"), ("CRO", "Croacia"), ("URU", "Uruguay"),
           ("MEX", "México"), ("USA", "Estados Unidos"), ("CAN", "Canadá"), ("JPN", "Japón")]
ESTADIOS = [("Monumental", "Buenos Aires"), ("Maracaná", "Río de Janeiro"), ("Camp Nou", "Barcelona"),
            ("Wembley", "Londres"), ("Stade de France", "París"), ("Allianz Arena", "Múnich"),
            ("Azteca", "Ciudad de México"), ("Lusail", "Lusail")]
COMENTARIOS = []  # Tribuna demo compartida entre navegadores; nunca se mezcla con Cassandra.


def partido(numero):
    equipos = [{"codigo": c, "nombre": n} for c, n in EQUIPOS[(numero-1)*2:numero*2]]
    estadio, ciudad = ESTADIOS[numero-1]
    return {"id": f"P-{numero:02}", "fecha": f"2030-06-{14+(numero+3)//4}", "fase": "Fase de grupos",
            "equipos": equipos, "estadio": {"id": f"EST00{numero}", "nombre": estadio, "ciudad": ciudad},
            "resultado": {"ganador": "ARG", "perdedor": "BRA", "goles_ganador": 2,
                          "goles_perdedor": 1, "origen": "SIMULADO"} if numero == 1 else
                         {"ganador": "FRA", "perdedor": "ESP", "goles_ganador": 1,
                          "goles_perdedor": 0, "origen": "SIMULADO"} if numero == 2 else None}


def leer(path, params, sesion):
    partes = path.split("/")
    if partes[0] == "equipos":
        codigo = partes[1]
        if len(partes) == 2:
            return next(({"codigo": c, "nombre": n} for c, n in EQUIPOS if c == codigo), None)
        return {"equipo": codigo, "total": 5, "limit": 20, "offset": 0, "items": [
            {"nombre": n, "apellido": "Demo", "dorsal": i+1, "posicion": pos, "equipo": codigo}
            for i, (n, pos) in enumerate(zip(["Lucas", "Mateo", "Nicolás", "Diego", "Tomás"],
                ["Portero", "Defensa", "Centrocampista", "Delantero", "Delantero"]))]}
    numero = int(partes[1].split("-")[1])
    p = partido(numero)
    if len(partes) == 2:
        return p
    recurso = partes[2]
    if recurso == "detalle":
        return {"codigo": p["id"], "equipo_local": p["equipos"][0]["codigo"],
                "equipo_visitante": p["equipos"][1]["codigo"], "fecha_hora": p["fecha"]+"T18:30:00Z",
                "sede": p["estadio"]["nombre"], "estado": "En juego" if numero == 1 else "Finalizado" if numero == 2 else "Programado",
                "eventos": [{"tipo": "Gol", "minuto": 32, "descripcion": "Gol de Argentina"},
                            {"tipo": "Gol", "minuto": 61, "descripcion": "Gol de Brasil"}] if numero == 1 else []}
    if recurso == "eventos":
        return {"partido_id": p["id"], "limit": 50, "items": [
            {"id": "E-1", "tipo": "Inicio", "minuto": 0},
            {"id": "E-2", "tipo": "Gol", "minuto": 32}] if numero == 1 else
            [{"id": "E-3", "tipo": "Inicio", "minuto": 0},
             {"id": "E-4", "tipo": "Final", "minuto": 90}] if numero == 2 else []}
    if recurso == "comentarios":
        ventana, pais = params.get("ventana"), params.get("pais")
        items = [c for c in COMENTARIOS if c["partido_id"] == p["id"] and
                 c["pais"] == pais and c["ventana"] == ventana]
        if numero == 1 and pais == "ARG" and ventana == "2030-06-15T18:30:00Z":
            items += [{"comentario_id": f"demo-{i}", "usuario_id": "U003", "usuario_nombre": nombre,
                       "contenido": texto, "likes": likes, "estado_moderacion": "PUBLICADO",
                       "creado_en": f"2030-06-15T18:{45-i:02}:00Z"}
                      for i, (nombre, texto, likes) in enumerate([
                          ("Hernán", "Qué lindo volver a vivir un Mundial en casa 🇦🇷", 9),
                          ("Gabi", "¡Ese pase entre líneas! Vamos por el segundo 🙌", 5),
                          ("Facu", "La tribuna está increíble. ¡Vamos Argentina!", 12)])]
        return {"partido_id": p["id"], "pais": pais, "ventana": ventana, "limit": 20,
                "items": sorted(items, key=lambda c: c["creado_en"], reverse=True)[:20], "next_cursor": None}
    if recurso == "estadisticas":
        inicio = datetime.fromisoformat(params["desde"].replace("Z", "+00:00"))
        fin = datetime.fromisoformat(params["hasta"].replace("Z", "+00:00"))
        datos = numero <= 2 and inicio <= datetime(2030, 6, 15, 18, 30, tzinfo=timezone.utc) < fin
        return {"partido_id": p["id"], "desde": params["desde"], "hasta": params["hasta"],
                "agregacion": "1m", "truncado": False, "max_puntos": 500, "puntos": [
                    {"ventana": "2030-06-15T18:30:00Z", "equipo_id": e["codigo"], "fuente": "demo",
                     "posesion_pct_prom": 58 if i == 0 else 42, "pases_completados": 38 if i == 0 else 29,
                     "tiros": 4 if i == 0 else 2, "recuperaciones": 6 if i == 0 else 4,
                     "velocidad_kmh_prom": 12.3, "velocidad_kmh_max": 28.1}
                    for i, e in enumerate(p["equipos"])] if datos else []}
    return None
