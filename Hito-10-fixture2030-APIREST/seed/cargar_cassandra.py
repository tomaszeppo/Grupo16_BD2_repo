import uuid
from datetime import datetime
from pathlib import Path

from cassandra.cluster import Cluster

from app.config.settings import Settings

VENTANA = datetime(2030, 6, 15, 18, 30)
COMENTARIOS = [  # (minuto dentro de la ventana, usuario_id, nombre, texto, likes)
    (1, "U001", "Facundo", "¡Vamos Argentina!", 12), (3, "U002", "Gabriela", "Qué partidazo", 5),
    (7, "U003", "Hernán", "Gol de Argentina", 9), (12, "U001", "Facundo", "Increíble la defensa", 2),
    (20, "U002", "Gabriela", "Se viene el segundo tiempo", 0),
]
INS = (
    "INSERT INTO comentarios_por_partido_pais (partido_id, pais, ventana, creado_en, comentario_id, usuario_id, "
    "usuario_nombre, contenido, likes, estado_moderacion) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'PUBLICADO') IF NOT EXISTS"
)
INS_L = (
    "INSERT INTO comentarios_por_likes_partido_pais (partido_id, pais, ventana, likes, creado_en, comentario_id, "
    "usuario_nombre, contenido) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) IF NOT EXISTS"
)


def cargar(s: Settings) -> str:
    cluster = Cluster([s.cassandra_host], port=s.cassandra_port, protocol_version=4)
    ses = cluster.connect()
    texto = (Path(__file__).parent / "cassandra" / "esquema.cql").read_text(encoding="utf-8")
    for st in texto.split(";"):
        st = "\n".join(l for l in st.splitlines() if not l.strip().startswith("--")).strip()
        if st:
            ses.execute(st)
    ses.set_keyspace(s.cassandra_keyspace)
    for minuto, uid, nombre, contenido, likes in COMENTARIOS:
        creado = VENTANA.replace(minute=30 + minuto)
        cid = uuid.uuid5(uuid.NAMESPACE_URL, f"fixture2030/P-01/ARG/{minuto}/{uid}")
        ses.execute(INS, ("P-01", "ARG", VENTANA, creado, cid, uid, nombre, contenido, likes))
        ses.execute(INS_L, ("P-01", "ARG", VENTANA, likes, creado, cid, nombre, contenido))
    cluster.shutdown()
    return f"{len(COMENTARIOS)} comentarios en (P-01, ARG, 2030-06-15 18:30)"
