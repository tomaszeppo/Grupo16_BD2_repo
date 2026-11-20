"""Simulación de laboratorio y lectura de comentarios por región."""
import base64
import json
import random
import threading
import time
import uuid
import httpx
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from fastapi import APIRouter, Depends, Query
from app.config.settings import get_settings
from app.adapters.influx import InfluxAdapter
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.deps import _influx, get_influx, get_mongo, get_neo4j, get_partidos_admin_service, get_puntuacion_service, requiere_admin, usuario_actual
from app.errors import Conflicto, DependenciaNoDisponible, NoEncontrado, ValidacionError
from app.schemas.comunes import PartidoId
from app.observability import logger
from seed.cargar_guion_simulacion import obtener_o_crear

router = APIRouter(tags=["Simulaciones"])


def _influx_de_simulacion(influx, documento):
    return influx.para_simulacion(documento) if isinstance(influx, InfluxAdapter) else influx

@lru_cache
def cassandra():
    try:
        from cassandra.cluster import Cluster
        cluster = Cluster(["cassandra"], connect_timeout=5, protocol_version=4)
        session = cluster.connect("fixture2030")
        session.default_timeout = 5
        return session
    except Exception as exc:
        raise DependenciaNoDisponible("cassandra") from exc

def ventana(fecha):
    return fecha.replace(minute=fecha.minute // 30 * 30, second=0, microsecond=0)

COMENTARIOS = (
    "Qué lindo partido se está armando.", "¡Vamos, que todavía hay tiempo!",
    "Ese pase merecía terminar en gol.", "El mediocampo está dejando todo.",
    "No puedo mirar tranquilo este partido.", "Bien ahí, hay que seguir presionando.",
    "Qué nervios cada vez que se acercan al área.", "Hoy el arquero está inspirado.",
    "Se viene un final para el infarto.", "Necesitamos cuidar más la pelota.",
    "¡Qué oportunidad se escapó!", "La tribuna está a pleno hoy.",
    "Estoy siguiendo el partido desde casa.", "Qué bien está jugando el equipo.",
    "Con un poco más de precisión entra.", "No se puede regalar una pelota así.",
    "Partidazo, no me despego de la pantalla.", "Dale que se puede dar vuelta.",
    "Ufff, pasó cerquita.", "Qué pase metió, por favor.",
    "Che, ¿vieron esa jugada?", "Nooo, era por abajo.",
    "Dale, una más y entra.", "Me agarró un ataque con esa defensa.",
    "Buenísima esa recuperación.", "El arquero nos acaba de salvar.",
    "Aguanten, que falta un montón todavía.", "Está lindo para un gol ahora, eh.",
    "Qué nervios, no puedo ni tomar mate.", "La próxima hay que definirla mejor.",
    "Vamos equipo, metan una buena contra.", "Esa pelota pedía un pase más.",
    "Cómo está corriendo todo el equipo hoy.", "Qué partido raro, puede pasar cualquier cosa.",
    "Bien ahí, sigan tocando.", "Me levanté del sillón con esa.",
    "Hay que aprovechar estos minutos.", "Qué manera de sufrir este partido.",
    "El medio está jugando una barbaridad.", "Dale, dale, no aflojen ahora.",
)
NOMBRES = ("Luli", "Nico", "Mica", "Santi", "Fede", "Sofi", "Juli", "Tomi", "Vale", "Maru", "Fran", "Paz")
GOLES = ("¡Gooooool! ¡Qué locura!", "¡Gol! Se gritó con todo.", "¡Adentro! Cambia el partido.", "¡Qué momento para meterla!", "GOOOOL, me escuchó todo el edificio", "VAMOOOS, qué golazo",
         "Al finnn, lo veníamos pidiendo", "No puedo creer lo que acaba de pasar")


def guardar_comentario(partido, pais, nombre, contenido):
    ahora = datetime.now(timezone.utc)
    comentario_id = uuid.uuid4()
    try:
        cassandra().execute("INSERT INTO comentarios_por_partido_pais (partido_id,pais,ventana,creado_en,comentario_id,usuario_nombre,contenido) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (partido, pais, ventana(ahora), ahora, comentario_id, nombre, contenido))
    except Exception as exc:
        raise DependenciaNoDisponible("cassandra") from exc
    return {"comentario_id": str(comentario_id), "usuario_nombre": nombre,
            "contenido": contenido, "creado_en": ahora.isoformat()}


def escribir(partido, pais, minuto, es_gol=None):
    textos = GOLES if (minuto in (23, 75) if es_gol is None else es_gol) else COMENTARIOS
    guardar_comentario(partido, pais, random.choice(NOMBRES), random.choice(textos))


class NuevoComentario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contenido: str = Field(min_length=1, max_length=280)

    @field_validator("contenido")
    @classmethod
    def validar_contenido(cls, texto):
        texto = texto.strip()
        if not texto:
            raise ValueError("El comentario no puede estar vacío.")
        return texto


@router.post("/partidos/{partido_id}/comentarios", status_code=201)
def publicar_comentario(partido_id: PartidoId, cuerpo: NuevoComentario,
                        usuario_id: str = Depends(usuario_actual),
                        mongo=Depends(get_mongo), neo4j=Depends(get_neo4j)):
    partido = neo4j.obtener_partido(partido_id)
    if partido is None:
        raise NoEncontrado("No existe el partido.")
    if partido["estado"] != "En juego":
        raise Conflicto("Solo se puede comentar mientras el partido está en juego.")
    usuario = mongo.obtener_usuario(usuario_id)
    if usuario is None:
        raise NoEncontrado("No existe el usuario.")
    comentario = guardar_comentario(partido_id, usuario["pais"], usuario["nombre"], cuerpo.contenido)
    return {"fuente": "cassandra", "partido_id": partido_id, "pais": usuario["pais"], **comentario}


@router.get("/partidos/{partido_id}/comentarios/recientes")
def recientes(partido_id: PartidoId, pais: str = Query(pattern="^[A-Z]{3}$")):
    ahora = datetime.now(timezone.utc)
    actual = ventana(ahora)
    items = []
    try:
        for v in (actual, actual - timedelta(minutes=30)):
            filas = cassandra().execute("SELECT comentario_id,usuario_nombre,contenido,creado_en FROM comentarios_por_partido_pais WHERE partido_id=%s AND pais=%s AND ventana=%s LIMIT 20", (partido_id, pais, v))
            items.extend({"comentario_id": str(f.comentario_id), "usuario_nombre": f.usuario_nombre,
                          "contenido": f.contenido, "creado_en": f.creado_en.isoformat()} for f in filas)
            if len(items) >= 20: break
    except Exception as exc:
        raise DependenciaNoDisponible("cassandra") from exc
    return {"fuente":"cassandra", "partido_id":partido_id, "pais":pais, "items":items[:20]}

def _utc(fecha):
    return fecha.replace(tzinfo=timezone.utc) if fecha.tzinfo is None else fecha.astimezone(timezone.utc)


def _cursor_comentarios(ventana_actual, paging_state=None, partido_id=None, pais=None):
    datos = {"partido": partido_id, "pais": pais, "ventana": ventana_actual.isoformat(), "pagina": base64.urlsafe_b64encode(paging_state).decode("ascii") if paging_state else None}
    return base64.urlsafe_b64encode(json.dumps(datos, separators=(",", ":")).encode()).decode("ascii")


@router.get("/partidos/{partido_id}/comentarios/historial")
def historial_comentarios(partido_id: PartidoId, pais: str = Query(pattern="^[A-Z]{3}$"),
                           cursor: str | None = Query(default=None, max_length=4096),
                           mongo=Depends(get_mongo), neo4j=Depends(get_neo4j)):
    """Comentarios de un partido finalizado; cursor recorre ventanas y páginas de Cassandra."""
    from cassandra.query import SimpleStatement
    partido = neo4j.obtener_partido(partido_id)
    if not partido: raise NoEncontrado("No existe el partido.")
    if partido["estado"] != "Finalizado": raise Conflicto("El historial está disponible al finalizar el partido.")
    doc = mongo.db.simulaciones.find_one({"_id": partido_id}) or {}
    inicio = doc.get("inicio_comentarios") or doc.get("inicio_estadisticas") or partido.get("inicio_real")
    if inicio is None: raise NoEncontrado("No está registrada la fecha de inicio de comentarios.")
    # En simulaciones anteriores los comentarios se creaban poco antes del inicio de estadísticas.
    if not doc.get("inicio_comentarios"): inicio -= timedelta(minutes=2)
    resultado = mongo.obtener_resultado(partido_id)
    fin = doc.get("fin_comentarios") or (resultado or {}).get("cerrado_en")
    if fin is None: raise NoEncontrado("No está registrada la fecha de cierre del partido.")
    primera, ultima = ventana(_utc(inicio)), ventana(_utc(fin))
    actual, pagina = ultima, None
    if cursor:
        try:
            datos = json.loads(base64.b64decode(cursor.encode("ascii"), altchars=b"-_", validate=True))
            if datos.get("partido") != partido_id or datos.get("pais") != pais: raise ValueError()
            actual = _utc(datetime.fromisoformat(datos["ventana"]))
            pagina = base64.b64decode(datos["pagina"].encode("ascii"), altchars=b"-_", validate=True) if datos.get("pagina") else None
            if actual != ventana(actual) or actual < primera or actual > ultima: raise ValueError()
        except (ValueError, KeyError, TypeError, UnicodeError) as exc:
            raise ValidacionError("El cursor de comentarios no es válido.") from exc
    try:
        consulta = SimpleStatement("SELECT comentario_id,usuario_nombre,contenido,creado_en FROM comentarios_por_partido_pais WHERE partido_id=%s AND pais=%s AND ventana=%s", fetch_size=20)
        resultado_pagina = cassandra().execute(consulta, (partido_id, pais, actual), paging_state=pagina)
        items = [{"comentario_id":str(f.comentario_id), "usuario_nombre":f.usuario_nombre,
                  "contenido":f.contenido, "creado_en":f.creado_en.isoformat()} for f in resultado_pagina.current_rows]
        if resultado_pagina.has_more_pages:
            siguiente = _cursor_comentarios(actual, resultado_pagina.paging_state, partido_id, pais)
        elif actual > primera:
            siguiente = _cursor_comentarios(actual - timedelta(minutes=30), partido_id=partido_id, pais=pais)
        else:
            siguiente = None
    except Exception as exc:
        raise DependenciaNoDisponible("cassandra") from exc
    return {"fuente":"cassandra", "partido_id":partido_id, "pais":pais, "items":items, "next_cursor":siguiente}


class MinutoSimulado(BaseModel):
    model_config = ConfigDict(extra="forbid")
    minuto: int = Field(ge=0, le=90)


@router.post("/administracion/simulaciones/{partido_id}/muestras", dependencies=[Depends(requiere_admin)])
def registrar_muestra(partido_id: PartidoId, cuerpo: MinutoSimulado,
                      mongo=Depends(get_mongo), influx=Depends(get_influx)):
    """Recibe el minuto simulado y escribe la muestra temporal de la corrida activa."""
    col = mongo.db.simulaciones
    doc = col.find_one({"_id": partido_id})
    if not doc or doc.get("estado_simulacion") != "en_curso":
        raise Conflicto("No hay una simulación en curso.")
    influx = _influx_de_simulacion(influx, doc)
    minuto = cuerpo.minuto
    partido, jugadas = doc["partido"], doc["jugadas"]
    marcador = {lado: sum(1 for j in jugadas if j["tipo"] == "Gol" and j["minuto"] <= minuto
                          and j["equipo_id"] == partido[lado]["codigo"]) for lado in ("local", "visitante")}
    try:
        influx.guardar_jugadores(partido_id, minuto, doc["plantel_estadisticas"], jugadas,
                                doc["inicio_estadisticas"] + timedelta(seconds=minuto), doc["corrida_id"])
    except Exception:
        col.update_one({"_id": partido_id}, {"$set": {"estadisticas_estado": "fallida", "estadisticas_incompletas": True}})
        raise
    col.update_one({"_id": partido_id}, {"$set": {"minuto": minuto, "marcador": marcador,
                                                   "estadisticas_estado": "actualizada"}})
    return {"partido_id": partido_id, "minuto": minuto, "marcador": marcador}


def _ejecutar(partido_id, mongo, admin, puntuacion, neo=None):
    """Generador: usa HTTP para iniciar, publicar comentarios, muestras y cerrar."""
    col = mongo.db.simulaciones
    try:
        partido = admin._partido(partido_id)
        guion = obtener_o_crear(partido, mongo.db)
        jugadas = guion["jugadas"]
        plantel = {}
        for lado in ("local", "visitante"):
            equipo = partido[lado]["codigo"]
            jugadores = list(mongo.db.jugadores.find({"equipo": equipo}, {"_id": 1, "dorsal": 1}).sort("dorsal", 1))
            titulares = [j["_id"] for j in jugadores[:11]]
            protagonistas = [j["jugador"] for j in jugadas if j["equipo_id"] == equipo]
            if len(titulares) != 11 or any(j not in {x["_id"] for x in jugadores} for j in protagonistas):
                raise Conflicto("Plantel incompleto o jugador del guion inexistente.")
            plantel[equipo] = list(dict.fromkeys(titulares + protagonistas))
        corrida_id = uuid.uuid4().hex
        settings = get_settings()
        col.update_one({"_id": partido_id}, {"$set": {"jugadas": jugadas, "plantel_estadisticas": plantel,
                       "estadisticas_version": 3, "corrida_id": corrida_id, "influx_raw_db": settings.influx_raw_db}})
        with httpx.Client(base_url=settings.simulador_api_url, timeout=15, trust_env=False,
                          headers={"X-Admin-Clave": settings.admin_clave}) as http:
            def post(url, **kwargs):
                respuesta = http.post(url, **kwargs)
                respuesta.raise_for_status()
                return respuesta.json()
            usuarios = post("/administracion/hinchas-demo")["usuarios"]
            comentarios_por_segundo = max(1, min(10, settings.simulador_comentarios_por_region_segundo))
            # Los compañeros sintéticos también participan en el prode de prueba.
            # Se registra su pronóstico antes del inicio por el mismo endpoint público.
            for usuario in usuarios["ARG"]:
                rng = random.Random(f"{partido_id}:{usuario}")
                respuesta = http.put(f"/partidos/{partido_id}/pronostico", headers={"X-Usuario-Id": usuario},
                                     json={"goles_local": rng.randrange(4), "goles_visitante": rng.randrange(4)})
                if respuesta.status_code != 409:
                    respuesta.raise_for_status()
            partido = post(f"/partidos/{partido_id}/estado", json={"estado": "En juego"})["partido"]
            inicio_datos = datetime.now(timezone.utc).replace(microsecond=0)
            col.update_one({"_id": partido_id}, {"$set": {"inicio_comentarios": datetime.now(timezone.utc),
                "estado": "En juego", "estado_simulacion": "en_curso", "partido": partido,
                "minuto": 0, "marcador": {"local": 0, "visitante": 0}, "inicio_estadisticas": inicio_datos}})
            inicio = time.monotonic()
            marcador = {"local": 0, "visitante": 0}
            for minuto in range(91):
                time.sleep(max(0, inicio + minuto - time.monotonic()))
                marcador = post(f"/administracion/simulaciones/{partido_id}/muestras", json={"minuto": minuto})["marcador"]
                if minuto < 90:
                    es_gol = any(j["tipo"] == "Gol" and j["minuto"] == minuto for j in jugadas)
                    for pais, hinchas in usuarios.items():
                        for _ in range(comentarios_por_segundo):
                            post(f"/partidos/{partido_id}/comentarios", headers={"X-Usuario-Id": random.choice(hinchas)},
                                 json={"contenido": random.choice(GOLES if es_gol else COMENTARIOS)})
            local, visitante = marcador["local"], marcador["visitante"]
            clasificado = partido["local"]["codigo"] if partido["fase"] != "Fase de grupos" and local == visitante else None
            post(f"/partidos/{partido_id}/resultado", json={"goles_local": local, "goles_visitante": visitante,
                                                            "clasificado": clasificado})
            col.update_one({"_id": partido_id}, {"$set": {"fin_comentarios": datetime.now(timezone.utc),
                                                             "estado": "Finalizado", "archivo_estado": "pendiente"}})
            try:
                post(f"/administracion/simulaciones/{partido_id}/archivar")
            except Exception:
                logger.exception("archivo_estadisticas_pendiente partido=%s", partido_id)
    except Exception:
        logger.exception("simulacion_fallida partido=%s", partido_id)
        col.update_one({"_id": partido_id}, {"$set": {"estado_simulacion": "fallida"}})
    else:
        col.update_one({"_id": partido_id}, {"$set": {"estado_simulacion": "completa"}})

def _agregar_equipos(minutos):
    """Suma contadores por equipo; la posesión se calcula con segundos de ambos."""
    campos = ("pases_intentados", "pases_completados", "tiros", "tiros_arco", "goles", "faltas", "corners", "posesion_segundos")
    por_equipo = {}
    for fila in minutos:
        equipo = fila["equipo_id"]
        total = por_equipo.setdefault(equipo, {"equipo_id": equipo, "minuto": 0, "muestras": 0, "muestras_detalladas": 0, **{k: 0 for k in campos}})
        for campo in campos:
            total[campo] += fila[campo]
        total["minuto"] = max(total["minuto"], fila["minuto"])
        total["muestras"] += 1
        total["muestras_detalladas"] += 1
    segundos = sum(f["posesion_segundos"] for f in por_equipo.values())
    for total in por_equipo.values():
        total["posesion_pct"] = 100 * total["posesion_segundos"] / segundos if segundos else None
    por_minuto = {}
    for fila in minutos:
        por_minuto[fila["minuto"]] = por_minuto.get(fila["minuto"], 0) + fila["posesion_segundos"]
    for fila in minutos:
        denominador = por_minuto[fila["minuto"]]
        fila["posesion_pct"] = 100 * fila["posesion_segundos"] / denominador if denominador else 0.0
    return list(por_equipo.values())


def _validar_jugadores(doc, muestras):
    campos = ("pases_intentados", "pases_completados", "tiros", "tiros_arco", "goles", "faltas", "corners", "posesion_segundos")
    plantel = doc.get("plantel_estadisticas") or {}
    esperados = {(equipo, jugador, minuto) for equipo, jugadores in plantel.items() for jugador in jugadores for minuto in range(91)}
    claves = [(f.get("equipo_id"), f.get("jugador_id"), f.get("minuto")) for f in muestras]
    if len(claves) != len(set(claves)) or set(claves) != esperados or not esperados:
        raise Conflicto("Faltan muestras por jugador o existen duplicados.")
    for fila in muestras:
        if any(not isinstance(fila.get(c), int) or fila[c] < 0 for c in campos):
            raise Conflicto("Métrica por jugador inválida.")
        if fila["tiros_arco"] > fila["tiros"] or fila["goles"] > fila["tiros_arco"] or fila["pases_completados"] > fila["pases_intentados"]:
            raise Conflicto("Métricas inconsistentes para un jugador.")
    por_clave = {(f["jugador_id"], f["minuto"]): f for f in muestras}
    for jugada in doc.get("jugadas", []):
        fila = por_clave.get((jugada["jugador"], jugada["minuto"]))
        if not fila or fila["equipo_id"] != jugada["equipo_id"]:
            raise Conflicto("La jugada no corresponde a un jugador del plantel.")
    from collections import Counter
    requeridos = Counter((j["jugador"], j["minuto"], j["tipo"]) for j in doc.get("jugadas", []))
    for (jugador, minuto, tipo), cantidad in requeridos.items():
        campo = {"Gol": "goles", "Pase": "pases_completados", "Tiro": "tiros", "Falta": "faltas"}.get(tipo)
        if campo and por_clave[(jugador, minuto)][campo] < cantidad:
            raise Conflicto("Las estadísticas no incluyen las jugadas del jugador.")


def archivar_estadisticas(partido_id, mongo, neo, influx):
    """Importa muestras completas al grafo; repetir el proceso no crea duplicados."""
    col = mongo.db.simulaciones
    doc = col.find_one({"_id": partido_id})
    if not doc or doc.get("estado") != "Finalizado":
        raise Conflicto("El partido debe estar finalizado antes de archivar las estadísticas.")
    influx = _influx_de_simulacion(influx, doc)
    if doc.get("estadisticas_incompletas"):
        raise Conflicto("Faltan muestras de InfluxDB; no se puede afirmar que el histórico esté completo.")
    equipos = {doc["partido"]["local"]["codigo"], doc["partido"]["visitante"]["codigo"]}
    jugadores_resumen = []
    version = doc.get("estadisticas_version")
    if version in (2, 3):
        filas_jugador = []
    else:
        muestras = []
    # Influx puede tardar algunos segundos en hacer visible la última escritura.
    for intento in range(8):
        if version in (2, 3):
            filas_jugador = influx.muestras_jugadores(partido_id, doc["corrida_id"]) if version == 3 else influx.muestras_jugadores(partido_id)
            try:
                _validar_jugadores(doc, filas_jugador)
            except Conflicto:
                if intento == 7:
                    raise
                time.sleep(1)
                continue
            if version == 3:
                eventos = influx.eventos_partido(partido_id, doc["corrida_id"])
                esperados = {j["id"]: (j["equipo_id"], j["jugador"], j["minuto"], j["orden"], j["tipo"]) for j in doc.get("jugadas", [])}
                categorias = {"pase":"Pase", "tiro":"Tiro", "gol":"Gol", "falta":"Falta", "amarilla":"Tarjeta amarilla", "roja":"Tarjeta roja", "cambio":"Cambio"}
                observados = {e["evento_id"]: (e["equipo_id"], e["jugador_id"], e["minuto"], e["orden"], categorias.get(e["categoria"])) for e in eventos}
                if len(eventos) != len(observados) or observados != esperados:
                    if intento == 7:
                        raise Conflicto("Las jugadas en InfluxDB no coinciden con el guion.")
                    time.sleep(1)
                    continue
                muestras, jugadores_resumen = influx.agregados_eventos(partido_id, doc["corrida_id"])
            else:
                muestras, jugadores_resumen = influx.agregados_jugadores(partido_id)
        else:
            muestras = influx.muestras_partido(partido_id)
        claves = {(fila.get("equipo_id"), fila.get("minuto")) for fila in muestras}
        if len(muestras) == 182 and claves == {(equipo, minuto) for equipo in equipos for minuto in range(91)}:
            break
        if intento < 7: time.sleep(1)
    else:
        raise Conflicto("El histórico requiere las 91 muestras de ambos equipos, sin duplicados.")
    resumen = _agregar_equipos(muestras) if version in (2, 3) else influx.resumen_partido(partido_id)
    if len(resumen) != 2 or {fila.get("equipo_id") for fila in resumen} != equipos:
        raise Conflicto("Faltan los resúmenes de ambos equipos.")
    # Neo4j acepta propiedades escalares; la fecha se conserva como texto ISO.
    campos = ("equipo_id", "minuto", "posesion_pct", "tiros", "tiros_arco", "pases_completados", "pases_intentados", "faltas", "corners", "goles")
    if any(any(fila.get(campo) is None for campo in campos) for fila in muestras):
        raise Conflicto("Las muestras no tienen todas las métricas necesarias para el histórico.")
    jugadas = doc.get("jugadas")
    if not isinstance(jugadas, list) or not jugadas:
        raise Conflicto("Faltan las jugadas del guion guardadas en MongoDB; no se inventarán jugadores.")
    ids = set()
    for jugada in jugadas:
        if jugada.get("id") in ids or jugada.get("equipo_id") not in equipos or not jugada.get("jugador"):
            raise Conflicto("El guion contiene jugadas duplicadas o jugadores sin equipo válido.")
        if any(previa not in ids for previa in jugada.get("influido_por", [])):
            raise Conflicto("El guion contiene relaciones con jugadas inexistentes o posteriores.")
        ids.add(jugada["id"])
    if version == 3:
        tiempos = {evento["evento_id"]: str(evento["time"]) for evento in eventos}
        jugadas = [{**jugada, "timestamp": tiempos[jugada["id"]], "categoria": jugada["tipo"]} for jugada in jugadas]
    for muestra in muestras:
        esperados = sum(1 for j in jugadas if j["tipo"] == "Gol" and j["minuto"] == muestra["minuto"] and j["equipo_id"] == muestra["equipo_id"])
        if muestra["goles"] != esperados:
            raise Conflicto("Las jugadas de MongoDB no coinciden con los goles por minuto en InfluxDB.")
        acciones = [j for j in jugadas if j["minuto"] == muestra["minuto"] and j["equipo_id"] == muestra["equipo_id"]]
        if (muestra["tiros"] < sum(j["tipo"] in ("Tiro", "Gol") for j in acciones)
                or muestra["pases_completados"] < sum(j["tipo"] == "Pase" for j in acciones)
                or muestra["faltas"] < sum(j["tipo"] == "Falta" for j in acciones)):
            raise Conflicto("Las estadísticas de InfluxDB no incluyen todas las jugadas del guion de MongoDB.")
    marcador = doc.get("marcador") or {}
    for lado in ("local", "visitante"):
        codigo = doc["partido"][lado]["codigo"]
        if sum(f["goles"] for f in muestras if f["equipo_id"] == codigo) != marcador.get(lado):
            raise Conflicto("Los goles de InfluxDB no coinciden con el marcador final.")
    limpias = [{**{campo: fila[campo] for campo in campos}, "observado_en": str(fila.get("time", ""))} for fila in muestras]
    resumen_limpio = [{k: v for k, v in fila.items() if v is not None} for fila in resumen]
    if version == 3:
        influx.guardar_resumenes(partido_id, doc["corrida_id"], doc["inicio_estadisticas"], resumen_limpio, jugadores_resumen)
    if version in (2, 3):
        neo.archivar_estadisticas(partido_id, resumen_limpio, limpias, jugadas, jugadores_resumen)
    else:
        neo.archivar_estadisticas(partido_id, resumen_limpio, limpias, jugadas)
    col.update_one({"_id": partido_id}, {"$set": {"archivo_estado": "completo"}})
    return {"partido_id": partido_id, "equipos": len(resumen), "muestras": len(limpias), "jugadas": len(jugadas), "archivo_estado": "completo"}


@router.post("/administracion/simulaciones/{partido_id}/archivar", dependencies=[Depends(requiere_admin)])
def reintentar_archivo(partido_id: PartidoId, mongo=Depends(get_mongo), neo=Depends(get_neo4j), influx=Depends(get_influx)):
    return archivar_estadisticas(partido_id, mongo, neo, influx)


@router.get("/partidos/{partido_id}/historico")
def historico_partido(partido_id: PartidoId, neo=Depends(get_neo4j)):
    historico = neo.leer_estadisticas_archivadas(partido_id)
    if not historico:
        raise NoEncontrado("Todavía no hay estadísticas archivadas para este partido.")
    jugadas = neo.listar_eventos(partido_id, 100)
    return {"fuente": "neo4j", "partido_id": partido_id, **historico, "jugadas": jugadas}


@router.get("/partidos/{partido_id}/estadisticas")
def estadisticas_partido(partido_id: PartidoId, mongo=Depends(get_mongo), influx=Depends(get_influx), neo=Depends(get_neo4j)):
    """Promedio de posesión y suma de tiros/pases de la simulación."""
    doc = mongo.db.simulaciones.find_one({"_id": partido_id}, {"_id": 0, "partido": 1, "estadisticas_estado": 1, "estadisticas_incompletas": 1, "archivo_estado": 1, "estadisticas_version": 1, "corrida_id": 1, "influx_raw_db": 1})
    if not doc or "partido" not in doc:
        raise NoEncontrado("No hay estadísticas para este partido.")
    if doc.get("archivo_estado") == "completo":
        historico = neo.leer_estadisticas_archivadas(partido_id)
        if historico:
            return {"fuente": "neo4j", "equipos": historico["equipos"], "incompletas": False}
    if doc.get("estadisticas_estado") == "fallida":
        raise DependenciaNoDisponible("influxdb")
    influx = _influx_de_simulacion(influx, doc)
    if doc.get("estadisticas_version") == 3:
        minutos, _ = influx.agregados_eventos(partido_id, doc["corrida_id"])
        equipos = _agregar_equipos(minutos)
    elif doc.get("estadisticas_version") == 2:
        minutos, _ = influx.agregados_jugadores(partido_id)
        equipos = _agregar_equipos(minutos)
    else:
        equipos = influx.resumen_partido(partido_id)
    return {"fuente": "influxdb", "equipos": equipos, "incompletas": doc.get("estadisticas_incompletas", False)}


@router.get("/partidos/{partido_id}/estadisticas/jugadores")
def estadisticas_jugadores(partido_id: PartidoId, mongo=Depends(get_mongo), influx=Depends(get_influx), neo=Depends(get_neo4j)):
    doc = mongo.db.simulaciones.find_one({"_id": partido_id}, {"estadisticas_version": 1, "archivo_estado": 1, "estadisticas_incompletas": 1, "corrida_id": 1, "influx_raw_db": 1})
    if not doc or doc.get("estadisticas_version") not in (2, 3):
        raise NoEncontrado("Esta simulación no tiene estadísticas por jugador.")
    if doc.get("archivo_estado") == "completo":
        return {"fuente": "neo4j", "jugadores": neo.leer_resumenes_jugadores(partido_id), "incompletas": False}
    influx = _influx_de_simulacion(influx, doc)
    if doc.get("estadisticas_version") == 3:
        _, jugadores = influx.agregados_eventos(partido_id, doc["corrida_id"])
    else:
        _, jugadores = influx.agregados_jugadores(partido_id)
    return {"fuente": "influxdb", "jugadores": jugadores, "incompletas": doc.get("estadisticas_incompletas", False)}


@router.get("/partidos/{partido_id}/jugadas/temporales")
def jugadas_temporales(partido_id: PartidoId, mongo=Depends(get_mongo), influx=Depends(get_influx), neo=Depends(get_neo4j)):
    doc = mongo.db.simulaciones.find_one({"_id": partido_id}, {"estadisticas_version": 1, "corrida_id": 1, "estadisticas_incompletas": 1, "archivo_estado": 1, "influx_raw_db": 1})
    if doc and doc.get("archivo_estado") == "completo":
        categorias = {"Pase":"pase", "Tiro":"tiro", "Gol":"gol", "Falta":"falta", "Tarjeta amarilla":"amarilla", "Tarjeta roja":"roja", "Cambio":"cambio"}
        eventos = neo.listar_eventos(partido_id, 10000) or []
        jugadas = [{"evento_id": e["id"], "minuto": e["minuto"], "equipo_id": (e.get("jugador") or {}).get("equipo"),
                    "jugador_id": (e.get("jugador") or {}).get("id"), "categoria": categorias.get(e["tipo"], e["tipo"].lower()),
                    "resultado": "exitoso" if e["tipo"] in ("Pase", "Gol") else "registrado"} for e in eventos]
        return {"fuente": "neo4j", "partido_id": partido_id, "jugadas": jugadas, "incompletas": False}
    if not doc or doc.get("estadisticas_version") != 3:
        raise NoEncontrado("Esta simulación no tiene jugadas temporales.")
    influx = _influx_de_simulacion(influx, doc)
    return {"fuente": "influxdb", "partido_id": partido_id,
            "jugadas": influx.eventos_partido(partido_id, doc["corrida_id"]),
            "incompletas": doc.get("estadisticas_incompletas", False)}


@router.get("/en-vivo/partidos")
def partidos_en_vivo(mongo=Depends(get_mongo)):
    """Fichas de simulaciones activas guardadas en MongoDB."""
    docs = mongo.db.simulaciones.find({"estado": "En juego"}, {"_id": 0})
    return {"fuente": "mongodb", "partidos": list(docs)}

@router.get("/en-vivo/partidos/{partido_id}")
def partido_en_vivo(partido_id: PartidoId, mongo=Depends(get_mongo)):
    from app.errors import NoEncontrado
    doc = mongo.db.simulaciones.find_one({"_id": partido_id}, {"_id": 0})
    if not doc or "partido" not in doc:
        raise NoEncontrado("No hay una simulación para este partido.")
    return {"fuente": "mongodb", **doc}

@router.post("/administracion/simulaciones/{partido_id}", status_code=202, dependencies=[Depends(requiere_admin)])
def iniciar(partido_id: PartidoId, mongo=Depends(get_mongo), admin=Depends(get_partidos_admin_service), puntuacion=Depends(get_puntuacion_service), neo=Depends(get_neo4j)):
    partido = admin._partido(partido_id)
    if partido["estado"] != "Programado" or not partido["local"] or not partido["visitante"]:
        raise Conflicto("Elegí un partido programado con equipos definidos.")
    cassandra()
    try:
        mongo.db.simulaciones.insert_one({"_id":partido_id, "estado_simulacion":"iniciando"})
    except Exception as exc:
        from pymongo.errors import DuplicateKeyError
        if not isinstance(exc, DuplicateKeyError):
            raise
        reinicio = mongo.db.simulaciones.replace_one(
            {"_id": partido_id, "estado_simulacion": "fallida"},
            {"_id": partido_id, "estado_simulacion": "iniciando"},
        )
        if reinicio.modified_count != 1:
            raise Conflicto("Ya existe una simulación activa o finalizada para este partido.") from exc
    threading.Thread(target=_ejecutar, args=(partido_id,mongo,admin,puntuacion,neo), daemon=True).start()
    return {"partido_id":partido_id,"estado":"iniciando"}

@router.get("/administracion/simulaciones/{partido_id}", dependencies=[Depends(requiere_admin)])
def estado(partido_id: PartidoId, mongo=Depends(get_mongo)):
    return mongo.db.simulaciones.find_one({"_id":partido_id}, {"_id":0}) or {"estado_simulacion":"sin iniciar"}
