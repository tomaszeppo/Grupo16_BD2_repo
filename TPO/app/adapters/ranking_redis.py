"""Puntuación y ranking de laboratorio en Redis, con procesamiento acotado por lotes."""
import json
import time
from datetime import datetime

import redis

from app.dominio.puntuacion import calcular
from app.dominio.ranking_redis import codificar_puntaje, miembro_redis, usuario_de_miembro
from app.errors import DependenciaNoDisponible

ZSET = "prode:ranking"
DATOS = "prode:ranking:datos"
NOMBRES = "prode:ranking:nombres"
LISTO = "prode:ranking:listo"
LUA_APLICAR = """
local ya = redis.call('HGET', KEYS[3], ARGV[1])
local total
if ya then
  local guardado = cjson.decode(ya)
  if guardado.estado ~= 'preparado' then return 0 end
  total = guardado.base
else
  local previo = redis.call('HGET', KEYS[2], ARGV[1])
  total = previo and cjson.decode(previo) or {puntos=0,exactos=0,tiempo_seg=0}
  -- Redis no revierte escrituras anteriores si un comando dentro del script falla.
  -- Conservar la base permite reintentar sin volver a incrementar el acumulado.
  redis.call('HSET', KEYS[3], ARGV[1], cjson.encode({estado='preparado',base=total}))
end
local resultado = cjson.decode(ARGV[3])
total.puntos = total.puntos + resultado.puntos
total.exactos = total.exactos + (resultado.exacto and 1 or 0)
total.tiempo_seg = total.tiempo_seg + resultado.tiempo_seg
local score = total.puntos * 100000000000 + total.exactos * 100000000 + total.tiempo_seg
redis.call('HSET', KEYS[2], ARGV[1], cjson.encode(total))
redis.call('ZADD', KEYS[1], score, ARGV[2])
redis.call('HSET', KEYS[3], ARGV[1], ARGV[3])
return 1
"""


def _lotes(iterable, tamano):
    lote = []
    for item in iterable:
        lote.append(item)
        if len(lote) >= tamano:
            yield lote
            lote = []
    if lote:
        yield lote


class RankingRedis:
    nombre = "redis"

    def __init__(self, mongo, settings, cliente=None):
        self.mongo = mongo
        self.lote = max(1, settings.redis_lote)
        self.demora = max(0, settings.redis_persistencia_demora_segundos)
        self.r = cliente or redis.Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=5,
                                                 socket_connect_timeout=5, health_check_interval=30)

    def _asegurar_ranking(self):
        if self.r.exists(LISTO):
            return
        # La reconstrucción es exclusiva y no publica un ranking parcialmente inicializado.
        with self.r.lock("prode:ranking:reconstruccion", timeout=3600, blocking_timeout=10):
            if self.r.exists(LISTO):
                return
            self.r.delete(ZSET, DATOS, NOMBRES)
            cursor = self.mongo.db.puntajes.find({}, {"puntos": 1, "exactos": 1, "tiempo_seg": 1}).batch_size(self.lote)
            for bloque in _lotes(cursor, self.lote):
                pipe = self.r.pipeline(transaction=False)
                ids = [f["_id"] for f in bloque]
                nombres = {u["_id"]: u.get("nombre", "") for u in self.mongo.db.usuarios.find({"_id": {"$in": ids}}, {"nombre": 1})}
                for f in bloque:
                    datos = {k: int(f.get(k, 0)) for k in ("puntos", "exactos", "tiempo_seg")}
                    pipe.hset(DATOS, f["_id"], json.dumps(datos))
                    pipe.zadd(ZSET, {miembro_redis(f["_id"]): codificar_puntaje(**datos)})
                    if f["_id"] in nombres:
                        pipe.hset(NOMBRES, f["_id"], nombres[f["_id"]])
                pipe.execute()
            self.r.set(LISTO, "1")

    def ping(self):
        try:
            self.r.ping()
        except redis.RedisError as exc:
            raise DependenciaNoDisponible("redis") from exc

    def preparar_partido(self, partido_id, al_avanzar=None):
        """Reserva un snapshot por partido, recorriendo Mongo sin cargarlo entero en memoria.

        `al_avanzar` se llama después de cada lote: quien puntúa lo usa para avisar que sigue trabajando."""
        with self.r.lock(f"prode:partido:{partido_id}:preparacion", timeout=3600, blocking_timeout=3600):
            return self._preparar_partido(partido_id, al_avanzar)

    def _preparar_partido(self, partido_id, al_avanzar=None):
        self._asegurar_ranking()
        clave = f"prode:partido:{partido_id}:pronosticos"
        cursor = self.mongo.db.pronosticos.find({"partido_id": partido_id},
            {"usuario_id": 1, "goles_local": 1, "goles_visitante": 1, "cargado_en": 1}).batch_size(self.lote)
        cantidad = 0
        for bloque in _lotes(cursor, self.lote):
            mapping = {}
            for p in bloque:
                mapping[p["usuario_id"]] = json.dumps({"goles_local": p["goles_local"], "goles_visitante": p["goles_visitante"],
                                                        "cargado_en": p["cargado_en"].isoformat()})
            if mapping:
                self.r.hset(clave, mapping=mapping)
                nombres = {u["_id"]: u.get("nombre", "") for u in self.mongo.db.usuarios.find({"_id": {"$in": list(mapping)}}, {"nombre": 1})}
                if nombres:
                    self.r.hset(NOMBRES, mapping=nombres)
                cantidad += len(mapping)
            if al_avanzar:
                al_avanzar()
        self.r.set(f"prode:partido:{partido_id}:preparado", "1")
        return cantidad

    def puntuar_en_redis(self, partido_id, resultado, al_avanzar=None):
        self._asegurar_ranking()
        # Se vuelve a leer al cerrar: una API con calendario en caché podría haber
        # aceptado una edición después del inicio; calcular() la marca anulada.
        self.preparar_partido(partido_id, al_avanzar)
        clave = f"prode:partido:{partido_id}:pronosticos"
        aplicados = f"prode:partido:{partido_id}:aplicados"
        cursor = self.r.hscan_iter(clave, count=self.lote)
        cantidad = 0
        for bloque in _lotes(cursor, self.lote):
            pipe = self.r.pipeline(transaction=False)
            ya_persistidos = {p["_id"] for p in self.mongo.db.puntajes.find(
                {"_id": {"$in": [usuario for usuario, _ in bloque]}, "aplicados": partido_id}, {"_id": 1})}
            for usuario, texto in bloque:
                p = json.loads(texto)
                valor = calcular(p["goles_local"], p["goles_visitante"], resultado["goles_local"], resultado["goles_visitante"],
                                 datetime.fromisoformat(p["cargado_en"]), resultado["inicio_programado"], resultado["inicio_real"])
                payload = json.dumps({"puntos": valor.puntos, "exacto": valor.exacto,
                                      "tiempo_seg": valor.tiempo_seg, "anulado": valor.anulado})
                if usuario in ya_persistidos:
                    pipe.hsetnx(aplicados, usuario, payload)
                else:
                    pipe.eval(LUA_APLICAR, 3, ZSET, DATOS, aplicados, usuario, miembro_redis(usuario), payload)
            pipe.execute()
            cantidad += len(bloque)
            if al_avanzar:
                al_avanzar()
        return cantidad

    def persistir_partido(self, partido_id, al_avanzar=None):
        """Escritura idempotente en Mongo de los resultados ya calculados en Redis."""
        from pymongo import UpdateOne

        from app.dominio.ids import id_pronostico
        aplicados = f"prode:partido:{partido_id}:aplicados"
        for bloque in _lotes(self.r.hscan_iter(aplicados, count=self.lote), self.lote):
            pronosticos, puntajes = [], []
            for usuario, texto in bloque:
                p = json.loads(texto)
                # Por su clave: MongoDB va directo al documento, sin pasar por un índice secundario.
                pronosticos.append(UpdateOne({"_id": id_pronostico(usuario, partido_id)}, {"$set": p}))
                previo = {"$in": [{"$literal": partido_id}, {"$ifNull": ["$aplicados", []]}]}
                campos = {}
                for nombre, valor in (("puntos", p["puntos"]), ("exactos", int(p["exacto"])), ("tiempo_seg", p["tiempo_seg"])):
                    campos[nombre] = {"$cond": [previo, {"$ifNull": [f"${nombre}", 0]},
                                                   {"$add": [{"$ifNull": [f"${nombre}", 0]}, valor]}]}
                campos["aplicados"] = {"$setUnion": [{"$ifNull": ["$aplicados", []]}, [partido_id]]}
                puntajes.append(UpdateOne({"_id": usuario}, [{"$set": campos}], upsert=True))
            if pronosticos:
                self.mongo.db.pronosticos.bulk_write(pronosticos, ordered=False)
                self.mongo.db.puntajes.bulk_write(puntajes, ordered=False)
            if al_avanzar:
                al_avanzar()

    def partido_puntuado(self, partido_id):
        pass

    def limpiar_partido(self, partido_id):
        self.r.delete(f"prode:partido:{partido_id}:pronosticos", f"prode:partido:{partido_id}:aplicados",
                      f"prode:partido:{partido_id}:preparado")

    def _nombres(self, usuarios):
        if not usuarios:
            return {}
        nombres = dict(zip(usuarios, self.r.hmget(NOMBRES, usuarios)))
        faltantes = [u for u, nombre in nombres.items() if nombre is None]
        if faltantes:
            encontrados = {u["_id"]: u["nombre"] for u in self.mongo.db.usuarios.find(
                {"_id": {"$in": faltantes}}, {"nombre": 1})}
            if encontrados:
                self.r.hset(NOMBRES, mapping=encontrados)
                nombres.update(encontrados)
        return nombres

    def top(self, limit):
        self._asegurar_ranking()
        usuarios = [usuario_de_miembro(x) for x in self.r.zrevrange(ZSET, 0, limit - 1)]
        datos = self.r.hmget(DATOS, usuarios) if usuarios else []
        nombres = self._nombres(usuarios)
        return [{"puesto": i, "usuario_id": u, "nombre": nombres.get(u), **json.loads(d)}
                for i, (u, d) in enumerate(zip(usuarios, datos), 1) if d]

    def posicion(self, usuario_id):
        self._asegurar_ranking()
        posicion = self.r.zrevrank(ZSET, miembro_redis(usuario_id))
        if posicion is None:
            return None
        texto = self.r.hget(DATOS, usuario_id)
        if texto is None:  # está en el orden pero sin sus datos: se informa como sin puntaje, no como error
            return None
        datos = json.loads(texto)
        return {"puesto": posicion + 1, **datos, "total_usuarios": self.r.zcard(ZSET)}

    def puntajes_de(self, usuario_ids):
        self._asegurar_ranking()
        valores = self.r.hmget(DATOS, usuario_ids) if usuario_ids else []
        nombres = self._nombres(usuario_ids)
        return [{"usuario_id": u, "nombre": nombres.get(u), **(json.loads(v) if v else {"puntos": 0, "exactos": 0, "tiempo_seg": 0})}
                for u, v in zip(usuario_ids, valores)]
