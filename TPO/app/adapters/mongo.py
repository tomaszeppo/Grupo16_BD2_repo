from app.adapters.base import operacion
from app.config.settings import Settings
from app.dominio.ids import id_pronostico, id_usuario
from app.dominio.puntuacion import PUNTOS_EXACTO, PUNTOS_GANADOR, TOPE_ANTICIPACION
from app.errors import ApiError, DependenciaNoDisponible, DependenciaTimeout

FUENTE = "mongodb"
# Orden del ranking. Coincide con el índice de `puntajes`, así que el top N sale de recorrer el índice.
ORDEN_RANKING = [("puntos", -1), ("exactos", -1), ("tiempo_seg", -1), ("_id", 1)]


def _publico(doc: dict | None) -> dict | None:
    """Hacia afuera la clave se llama `id`; `_id` es un detalle de MongoDB."""
    if doc is None:
        return None
    return {"id": doc["_id"], **{k: v for k, v in doc.items() if k != "_id"}}


def _traducir(exc: Exception) -> ApiError | None:
    from pymongo.errors import ExecutionTimeout, NetworkTimeout, PyMongoError

    if isinstance(exc, (NetworkTimeout, ExecutionTimeout)):
        return DependenciaTimeout(FUENTE)
    if isinstance(exc, PyMongoError):
        return DependenciaNoDisponible(FUENTE)
    return None


class MongoAdapter:
    """Base `prode2030`: todo lo del prode y el catálogo de equipos y jugadores."""

    fuente = FUENTE

    def __init__(self, settings: Settings):
        self._s = settings
        self._client = None
        self._client_trabajo = None

    @property
    def db(self):
        if self._client is None:
            from pymongo import MongoClient

            ms = int(self._s.timeout_segundos * 1000)
            self._client = MongoClient(
                self._s.mongo_uri,
                serverSelectionTimeoutMS=ms,
                connectTimeoutMS=ms,
                socketTimeoutMS=ms,
                w="majority",  # una escritura confirmada sobrevive a la caída del primario
                retryWrites=True,  # si el primario cambia en medio de una escritura, el driver la repite una vez
                tz_aware=True,
            )
        return self._client[self._s.mongo_db]

    @property
    def db_lectura(self):
        """Para el ranking: puede leer de un secundario. Una tabla de posiciones tolera un instante de atraso."""
        from pymongo import ReadPreference

        return self.db.with_options(read_preference=ReadPreference.SECONDARY_PREFERRED)

    @property
    def db_trabajo(self):
        """Para la puntuación: mismas garantías de escritura, sin el tope de 3 s de los pedidos comunes."""
        if self._client_trabajo is None:
            from pymongo import MongoClient

            self._client_trabajo = MongoClient(
                self._s.mongo_uri, serverSelectionTimeoutMS=10000, socketTimeoutMS=600000,
                w="majority", retryWrites=True, tz_aware=True)
        return self._client_trabajo[self._s.mongo_db]

    # --- usuarios ---
    def crear_usuario(self, nombre: str, pais: str, ahora) -> dict:
        from pymongo import ReturnDocument

        with operacion(FUENTE, "crear_usuario", _traducir):
            # El contador se incrementa de forma atómica: dos altas simultáneas reciben números distintos.
            contador = self.db.contadores.find_one_and_update(
                {"_id": "usuarios"}, {"$inc": {"valor": 1}}, upsert=True, return_document=ReturnDocument.AFTER)
            doc = {"_id": id_usuario(contador["valor"]), "nombre": nombre, "pais": pais, "creado_en": ahora}
            self.db.usuarios.insert_one(doc)
            return _publico(doc)

    def obtener_usuario(self, usuario_id: str) -> dict | None:
        with operacion(FUENTE, "obtener_usuario", _traducir):
            return _publico(self.db.usuarios.find_one({"_id": usuario_id}))

    def existe_usuario(self, usuario_id: str) -> bool:
        with operacion(FUENTE, "existe_usuario", _traducir):
            return self.db.usuarios.count_documents({"_id": usuario_id}, limit=1) == 1

    # --- prodes privados ---
    def crear_prode(self, nombre: str, dueno: str, ahora) -> dict:
        import secrets

        from pymongo.errors import DuplicateKeyError

        with operacion(FUENTE, "crear_prode", _traducir):
            for _ in range(5):  # el código de invitación es al azar; si justo se repite, se sortea otro
                doc = {"_id": f"PR-{secrets.token_hex(4)}", "nombre": nombre, "dueno": dueno,
                       "codigo": secrets.token_hex(4).upper(), "integrantes": [dueno], "creado_en": ahora}
                try:
                    self.db.prodes.insert_one(doc)
                    return _publico(doc)
                except DuplicateKeyError:
                    continue
            raise RuntimeError("No se pudo generar un código de invitación único.")

    def unir_a_prode(self, codigo: str, usuario_id: str, maximo: int) -> tuple[str, dict | None]:
        """Devuelve ("unido" | "ya_estaba" | "lleno" | "no_existe", prode).

        El control del tope y el alta van en una sola operación: aunque varios se unan a la vez,
        MongoDB aplica de a una sobre el documento y ninguna puede pasar el máximo.
        """
        from pymongo import ReturnDocument

        with operacion(FUENTE, "unir_a_prode", _traducir):
            prode = self.db.prodes.find_one_and_update(
                {"codigo": codigo, "integrantes": {"$ne": usuario_id},
                 "$expr": {"$lt": [{"$size": "$integrantes"}, maximo]}},
                {"$addToSet": {"integrantes": usuario_id}},
                return_document=ReturnDocument.AFTER)
            if prode is not None:
                return "unido", _publico(prode)
            prode = self.db.prodes.find_one({"codigo": codigo})
            if prode is None:
                return "no_existe", None
            return ("ya_estaba" if usuario_id in prode["integrantes"] else "lleno"), _publico(prode)

    def prodes_de(self, usuario_id: str) -> list[dict]:
        with operacion(FUENTE, "prodes_de", _traducir):  # índice sobre prodes.integrantes
            cursor = self.db.prodes.find({"integrantes": usuario_id}).sort([("creado_en", 1), ("_id", 1)])
            return [_publico(p) for p in cursor]

    def obtener_prode(self, prode_id: str) -> dict | None:
        with operacion(FUENTE, "obtener_prode", _traducir):
            return _publico(self.db.prodes.find_one({"_id": prode_id}))

    # --- catálogo ---
    def listar_equipos(self) -> list[dict]:
        with operacion(FUENTE, "listar_equipos", _traducir):
            return [{"codigo": e["_id"], "nombre": e["nombre"], "grupo": e["grupo"]}
                    for e in self.db.equipos.find().sort("_id", 1)]

    def obtener_equipo(self, codigo: str) -> dict | None:
        with operacion(FUENTE, "obtener_equipo", _traducir):
            e = self.db.equipos.find_one({"_id": codigo})
            return {"codigo": e["_id"], "nombre": e["nombre"], "grupo": e["grupo"]} if e else None

    def listar_jugadores(self, codigo: str, posicion: str | None, limit: int, offset: int) -> tuple[list[dict], int]:
        filtro = {"equipo": codigo}  # índice {equipo, posicion}
        if posicion:
            filtro["posicion"] = posicion
        with operacion(FUENTE, "listar_jugadores", _traducir):
            total = self.db.jugadores.count_documents(filtro)
            cursor = self.db.jugadores.find(filtro).sort("dorsal", 1).skip(offset).limit(limit)
            return [_publico(j) for j in cursor], total

    # --- pronósticos ---
    def guardar_pronostico(self, usuario_id: str, partido_id: str, goles_local: int, goles_visitante: int,
                           ahora) -> tuple[dict, bool]:
        """Alta o corrección en una sola escritura. Devuelve el pronóstico y si fue alta."""
        from pymongo import ReturnDocument
        from pymongo.errors import DuplicateKeyError

        clave = id_pronostico(usuario_id, partido_id)
        with operacion(FUENTE, "guardar_pronostico", _traducir):
            for intento in (1, 2):
                try:
                    nuevos = {"goles_local": goles_local, "goles_visitante": goles_visitante, "cargado_en": ahora}
                    al_crear = {"usuario_id": usuario_id, "partido_id": partido_id, "creado_en": ahora}
                    # Se pide el documento anterior: si no había, fue un alta.
                    anterior = self.db.pronosticos.find_one_and_update(
                        {"_id": clave}, {"$set": nuevos, "$setOnInsert": al_crear},
                        upsert=True, return_document=ReturnDocument.BEFORE)
                    doc = {**(anterior or {"_id": clave, **al_crear}), **nuevos}
                    return _publico(doc), anterior is None
                except DuplicateKeyError:
                    # Dos altas simultáneas de la misma clave: una inserta y la otra choca. Al repetir, corrige.
                    if intento == 2:
                        raise

    def obtener_pronostico(self, usuario_id: str, partido_id: str) -> dict | None:
        with operacion(FUENTE, "obtener_pronostico", _traducir):
            return _publico(self.db.pronosticos.find_one({"_id": id_pronostico(usuario_id, partido_id)}))

    def pronosticos_del_partido(self, partido_id: str, usuario_ids: list[str]) -> dict[str, dict]:
        claves = [id_pronostico(usuario_id, partido_id) for usuario_id in usuario_ids]
        with operacion(FUENTE, "pronosticos_del_partido", _traducir):
            docs = self.db.pronosticos.find(
                {"_id": {"$in": claves}},
                {"_id": 0, "usuario_id": 1, "goles_local": 1, "goles_visitante": 1, "anulado": 1, "puntos": 1},
            )
            return {doc.pop("usuario_id"): doc for doc in docs}

    def pronosticos_de(self, usuario_id: str, limit: int, offset: int) -> tuple[list[dict], int]:
        with operacion(FUENTE, "pronosticos_de", _traducir):  # índice sobre pronosticos.usuario_id
            total = self.db.pronosticos.count_documents({"usuario_id": usuario_id})
            cursor = (self.db.pronosticos.find({"usuario_id": usuario_id})
                      .sort("partido_id", 1).skip(offset).limit(limit))
            return [_publico(p) for p in cursor], total

    # --- cierre de partido y puntuación ---
    def registrar_resultado(self, partido_id: str, goles_local: int, goles_visitante: int, clasificado: str | None,
                            inicio_programado, inicio_real, ahora) -> dict:
        """Guarda el resultado si no había uno y devuelve el que quedó registrado (puede ser uno anterior)."""
        from pymongo import ReturnDocument

        with operacion(FUENTE, "registrar_resultado", _traducir):
            doc = self.db.resultados.find_one_and_update(
                {"_id": partido_id},
                {"$setOnInsert": {
                    "goles_local": goles_local, "goles_visitante": goles_visitante, "clasificado": clasificado,
                    "inicio_programado": inicio_programado, "inicio_real": inicio_real, "cerrado_en": ahora,
                    "puntuacion": {"estado": "pendiente", "pasos": {}, "pronosticos": None,
                                   "iniciada_en": None, "terminada_en": None, "tomada_en": None},
                }},
                upsert=True, return_document=ReturnDocument.AFTER)
            return _publico(doc)

    def obtener_resultado(self, partido_id: str) -> dict | None:
        with operacion(FUENTE, "obtener_resultado", _traducir):
            return _publico(self.db.resultados.find_one({"_id": partido_id}))

    def tomar_puntuacion(self, partido_id: str, ahora, vencimiento_seg: float) -> dict | None:
        """Reserva la puntuación del partido para este proceso. None si otro la tiene o ya está completa.

        Es una sola operación atómica: aunque lleguen varios cierres a la vez, uno solo la toma. Una toma
        vieja (el proceso que la tenía se cayó) se puede volver a tomar pasado el vencimiento.
        """
        from datetime import timedelta

        from pymongo import ReturnDocument

        limite = ahora - timedelta(seconds=vencimiento_seg)
        with operacion(FUENTE, "tomar_puntuacion", _traducir):
            doc = self.db.resultados.find_one_and_update(
                {"_id": partido_id, "$or": [
                    {"puntuacion.estado": {"$in": ["pendiente", "fallida"]}},
                    {"puntuacion.estado": "en_curso", "puntuacion.tomada_en": {"$lt": limite}},
                ]},
                [{"$set": {"puntuacion.estado": "en_curso", "puntuacion.tomada_en": ahora,
                           "puntuacion.iniciada_en": {"$ifNull": ["$puntuacion.iniciada_en", ahora]},
                           "puntuacion.intentos": {"$add": [{"$ifNull": ["$puntuacion.intentos", 0]}, 1]}}}],
                return_document=ReturnDocument.AFTER)
            return _publico(doc)

    def puntuaciones_por_retomar(self, ahora, vencimiento_seg: float, max_intentos: int) -> list[str]:
        """Partidos cerrados cuya puntuación no terminó: pendiente, fallida o tomada por un proceso que ya no
        da señales. Deja afuera las que ya se intentaron `max_intentos` veces. `resultados` tiene a lo sumo
        104 documentos: no hace falta un índice."""
        from datetime import timedelta

        limite = ahora - timedelta(seconds=vencimiento_seg)
        with operacion(FUENTE, "puntuaciones_por_retomar", _traducir):
            cursor = self.db.resultados.find(
                {"puntuacion.intentos": {"$not": {"$gte": max_intentos}}, "$or": [
                    {"puntuacion.estado": {"$in": ["pendiente", "fallida"]}},
                    {"puntuacion.estado": "en_curso", "puntuacion.tomada_en": {"$lt": limite}},
                ]}, {"_id": 1}).sort("_id", 1)
            return [doc["_id"] for doc in cursor]

    def puntuar_pronosticos(self, partido_id: str, resultado: dict) -> int:
        """Puntúa todos los pronósticos del partido dentro de MongoDB, sin traerlos a la API.

        Aplica las reglas de app/dominio/puntuacion.py. Escribe el valor final de cada campo, así que
        repetirla deja lo mismo. Devuelve la cantidad de pronósticos del partido.
        """
        gl, gv = resultado["goles_local"], resultado["goles_visitante"]
        tuberia = [
            {"$set": {
                "anulado": {"$gte": ["$cargado_en", resultado["inicio_real"]]},
                "_exacto": {"$and": [{"$eq": ["$goles_local", gl]}, {"$eq": ["$goles_visitante", gv]}]},
                "_acierto": {"$eq": [{"$cmp": ["$goles_local", "$goles_visitante"]}, {"$cmp": [gl, gv]}]},
                "_anticipacion": {"$min": [TOPE_ANTICIPACION, {"$max": [0, {"$dateDiff": {
                    "startDate": "$cargado_en", "endDate": resultado["inicio_programado"], "unit": "second"}}]}]},
            }},
            {"$set": {
                "exacto": {"$and": ["$_exacto", {"$not": ["$anulado"]}]},
                "puntos": {"$cond": ["$anulado", 0, {"$cond": ["$_exacto", PUNTOS_EXACTO,
                                                              {"$cond": ["$_acierto", PUNTOS_GANADOR, 0]}]}]},
                "tiempo_seg": {"$toInt": {"$cond": ["$anulado", 0, {"$cond": [
                    "$_exacto", "$_anticipacion",
                    {"$cond": ["$_acierto", {"$floor": {"$divide": ["$_anticipacion", 2]}}, 0]}]}]}},
            }},
            {"$unset": ["_exacto", "_acierto", "_anticipacion"]},
        ]
        with operacion(FUENTE, "puntuar_pronosticos", _traducir):
            return self.db_trabajo.pronosticos.update_many({"partido_id": partido_id}, tuberia).matched_count

    def sumar_a_puntajes(self, partido_id: str) -> None:
        """Suma a cada usuario lo que hizo en este partido, salvo que ya lo tenga sumado.

        `aplicados` guarda qué partidos entraron en el total. Con eso repetir la suma no duplica puntos y el
        trabajo depende de los pronósticos de este partido, no de todo el torneo.
        """
        ya_aplicado = {"$in": [{"$literal": partido_id}, "$aplicados"]}

        def acumular(campo: str) -> dict:
            return {"$cond": [ya_aplicado, f"${campo}", {"$add": [f"${campo}", f"$$new.{campo}"]}]}

        tuberia = [
            {"$match": {"partido_id": partido_id}},  # índice sobre pronosticos.partido_id
            {"$project": {"_id": "$usuario_id", "puntos": 1, "tiempo_seg": 1,
                          "exactos": {"$cond": ["$exacto", 1, 0]}, "aplicados": [{"$literal": partido_id}]}},
            {"$merge": {"into": "puntajes", "on": "_id", "whenNotMatched": "insert", "whenMatched": [
                {"$set": {"puntos": acumular("puntos"), "exactos": acumular("exactos"),
                          "tiempo_seg": acumular("tiempo_seg"),
                          "aplicados": {"$setUnion": ["$aplicados", "$$new.aplicados"]}}}]}},
        ]
        with operacion(FUENTE, "sumar_a_puntajes", _traducir):
            self.db_trabajo.pronosticos.aggregate(tuberia)

    def guardar_foto(self, partido_id: str, ahora) -> None:
        """Versión histórica del ranking tras este partido: los 100 primeros y el total de usuarios."""
        with operacion(FUENTE, "guardar_foto", _traducir):
            self.db_trabajo.rankings_historicos.replace_one(
                {"_id": partido_id},
                {"generado_en": ahora, "total_usuarios": self.db_trabajo.puntajes.estimated_document_count(),
                 "primeros": self._top(self.db_trabajo, 100)},
                upsert=True)

    def renovar_toma(self, partido_id: str, ahora) -> None:
        """Señal de vida del proceso que está puntuando: mientras llegue, nadie más retoma la puntuación."""
        with operacion(FUENTE, "renovar_toma", _traducir):
            self.db.resultados.update_one({"_id": partido_id, "puntuacion.estado": "en_curso"},
                                          {"$set": {"puntuacion.tomada_en": ahora}})

    def marcar_paso(self, partido_id: str, paso: str, duracion_ms: float, extra: dict) -> None:
        cambios = {f"puntuacion.pasos.{paso}": duracion_ms, **{f"puntuacion.{k}": v for k, v in extra.items()}}
        with operacion(FUENTE, "marcar_paso", _traducir):
            self.db.resultados.update_one({"_id": partido_id}, {"$set": cambios})

    def cerrar_puntuacion(self, partido_id: str, estado: str, ahora) -> None:
        with operacion(FUENTE, "cerrar_puntuacion", _traducir):
            self.db.resultados.update_one(
                {"_id": partido_id}, {"$set": {"puntuacion.estado": estado, "puntuacion.terminada_en": ahora}})

    # --- ranking ---
    def _top(self, db, limit: int) -> list[dict]:
        filas = list(db.puntajes.find({}, {"aplicados": 0}).sort(ORDEN_RANKING).limit(limit))
        nombres = {u["_id"]: u["nombre"] for u in db.usuarios.find({"_id": {"$in": [f["_id"] for f in filas]}},
                                                                   {"nombre": 1})}
        return [{"puesto": n, "usuario_id": f["_id"], "nombre": nombres.get(f["_id"]), "puntos": f["puntos"],
                 "exactos": f["exactos"], "tiempo_seg": f["tiempo_seg"]} for n, f in enumerate(filas, start=1)]

    def top_puntajes(self, limit: int) -> list[dict]:
        with operacion(FUENTE, "top_puntajes", _traducir):  # recorre el índice del ranking y corta en `limit`
            return self._top(self.db_lectura, limit)

    def posicion_en_puntajes(self, usuario_id: str) -> dict | None:
        """Puesto de un usuario: hay que contar cuántos tienen mejor puntaje que él."""
        with operacion(FUENTE, "posicion_en_puntajes", _traducir):
            db = self.db_lectura
            yo = db.puntajes.find_one({"_id": usuario_id}, {"aplicados": 0})
            if yo is None:
                return None
            p, e, t = yo["puntos"], yo["exactos"], yo["tiempo_seg"]
            mejores = db.puntajes.count_documents({"$or": [
                {"puntos": {"$gt": p}},
                {"puntos": p, "exactos": {"$gt": e}},
                {"puntos": p, "exactos": e, "tiempo_seg": {"$gt": t}},
                {"puntos": p, "exactos": e, "tiempo_seg": t, "_id": {"$lt": usuario_id}},
            ]})
            return {"puesto": mejores + 1, "puntos": p, "exactos": e, "tiempo_seg": t,
                    "total_usuarios": db.puntajes.estimated_document_count()}

    def puntajes_de(self, usuario_ids: list[str]) -> list[dict]:
        with operacion(FUENTE, "puntajes_de", _traducir):
            db = self.db_lectura
            puntajes = {f["_id"]: f for f in db.puntajes.find({"_id": {"$in": usuario_ids}}, {"aplicados": 0})}
            nombres = {u["_id"]: u["nombre"] for u in db.usuarios.find({"_id": {"$in": usuario_ids}}, {"nombre": 1})}
            vacio = {"puntos": 0, "exactos": 0, "tiempo_seg": 0}
            return [{"usuario_id": u, "nombre": nombres.get(u),
                     **{k: puntajes.get(u, vacio)[k] for k in ("puntos", "exactos", "tiempo_seg")}}
                    for u in usuario_ids]

    def obtener_foto(self, partido_id: str) -> dict | None:
        with operacion(FUENTE, "obtener_foto", _traducir):
            return _publico(self.db.rankings_historicos.find_one({"_id": partido_id}))

    def ping(self) -> None:
        with operacion(FUENTE, "ping", _traducir):
            self.db.command("ping")
