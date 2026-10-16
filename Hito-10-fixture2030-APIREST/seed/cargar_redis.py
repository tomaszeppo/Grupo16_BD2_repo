import redis

from app.adapters.redis import clave_sesion
from app.config.settings import Settings
from seed import datos


def cargar(s: Settings) -> str:
    r = redis.Redis(host=s.redis_host, port=s.redis_port, password=s.redis_password or None, decode_responses=True)
    for uid, estado in datos.SESIONES:
        clave = clave_sesion(uid)
        pipe = r.pipeline()
        pipe.delete(clave)
        pipe.hset(clave, mapping={
            "session_id": f"S-DEMO-{uid[1:]}", "usuario_id": uid, "rol": "fan", "estado_acceso": estado,
            "creado_en": "2030-06-14T10:00:00-03:00", "ultimo_acceso": "2030-06-14T10:05:00-03:00",
            "acciones": 1, "token_ref": f"DEMO-NO-SECRETO-{uid[1:]}",
        })
        pipe.expire(clave, 1800)  # TTL de inactividad de 30 min (Hito 7)
        pipe.execute()
    r.set("f2030:cache:partido:P-01:resumen", '{"id":"P-01"}', ex=300)
    return f"{len(datos.SESIONES)} sesiones (TTL 1800 s; volver a sembrar con --solo redis si expiran)"
