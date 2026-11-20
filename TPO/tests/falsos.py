"""Adaptadores falsos para las pruebas unitarias: guardan en memoria y permiten simular una caída.

Devuelven las mismas formas que los adaptadores reales; las pruebas de integración verifican a los reales.
"""
import copy

from app.dominio.puntuacion import calcular
from app.errors import DependenciaNoDisponible
from seed.datos import Fixture


class _Base:
    fuente = "?"

    def __init__(self):
        self.caida = False
        self.llamadas = 0

    def _verificar(self):
        self.llamadas += 1
        if self.caida:
            raise DependenciaNoDisponible(self.fuente)

    def ping(self) -> None:
        self._verificar()


def _pub(doc):
    return None if doc is None else {"id": doc["_id"], **{k: v for k, v in doc.items() if k != "_id"}}


class MongoFalso(_Base):
    fuente = "mongodb"

    def __init__(self):
        super().__init__()
        self.usuarios, self.prodes, self.pronosticos = {}, {}, {}
        self.equipos, self.jugadores = {}, {}
        self.resultados, self.puntajes, self.fotos = {}, {}, {}

    def crear_usuario(self, nombre, pais, ahora) -> dict:
        self._verificar()
        doc = {"_id": f"U{len(self.usuarios) + 1:07d}", "nombre": nombre, "pais": pais, "creado_en": ahora}
        self.usuarios[doc["_id"]] = doc
        return _pub(doc)

    def obtener_usuario(self, usuario_id):
        self._verificar()
        return _pub(self.usuarios.get(usuario_id))

    def existe_usuario(self, usuario_id) -> bool:
        self._verificar()
        return usuario_id in self.usuarios

    def crear_prode(self, nombre, dueno, ahora) -> dict:
        self._verificar()
        n = len(self.prodes) + 1
        doc = {"_id": f"PR-{n:08x}", "nombre": nombre, "dueno": dueno, "codigo": f"{n:08X}",
               "integrantes": [dueno], "creado_en": ahora}
        self.prodes[doc["_id"]] = doc
        return _pub(copy.deepcopy(doc))

    def unir_a_prode(self, codigo, usuario_id, maximo):
        self._verificar()
        prode = next((p for p in self.prodes.values() if p["codigo"] == codigo), None)
        if prode is None:
            return "no_existe", None
        if usuario_id in prode["integrantes"]:
            return "ya_estaba", _pub(copy.deepcopy(prode))
        if len(prode["integrantes"]) >= maximo:
            return "lleno", _pub(copy.deepcopy(prode))
        prode["integrantes"].append(usuario_id)
        return "unido", _pub(copy.deepcopy(prode))

    def prodes_de(self, usuario_id):
        self._verificar()
        return [_pub(copy.deepcopy(p)) for p in self.prodes.values() if usuario_id in p["integrantes"]]

    def obtener_prode(self, prode_id):
        self._verificar()
        return _pub(copy.deepcopy(self.prodes.get(prode_id)))

    def listar_equipos(self):
        self._verificar()
        return [{"codigo": e["_id"], "nombre": e["nombre"], "grupo": e["grupo"]} for e in self.equipos.values()]

    def obtener_equipo(self, codigo):
        self._verificar()
        e = self.equipos.get(codigo)
        return {"codigo": e["_id"], "nombre": e["nombre"], "grupo": e["grupo"]} if e else None

    def listar_jugadores(self, codigo, posicion, limit, offset):
        self._verificar()
        filas = [_pub(j) for j in self.jugadores.values()
                 if j["equipo"] == codigo and (posicion is None or j["posicion"] == posicion)]
        return filas[offset:offset + limit], len(filas)

    def guardar_pronostico(self, usuario_id, partido_id, goles_local, goles_visitante, ahora):
        self._verificar()
        clave = f"{usuario_id}:{partido_id}"
        anterior = self.pronosticos.get(clave)
        doc = {**(anterior or {"_id": clave, "usuario_id": usuario_id, "partido_id": partido_id, "creado_en": ahora}),
               "goles_local": goles_local, "goles_visitante": goles_visitante, "cargado_en": ahora}
        self.pronosticos[clave] = doc
        return _pub(doc), anterior is None

    def pronosticos_de(self, usuario_id, limit, offset):
        self._verificar()
        filas = sorted((_pub(p) for p in self.pronosticos.values() if p["usuario_id"] == usuario_id),
                       key=lambda p: p["partido_id"])
        return filas[offset:offset + limit], len(filas)

    # --- cierre, puntuación y ranking (mismas reglas que el adaptador real, con la función de dominio) ---
    def registrar_resultado(self, partido_id, goles_local, goles_visitante, clasificado, inicio_programado,
                            inicio_real, ahora) -> dict:
        self._verificar()
        if partido_id not in self.resultados:
            self.resultados[partido_id] = {
                "_id": partido_id, "goles_local": goles_local, "goles_visitante": goles_visitante,
                "clasificado": clasificado, "inicio_programado": inicio_programado, "inicio_real": inicio_real,
                "cerrado_en": ahora,
                "puntuacion": {"estado": "pendiente", "pasos": {}, "pronosticos": None, "iniciada_en": None,
                               "terminada_en": None, "tomada_en": None}}
        return _pub(copy.deepcopy(self.resultados[partido_id]))

    def obtener_resultado(self, partido_id):
        self._verificar()
        return _pub(copy.deepcopy(self.resultados.get(partido_id)))

    def tomar_puntuacion(self, partido_id, ahora, vencimiento_seg):
        self._verificar()
        r = self.resultados.get(partido_id)
        if r is None:
            return None
        p = r["puntuacion"]
        vencida = p["estado"] == "en_curso" and (ahora - p["tomada_en"]).total_seconds() > vencimiento_seg
        if p["estado"] not in ("pendiente", "fallida") and not vencida:
            return None
        p.update(estado="en_curso", tomada_en=ahora, iniciada_en=p["iniciada_en"] or ahora)
        return _pub(copy.deepcopy(r))

    def puntuar_pronosticos(self, partido_id, resultado) -> int:
        self._verificar()
        n = 0
        for p in self.pronosticos.values():
            if p["partido_id"] == partido_id:
                v = calcular(p["goles_local"], p["goles_visitante"], resultado["goles_local"],
                             resultado["goles_visitante"], p["cargado_en"], resultado["inicio_programado"],
                             resultado["inicio_real"])
                p.update(puntos=v.puntos, exacto=v.exacto, tiempo_seg=v.tiempo_seg, anulado=v.anulado)
                n += 1
        return n

    def sumar_a_puntajes(self, partido_id) -> None:
        self._verificar()
        for p in self.pronosticos.values():
            if p["partido_id"] != partido_id:
                continue
            fila = self.puntajes.setdefault(p["usuario_id"], {"_id": p["usuario_id"], "puntos": 0, "exactos": 0,
                                                              "tiempo_seg": 0, "aplicados": []})
            if partido_id in fila["aplicados"]:
                continue
            fila["puntos"] += p["puntos"]
            fila["exactos"] += 1 if p["exacto"] else 0
            fila["tiempo_seg"] += p["tiempo_seg"]
            fila["aplicados"].append(partido_id)

    def _ordenados(self):
        return sorted(self.puntajes.values(),
                      key=lambda f: (-f["puntos"], -f["exactos"], -f["tiempo_seg"], f["_id"]))

    def _fila(self, f):
        return {"usuario_id": f["_id"], "nombre": self.usuarios.get(f["_id"], {}).get("nombre"),
                "puntos": f["puntos"], "exactos": f["exactos"], "tiempo_seg": f["tiempo_seg"]}

    def top_puntajes(self, limit):
        self._verificar()
        return [{"puesto": n, **self._fila(f)} for n, f in enumerate(self._ordenados()[:limit], start=1)]

    def posicion_en_puntajes(self, usuario_id):
        self._verificar()
        for n, f in enumerate(self._ordenados(), start=1):
            if f["_id"] == usuario_id:
                return {"puesto": n, "puntos": f["puntos"], "exactos": f["exactos"], "tiempo_seg": f["tiempo_seg"],
                        "total_usuarios": len(self.puntajes)}
        return None

    def puntajes_de(self, usuario_ids):
        self._verificar()
        vacio = {"puntos": 0, "exactos": 0, "tiempo_seg": 0, "aplicados": []}
        return [self._fila({"_id": u, **{k: v for k, v in self.puntajes.get(u, vacio).items() if k != "_id"}})
                for u in usuario_ids]

    def guardar_foto(self, partido_id, ahora) -> None:
        self._verificar()
        self.fotos[partido_id] = {"_id": partido_id, "generado_en": ahora, "total_usuarios": len(self.puntajes),
                                  "primeros": self.top_puntajes(100)}

    def obtener_foto(self, partido_id):
        self._verificar()
        return _pub(copy.deepcopy(self.fotos.get(partido_id)))

    def marcar_paso(self, partido_id, paso, duracion_ms, extra) -> None:
        self._verificar()
        self.resultados[partido_id]["puntuacion"]["pasos"][paso] = duracion_ms
        self.resultados[partido_id]["puntuacion"].update(extra)

    def cerrar_puntuacion(self, partido_id, estado, ahora) -> None:
        self.resultados[partido_id]["puntuacion"].update(estado=estado, terminada_en=ahora)


class Neo4jFalso(_Base):
    fuente = "neo4j"

    def __init__(self, fixture: Fixture):
        super().__init__()
        equipos = {e["codigo"]: {"codigo": e["codigo"], "nombre": e["nombre"]} for e in fixture.equipos}
        estadios = {e["id"]: e for e in fixture.estadios}
        self.jugadores = {j["id"]: j for j in fixture.jugadores}
        self.equipos = equipos
        self.partidos = {}
        for p in fixture.partidos:
            self.partidos[p["id"]] = {
                "id": p["id"], "fecha_hora": p["fecha_hora"], "fase": p["fase"], "estado": p["estado"],
                "local": equipos.get(p["local"]), "visitante": equipos.get(p["visitante"]),
                "estadio": dict(estadios[p["estadio"]]), "goles_local": p["goles_local"],
                "goles_visitante": p["goles_visitante"], "inicio_real": p["inicio_real"],
            }
        self.eventos = {pid: [dict(e) for e in lista] for pid, lista in fixture.eventos.items()}

    def _evento(self, e: dict) -> dict:
        j = self.jugadores.get(e["jugador"])
        return {"id": e["id"], "tipo": e["tipo"], "minuto": e["minuto"], "orden": e["orden"],
                "jugador": {"id": j["id"], "nombre": j["nombre"], "apellido": j["apellido"],
                            "equipo": j["equipo"]} if j else None}

    # --- lecturas del fixture ---
    def listar_partidos(self, fase=None, fecha=None, estado=None) -> list[dict]:
        self._verificar()
        salida = [copy.deepcopy(p) for p in self.partidos.values()
                  if (fase is None or p["fase"] == fase) and (estado is None or p["estado"] == estado)
                  and (fecha is None or p["fecha_hora"].date() == fecha)]
        return sorted(salida, key=lambda p: (p["fecha_hora"], p["id"]))

    def obtener_partido(self, partido_id: str) -> dict | None:
        self._verificar()
        return copy.deepcopy(self.partidos.get(partido_id))

    def listar_eventos(self, partido_id: str, limit: int) -> list[dict] | None:
        self._verificar()
        if partido_id not in self.partidos:
            return None
        return [self._evento(e) for e in self.eventos.get(partido_id, [])][:limit]

    def cadena_de_evento(self, partido_id: str, evento_id: str) -> list[dict] | None:
        self._verificar()
        eventos = self.eventos.get(partido_id, [])
        if not any(e["id"] == evento_id for e in eventos):
            return None
        cadena, buscados = [], {evento_id}
        for e in reversed(eventos):
            if e["id"] in buscados or e["influye_en"] in buscados:
                buscados.add(e["id"])
                cadena.append(self._evento(e))
        return list(reversed(cadena))

    def camino_de_equipo(self, codigo: str) -> dict | None:
        self._verificar()
        if codigo not in self.equipos:
            return None
        partidos = [p for p in self.listar_partidos()
                    if codigo in ((p["local"] or {}).get("codigo"), (p["visitante"] or {}).get("codigo"))]
        return {"equipo": self.equipos[codigo], "partidos": partidos, "camino_a_la_final": []}

    def participacion_en_goles(self, limit: int) -> list[dict]:
        self._verificar()
        return []

    # --- operación del partido ---
    def iniciar_partido(self, partido_id, ahora) -> bool:
        self._verificar()
        p = self.partidos.get(partido_id)
        if p is None:
            return False
        if p["estado"] == "Programado":
            p.update(estado="En juego", inicio_real=ahora)
        return True

    def asignar_equipos(self, partido_id, local, visitante) -> bool:
        self._verificar()
        p = self.partidos.get(partido_id)
        if p is None or p["estado"] != "Programado" or p["fase"] == "Fase de grupos":
            return False
        p.update(local=self.equipos[local], visitante=self.equipos[visitante])
        return True

    def equipos_existentes(self, codigos):
        self._verificar()
        return {c for c in codigos if c in self.equipos}

    def revisar_evento(self, partido_id, evento):
        self._verificar()
        p = self.partidos.get(partido_id)
        if p is None:
            return None
        existente = None
        for pid, lista in self.eventos.items():
            for e in lista:
                if e["id"] == evento["id"]:
                    existente = {"tipo": e["tipo"], "minuto": e["minuto"], "orden": e["orden"], "partido": pid,
                                 "jugador": e["jugador"]}
        del_partido = self.eventos.get(partido_id, [])
        juegan = {(p["local"] or {}).get("codigo"), (p["visitante"] or {}).get("codigo")}
        jugador = self.jugadores.get(evento.get("jugador"))
        return {
            "estado": p["estado"], "existente": existente,
            "jugador_ok": jugador["id"] if jugador and jugador["equipo"] in juegan else None,
            "previas_ok": [e["id"] for e in del_partido if e["id"] in (evento.get("influido_por") or [])],
            "influido_por_existente": [e["id"] for e in del_partido if e["influye_en"] == evento["id"]],
        }

    def registrar_evento(self, partido_id, evento) -> None:
        self._verificar()
        lista = self.eventos.setdefault(partido_id, [])
        if any(e["id"] == evento["id"] for e in lista):
            return
        for e in lista:
            if e["id"] in (evento.get("influido_por") or []):
                e["influye_en"] = evento["id"]
        lista.append({"id": evento["id"], "tipo": evento["tipo"], "minuto": evento["minuto"],
                      "orden": evento["orden"], "jugador": evento.get("jugador"), "influye_en": None})
        lista.sort(key=lambda e: (e["minuto"], e["orden"], e["id"]))

    def contar_goles(self, partido_id):
        self._verificar()
        goles = {}
        for e in self.eventos.get(partido_id, []):
            if e["tipo"] == "Gol":
                equipo = self.jugadores[e["jugador"]]["equipo"] if e["jugador"] else None
                goles[equipo] = goles.get(equipo, 0) + 1
        return goles

    def finalizar_partido(self, partido_id, goles_local, goles_visitante) -> None:
        self._verificar()
        self.partidos[partido_id].update(estado="Finalizado", goles_local=goles_local, goles_visitante=goles_visitante)


class RedisFalso(_Base):
    """Redis en memoria con vencimientos según un reloj inyectable (por defecto, el de la máquina)."""

    fuente = "redis"

    def __init__(self, reloj=None):
        super().__init__()
        import time

        self.reloj = reloj or time.time
        self.valores: dict[str, tuple[object, float | None]] = {}
        self.publicados: list[tuple[str, str]] = []

    def _vivo(self, clave):
        par = self.valores.get(clave)
        if par is None:
            return None
        valor, vence = par
        if vence is not None and self.reloj() >= vence:
            del self.valores[clave]
            return None
        return valor

    def _poner(self, clave, valor, ttl=None):
        self.valores[clave] = (valor, None if ttl is None else self.reloj() + ttl)

    def guardar(self, clave, valor, ttl_seg):
        self._verificar()
        self._poner(clave, valor, ttl_seg)

    def guardar_varios(self, pares, ttl_seg):
        for clave, valor in pares.items():
            self.guardar(clave, valor, ttl_seg)

    def reservar(self, clave, valor, ttl_seg) -> bool:
        self._verificar()
        if self._vivo(clave) is not None:
            return False
        self._poner(clave, valor, ttl_seg)
        return True

    def leer(self, clave):
        self._verificar()
        return self._vivo(clave)

    def leer_renovando(self, clave, ttl_seg):
        self._verificar()
        self.renovaciones = getattr(self, "renovaciones", []) + [ttl_seg]
        valor = self._vivo(clave)
        if valor is not None:
            self._poner(clave, valor, ttl_seg)
        return valor

    def borrar(self, *claves):
        self._verificar()
        for clave in claves:
            self.valores.pop(clave, None)

    def incrementar(self, clave) -> int:
        self._verificar()
        valor = int(self._vivo(clave) or 0) + 1
        self._poner(clave, str(valor))
        return valor

    def tomar_y_borrar(self, clave) -> int:
        self._verificar()
        valor = self._vivo(clave)
        self.valores.pop(clave, None)
        return int(valor) if valor is not None else 0

    def agregar_a_conjunto(self, clave, miembro):
        self._verificar()
        conjunto = self._vivo(clave) or set()
        conjunto.add(miembro)
        self._poner(clave, conjunto)

    def miembros(self, clave) -> set:
        self._verificar()
        return set(self._vivo(clave) or set())

    def marcar(self, clave, miembro, puntaje):
        self._verificar()
        zset = self._vivo(clave) or {}
        zset[miembro] = puntaje
        self._poner(clave, zset)

    def quitar(self, clave, miembro):
        self._verificar()
        (self._vivo(clave) or {}).pop(miembro, None)

    def contar_desde(self, clave, minimo) -> int:
        self._verificar()
        zset = self._vivo(clave) or {}
        for miembro in [m for m, p in zset.items() if p < minimo]:
            del zset[miembro]
        return len(zset)

    def agregar_unico(self, clave, miembro):
        self.agregar_a_conjunto(clave, miembro)

    def contar_unicos(self, clave) -> int:
        return len(self.miembros(clave))

    def publicar(self, canal, mensaje):
        self._verificar()
        self.publicados.append((canal, mensaje))


class CassandraFalso(_Base):
    """Comentarios en memoria, con regiones que se pueden dar por caídas y el mismo cambio de región."""

    fuente = "cassandra"

    def __init__(self):
        super().__init__()
        self.caidas: set[str] = set()
        self.filas: dict = {}  # misma clave primaria = misma fila, como en Cassandra

    def _region(self, region):
        from app.dominio.regiones import otra

        self._verificar()
        if region not in self.caidas:
            return region
        if otra(region) not in self.caidas:
            return otra(region)
        raise DependenciaNoDisponible(self.fuente)

    def guardar_comentario(self, region, c) -> str:
        atendio = self._region(region)
        self.filas[(c["partido_id"], c["pais"], c["ventana"], c["creado_en"], c["comentario_id"])] = dict(c)
        return atendio

    def comentarios(self, region, partido_id, pais, ventana, antes_de, limite):
        atendio = self._region(region)
        filas = [dict(f, comentario_id=str(f["comentario_id"])) for (p, pa, v, _, _), f in self.filas.items()
                 if (p, pa, v) == (partido_id, pais, ventana) and f["creado_en"] < antes_de]
        filas.sort(key=lambda f: f["creado_en"], reverse=True)
        return filas[:limite], atendio

    def ping_region(self, region):
        self._verificar()
        if region in self.caidas:
            raise DependenciaNoDisponible(self.fuente)


class _PubSubFalso:
    def __init__(self, redis):
        self._redis = redis
        self.canales: set[str] = set()
        import asyncio

        self._cola = asyncio.Queue()

    async def subscribe(self, *canales):
        import asyncio

        if self._redis.caida:  # como el driver real: su propia excepción, no la de la API
            raise ConnectionError("redis caído")
        await asyncio.sleep(0)
        self.canales.update(canales)

    async def unsubscribe(self, *canales):
        import asyncio

        await asyncio.sleep(self._redis.demora_desuscribir)  # viaje de red: deja intercalar a otro espectador
        self.canales.difference_update(canales)

    async def get_message(self, ignore_subscribe_messages=True, timeout=1.0):
        import asyncio

        try:
            return await asyncio.wait_for(self._cola.get(), timeout)
        except asyncio.TimeoutError:
            return None

    async def aclose(self):
        self.canales.clear()


class RedisAsincronoFalso(_Base):
    """Lo que usa la conexión en vivo: suscripciones y presencia. `emitir` simula un PUBLISH de otro proceso."""

    fuente = "redis"

    def __init__(self):
        super().__init__()
        self.zsets: dict[str, dict[str, float]] = {}
        self.conjuntos: dict[str, set] = {}
        self.suscripciones: list[_PubSubFalso] = []
        self.demora_desuscribir = 0.0

    async def suscriptor(self):
        pubsub = _PubSubFalso(self)
        self.suscripciones.append(pubsub)
        return pubsub

    def emitir(self, canal: str, mensaje: str) -> None:
        for pubsub in self.suscripciones:
            if canal in pubsub.canales:
                pubsub._cola.put_nowait({"type": "message", "channel": canal, "data": mensaje})

    async def amarcar(self, clave, miembro, puntaje):
        self._verificar()
        self.zsets.setdefault(clave, {})[miembro] = puntaje

    async def aquitar(self, clave, miembro):
        import asyncio

        await asyncio.sleep(0)  # viaje de red: un punto donde llega una cancelación
        self._verificar()
        self.zsets.get(clave, {}).pop(miembro, None)

    async def asuscribir(self, pubsub, *canales):
        try:
            await pubsub.subscribe(*canales)
        except ConnectionError as exc:
            raise DependenciaNoDisponible(self.fuente) from exc

    async def adesuscribir(self, pubsub, *canales):
        await pubsub.unsubscribe(*canales)

    async def aleer(self, pubsub, timeout):
        return await pubsub.get_message(ignore_subscribe_messages=True, timeout=timeout)

    async def aagregar(self, clave_conjunto, miembro, clave_unicos, usuario):
        self._verificar()
        self.conjuntos.setdefault(clave_conjunto, set()).add(miembro)
        self.conjuntos.setdefault(clave_unicos, set()).add(usuario)
