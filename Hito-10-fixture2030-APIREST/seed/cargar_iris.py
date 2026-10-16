import iris

from app.config.settings import Settings
from seed import datos


def cargar(s: Settings) -> str:
    conn = iris.connect(s.iris_host, s.iris_port, s.iris_namespace, s.iris_user, s.iris_password)
    api = iris.createIRIS(conn)
    cur = conn.cursor()
    sede = {e[0]: e[1] for e in datos.ESTADIOS}
    creados = 0
    for p in datos.PARTIDOS:
        cur.execute("SELECT ID FROM Fixture.Partido WHERE Codigo = ?", [p["id"]])
        if cur.fetchone():
            continue  # idempotente: no se pisa un partido existente (puede haber cambiado de estado)
        obj = api.classMethodObject("Fixture.Partido", "%New")
        obj.set("Codigo", p["id"])
        obj.set("EquipoLocal", p["local"])
        obj.set("EquipoVisitante", p["visitante"])
        obj.set("FechaHora", f"{p['fecha']} 18:30:00")
        obj.set("Sede", sede[p["estadio"]])
        obj.set("Estado", "Programado")
        estado = datos.IRIS_ESTADO_INICIAL.get(p["id"])
        if estado and not obj.invoke("CambiarEstado", estado):
            raise RuntimeError(f"No se pudo pasar {p['id']} a {estado}")
        for tipo, minuto, jugador in datos.IRIS_EVENTOS.get(p["id"], []):
            if not obj.invoke("AgregarEvento", tipo, minuto, "", jugador):
                raise RuntimeError(f"Evento rechazado en {p['id']}: {tipo} {minuto}")
        if obj.invoke("%Save") != 1:
            raise RuntimeError(f"No se pudo guardar {p['id']}")
        creados += 1
    return f"{creados} partidos nuevos (los existentes se conservan)"
