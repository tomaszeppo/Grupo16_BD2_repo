import re
from datetime import datetime

from app.adapters.base import operacion
from app.config.settings import Settings
from app.errors import ApiError, DependenciaNoDisponible, DependenciaTimeout, ValidacionError

FUENTE = "influxdb"
_RE_PARTIDO = re.compile(r"^P-\d{2,3}$")
_RE_EQUIPO = re.compile(r"^[A-Z]{3}$")
_INTERVALOS = {"1m": "1 minute", "5m": "5 minutes"}
TIPOS_DE_CORRIDA = ("demo", "carga")  # demostración o prueba de carga: se separan en el análisis


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def construir_sql(
    partido_id: str, desde: datetime, hasta: datetime, equipo: str | None, agregacion: str, limite: int
) -> str:
    """SQL fijo. Los únicos valores variables pasaron por regex/tipos estrictos (defensa en profundidad: se revalida acá)."""
    if not _RE_PARTIDO.fullmatch(partido_id) or (equipo is not None and not _RE_EQUIPO.fullmatch(equipo)):
        raise ValidacionError("Identificador de partido o equipo inválido.")
    filtro = f"partido_id = '{partido_id}' AND time >= '{_iso(desde)}' AND time < '{_iso(hasta)}'"
    if equipo:
        filtro += f" AND equipo_id = '{equipo}'"
    if agregacion == "raw":
        return (
            "SELECT time, equipo_id, fuente, posesion_pct, pases_completados, tiros, recuperaciones, velocidad_kmh "
            f"FROM estadisticas_partido WHERE {filtro} ORDER BY time, equipo_id, fuente LIMIT {int(limite)}"
        )
    intervalo = _INTERVALOS[agregacion]
    return (
        f"SELECT DATE_BIN(INTERVAL '{intervalo}', time, TIMESTAMP '1970-01-01T00:00:00Z') AS ventana, "
        "equipo_id, fuente, "
        "AVG(posesion_pct) AS posesion_pct_prom, SUM(pases_completados) AS pases_completados, SUM(tiros) AS tiros, "
        "SUM(recuperaciones) AS recuperaciones, AVG(velocidad_kmh) AS velocidad_kmh_prom, "
        "MAX(velocidad_kmh) AS velocidad_kmh_max "
        f"FROM estadisticas_partido WHERE {filtro} GROUP BY 1, 2, 3 ORDER BY 1, 2, 3 LIMIT {int(limite)}"
    )


def _traducir(exc: Exception) -> ApiError | None:
    try:
        import httpx
    except ImportError:
        return None
    if isinstance(exc, httpx.ConnectTimeout):
        return DependenciaNoDisponible(FUENTE)
    if isinstance(exc, httpx.TimeoutException):
        return DependenciaTimeout(FUENTE)
    if isinstance(exc, httpx.HTTPError):
        return DependenciaNoDisponible(FUENTE)
    return None


def _z(valor):
    if isinstance(valor, str) and re.match(r"^\d{4}-\d{2}-\d{2}T[\d:.]+$", valor):
        return valor.split(".")[0] + "Z"
    return valor


class InfluxAdapter:
    """InfluxDB 3 Core por HTTP (`/api/v3/query_sql`). Base `fixture2030_metrics`, tabla `estadisticas_partido`."""

    fuente = FUENTE

    def __init__(self, settings: Settings):
        self._s = settings
        self._http = None

    def _cli(self):
        if self._http is None:
            import httpx

            t = self._s.timeout_segundos
            self._http = httpx.Client(
                base_url=self._s.influx_url,
                timeout=httpx.Timeout(t),
                headers={"Authorization": f"Bearer {self._s.influx_token}"} if self._s.influx_token else {},
            )
        return self._http

    def consultar(self, sql: str) -> list[dict]:
        resp = self._cli().post("/api/v3/query_sql", json={"db": self._s.influx_db, "q": sql, "format": "json"})
        if resp.status_code != 200:  # credencial inválida, base inexistente, error del servidor: nunca [] ni el detalle
            raise DependenciaNoDisponible(FUENTE)
        return resp.json()

    def consultar_estadisticas(self, partido_id, desde, hasta, equipo, agregacion, limite) -> list[dict]:
        sql = construir_sql(partido_id, desde, hasta, equipo, agregacion, limite)
        with operacion(FUENTE, f"estadisticas_{agregacion}", _traducir):
            filas = self.consultar(sql)
        return [{k: _z(v) for k, v in fila.items()} for fila in filas]

    def ping(self) -> None:
        with operacion(FUENTE, "ping", _traducir):
            resp = self._cli().get("/ping")
            if resp.status_code != 200:
                raise DependenciaNoDisponible(FUENTE)

    def guardar_minuto(self, partido_id: str, minuto: int, local: str, visitante: str, instante, goles_minuto=None, acciones_minuto=None):
        """Dos muestras: posesión instantánea y acciones del minuto simulado."""
        import math
        if not _RE_PARTIDO.fullmatch(partido_id) or not _RE_EQUIPO.fullmatch(local) or not _RE_EQUIPO.fullmatch(visitante):
            raise ValidacionError("Identificador de partido o equipo inválido.")
        posesion = round(50 + 9 * math.sin(minuto / 8), 1)
        timestamp = int(instante.timestamp() * 1_000_000_000)
        lineas = []
        for lado, equipo, pct in ((0, local, posesion), (1, visitante, round(100 - posesion, 1))):
            acciones = acciones_minuto[lado] if acciones_minuto is not None else {}
            pases = max(0 if minuto == 0 else 3 + (minuto + lado * 2) % 5, acciones.get("Pase", 0))
            gol = (goles_minuto[lado] if goles_minuto is not None else int(minuto == (23 if lado == 0 else 75)))
            tiros = max(int(minuto > 0 and minuto % (8 + lado) == 0), gol + acciones.get("Tiro", 0))
            intentados = pases + (int(minuto % 3 == lado) if minuto else 0)
            tiros_arco = max(int(bool(tiros) and minuto % 2 == lado), gol)
            faltas = max(int(minuto > 0 and minuto % (11 + lado) == 0), acciones.get("Falta", 0))
            corners = int(bool(tiros) and minuto % 3 == lado)
            lineas.append(f"estadisticas_partido,partido_id={partido_id},equipo_id={equipo},fuente=simulacion "
                          f"minuto={minuto}i,posesion_pct={pct},pases_completados={pases}i,"
                          f"pases_intentados={intentados}i,tiros={tiros}i,tiros_arco={tiros_arco}i,"
                          f"faltas={faltas}i,corners={corners}i,goles={gol}i {timestamp}")
        with operacion(FUENTE, "guardar_minuto", _traducir):
            respuesta = self._cli().post("/api/v3/write_lp", params={"db": self._s.influx_db, "precision": "nanosecond"},
                                         content="\n".join(lineas) + "\n")
            if respuesta.status_code not in (200, 204):
                raise DependenciaNoDisponible(FUENTE)


    def _escribir(self, nombre: str, lineas: list[str]) -> None:
        with operacion(FUENTE, nombre, _traducir):
            respuesta = self._cli().post("/api/v3/write_lp", params={"db": self._s.influx_db, "precision": "nanosecond"},
                                         content="\n".join(lineas) + "\n")
            if respuesta.status_code not in (200, 204):
                raise DependenciaNoDisponible(FUENTE)

    @staticmethod
    def _validar_audiencia(partido_id, corrida_id, tipo, paises) -> None:
        if not _RE_PARTIDO.fullmatch(partido_id) or not re.fullmatch(r"[0-9a-f]{32}", corrida_id or ""):
            raise ValidacionError("Partido o corrida inválidos.")
        if tipo not in TIPOS_DE_CORRIDA or any(not _RE_EQUIPO.fullmatch(p) for p in paises):
            raise ValidacionError("Tipo de corrida o país inválido.")

    def guardar_audiencia(self, partido_id: str, minuto: int, corrida_id: str, tipo: str,
                          espectadores: dict[str, int], comentarios: dict[tuple[str, str], int], instante) -> None:
        """Espectadores y comentarios de un minuto, por país. Mismo instante que las estadísticas del minuto."""
        self._validar_audiencia(partido_id, corrida_id, tipo, list(espectadores) + [p for p, _ in comentarios])
        if any(origen not in ("usuario", "simulacion") for _, origen in comentarios):
            raise ValidacionError("Origen de comentario inválido.")
        ts = int(instante.timestamp() * 1_000_000_000)
        etiquetas = f"corrida_id={corrida_id},tipo={tipo}"
        lineas = [f"audiencia_partido,partido_id={partido_id},pais={pais},{etiquetas} "
                  f"espectadores={int(n)}i,minuto={int(minuto)}i {ts}" for pais, n in espectadores.items()]
        lineas += [f"comentarios_partido,partido_id={partido_id},pais={pais},origen={origen},{etiquetas} "
                   f"comentarios={int(n)}i,minuto={int(minuto)}i {ts}" for (pais, origen), n in comentarios.items()]
        if lineas:
            self._escribir("guardar_audiencia", lineas)

    def guardar_resumen_audiencia(self, partido_id: str, corrida_id: str, tipo: str, unicos: dict[str, int],
                                  instante) -> None:
        self._validar_audiencia(partido_id, corrida_id, tipo, list(unicos))
        ts = int(instante.timestamp() * 1_000_000_000)
        lineas = [f"audiencia_resumen,partido_id={partido_id},pais={pais},corrida_id={corrida_id},tipo={tipo} "
                  f"unicos={int(n)}i {ts}" for pais, n in unicos.items()]
        if lineas:
            self._escribir("guardar_resumen_audiencia", lineas)

    def guardar_jugadores(self, partido_id, minuto, plantel, jugadas, instante, corrida_id=None):
        """Una muestra por jugador/minuto; un único lote por minuto."""
        if not _RE_PARTIDO.fullmatch(partido_id) or not 0 <= minuto <= 90:
            raise ValidacionError("Partido o minuto inválido.")
        if instante.tzinfo is None:
            raise ValidacionError("El instante debe incluir zona horaria.")
        timestamp = int(instante.timestamp() * 1_000_000_000)
        if corrida_id is not None and not re.fullmatch(r"[0-9a-f]{32}", corrida_id):
            raise ValidacionError("Identificador de simulación inválido.")
        etiqueta = f",corrida_id={corrida_id}" if corrida_id else ""
        lineas = []
        for lado, (equipo, jugadores) in enumerate(plantel.items()):
            if not _RE_EQUIPO.fullmatch(equipo) or not jugadores:
                raise ValidacionError("Equipo o plantel inválido.")
            for numero, jugador in enumerate(jugadores):
                if not re.fullmatch(r"J-[A-Z]{3}-[0-9]{2}", jugador) or not jugador.startswith(f"J-{equipo}-"):
                    raise ValidacionError("Jugador inválido para el equipo.")
                propias = [j for j in jugadas if j['minuto'] == minuto and j['jugador'] == jugador]
                goles = sum(j['tipo'] == 'Gol' for j in propias)
                tiros = goles + sum(j['tipo'] == 'Tiro' for j in propias)
                pases = sum(j['tipo'] == 'Pase' for j in propias)
                faltas = sum(j['tipo'] == 'Falta' for j in propias)
                # El simulador atribuye exactamente 60 segundos de posesión por minuto.
                total = (30 + (minuto % 11) - 5) if lado == 0 else (30 - (minuto % 11) + 5)
                segundos = 0 if minuto == 0 else total // len(jugadores) + int(numero < total % len(jugadores))
                lineas.append(f"estadisticas_jugador_minuto,partido_id={partido_id},equipo_id={equipo},jugador_id={jugador}{etiqueta} "
                              f"minuto={minuto}i,pases_intentados={pases}i,pases_completados={pases}i,"
                              f"tiros={tiros}i,tiros_arco={goles}i,goles={goles}i,faltas={faltas}i,"
                              f"corners=0i,posesion_segundos={segundos}i {timestamp}")
        if corrida_id:
            if minuto == 0:
                equipo = next(iter(plantel))
                jugador = plantel[equipo][0]
                lineas.append(f"jugadas_partido,partido_id={partido_id},equipo_id={equipo},jugador_id={jugador},categoria=inicio,corrida_id={corrida_id} "
                              f"minuto=0i,orden=0i,evento_id=\"inicio\",resultado=\"registrado\" {timestamp}")
            categorias = {"Pase": "pase", "Tiro": "tiro", "Gol": "gol", "Falta": "falta", "Tarjeta amarilla": "amarilla", "Tarjeta roja": "roja", "Cambio": "cambio"}
            for jugada in (j for j in jugadas if j["minuto"] == minuto):
                equipo, jugador = jugada["equipo_id"], jugada["jugador"]
                categoria = categorias.get(jugada["tipo"])
                orden = jugada["orden"]
                if not categoria or equipo not in plantel or jugador not in plantel[equipo] or not isinstance(orden, int) or not 1 <= orden <= 999999:
                    raise ValidacionError("Jugada inválida para el plantel.")
                evento_id = jugada["id"]
                if not re.fullmatch(r"[A-Za-z0-9_-]+", evento_id):
                    raise ValidacionError("Identificador de jugada inválido.")
                # El orden agrega microsegundos estables para evitar colisiones.
                tiempo_evento = timestamp + orden * 1000
                resultado = "exitoso" if categoria in ("pase", "gol") else "registrado"
                lineas.append(f"jugadas_partido,partido_id={partido_id},equipo_id={equipo},jugador_id={jugador},categoria={categoria},corrida_id={corrida_id} "
                              f"minuto={minuto}i,orden={orden}i,evento_id=\"{evento_id}\",resultado=\"{resultado}\" {tiempo_evento}")
        with operacion(FUENTE, "guardar_jugadores", _traducir):
            respuesta = self._cli().post("/api/v3/write_lp", params={"db": self._s.influx_db, "precision": "nanosecond"}, content="\n".join(lineas) + "\n")
            if respuesta.status_code not in (200, 204):
                raise DependenciaNoDisponible(FUENTE)

    def muestras_jugadores(self, partido_id, corrida_id=None):
        if not _RE_PARTIDO.fullmatch(partido_id):
            raise ValidacionError("Identificador de partido inválido.")
        if corrida_id is not None and not re.fullmatch(r"[0-9a-f]{32}", corrida_id):
            raise ValidacionError("Identificador de simulación inválido.")
        filtro_corrida = f" AND corrida_id = '{corrida_id}'" if corrida_id else ""
        sql = ("SELECT equipo_id, jugador_id, minuto, pases_intentados, pases_completados, tiros, tiros_arco, "
               "goles, faltas, corners, posesion_segundos, time FROM estadisticas_jugador_minuto "
               f"WHERE partido_id = '{partido_id}'{filtro_corrida} ORDER BY equipo_id, jugador_id, minuto LIMIT 10000")
        with operacion(FUENTE, "muestras_jugadores", _traducir):
            return self.consultar(sql)

    def agregados_jugadores(self, partido_id):
        """Dos consultas agregadas en Influx: por equipo/minuto y por jugador."""
        if not _RE_PARTIDO.fullmatch(partido_id):
            raise ValidacionError("Identificador de partido inválido.")
        campos = "SUM(pases_intentados) AS pases_intentados, SUM(pases_completados) AS pases_completados, SUM(tiros) AS tiros, SUM(tiros_arco) AS tiros_arco, SUM(goles) AS goles, SUM(faltas) AS faltas, SUM(corners) AS corners, SUM(posesion_segundos) AS posesion_segundos"
        filtro = f" FROM estadisticas_jugador_minuto WHERE partido_id = '{partido_id}' "
        with operacion(FUENTE, "agregados_jugadores", _traducir):
            minutos = self.consultar("SELECT equipo_id, minuto, " + campos + filtro + "GROUP BY equipo_id, minuto ORDER BY equipo_id, minuto LIMIT 500")
            jugadores = self.consultar("SELECT equipo_id, jugador_id, " + campos + filtro + "GROUP BY equipo_id, jugador_id ORDER BY equipo_id, jugador_id LIMIT 100")
        return minutos, jugadores

    def eventos_partido(self, partido_id, corrida_id):
        if not _RE_PARTIDO.fullmatch(partido_id) or not re.fullmatch(r"[0-9a-f]{32}", corrida_id):
            raise ValidacionError("Partido o simulación inválidos.")
        sql = ("SELECT equipo_id, jugador_id, categoria, minuto, orden, evento_id, resultado, time "
               f"FROM jugadas_partido WHERE partido_id = '{partido_id}' AND corrida_id = '{corrida_id}' AND categoria != 'inicio' "
               "ORDER BY time LIMIT 10000")
        with operacion(FUENTE, "eventos_partido", _traducir):
            return self.consultar(sql)

    def agregados_eventos(self, partido_id, corrida_id):
        """Agrupa eventos en Influx y combina únicamente la posesión por minuto."""
        if not _RE_PARTIDO.fullmatch(partido_id) or not re.fullmatch(r"[0-9a-f]{32}", corrida_id):
            raise ValidacionError("Partido o simulación inválidos.")
        campos = ("SUM(CASE WHEN categoria = 'pase' THEN 1 ELSE 0 END) AS pases_intentados, "
                  "SUM(CASE WHEN categoria = 'pase' AND resultado = 'exitoso' THEN 1 ELSE 0 END) AS pases_completados, "
                  "SUM(CASE WHEN categoria IN ('tiro', 'gol') THEN 1 ELSE 0 END) AS tiros, "
                  "SUM(CASE WHEN categoria = 'gol' THEN 1 ELSE 0 END) AS tiros_arco, "
                  "SUM(CASE WHEN categoria = 'gol' THEN 1 ELSE 0 END) AS goles, "
                  "SUM(CASE WHEN categoria = 'falta' THEN 1 ELSE 0 END) AS faltas")
        sql = ("SELECT equipo_id, jugador_id, minuto, " + campos + " FROM jugadas_partido "
               f"WHERE partido_id = '{partido_id}' AND corrida_id = '{corrida_id}' "
               "GROUP BY equipo_id, jugador_id, minuto LIMIT 10000")
        # Al principio del encuentro puede no haberse creado aún la medición.
        muestras = self.muestras_jugadores(partido_id, corrida_id)
        if not muestras:
            return [], []
        with operacion(FUENTE, "agregados_eventos", _traducir):
            eventos = self.consultar(sql)
        por_clave = {(x['equipo_id'], x['jugador_id'], x['minuto']): x for x in eventos}
        campos_contables = ('pases_intentados', 'pases_completados', 'tiros', 'tiros_arco', 'goles', 'faltas')
        minutos, jugadores = {}, {}
        for muestra in muestras:
            equipo, jugador, minuto = muestra['equipo_id'], muestra['jugador_id'], muestra['minuto']
            evento = por_clave.get((equipo, jugador, minuto), {})
            valores = {campo: int(evento.get(campo) or 0) for campo in campos_contables}
            valores.update(corners=0, posesion_segundos=muestra['posesion_segundos'])
            for destino, clave, identidad in ((minutos, (equipo, minuto), {'equipo_id': equipo, 'minuto': minuto}),
                                             (jugadores, (equipo, jugador), {'equipo_id': equipo, 'jugador_id': jugador})):
                fila = destino.setdefault(clave, {**identidad, **{campo: 0 for campo in valores}})
                for campo, valor in valores.items():
                    fila[campo] += valor
        return list(minutos.values()), list(jugadores.values())

    def resumen_partido(self, partido_id: str) -> list[dict]:
        if not _RE_PARTIDO.fullmatch(partido_id):
            raise ValidacionError("Identificador de partido inválido.")
        base = ("SELECT equipo_id, AVG(posesion_pct) AS posesion_pct, SUM(tiros) AS tiros, "
                "SUM(pases_completados) AS pases_completados, MAX(minuto) AS minuto ")
        nuevos = (", SUM(tiros_arco) AS tiros_arco, SUM(faltas) AS faltas, SUM(corners) AS corners, "
                  "SUM(pases_intentados) AS pases_intentados, COUNT(tiros_arco) AS muestras_detalladas, "
                  "COUNT(*) AS muestras ")
        filtro = ("FROM estadisticas_partido "
                  f"WHERE partido_id = '{partido_id}' AND fuente = 'simulacion' GROUP BY equipo_id ORDER BY equipo_id")
        with operacion(FUENTE, "resumen_partido", _traducir):
            try:
                return self.consultar(base + nuevos + filtro)
            except DependenciaNoDisponible:
                # Las instalaciones antiguas pueden no tener todavía las columnas nuevas.
                return self.consultar(base + filtro)

    def muestras_partido(self, partido_id: str) -> list[dict]:
        """Muestras por equipo y minuto que sustentan el resumen histórico."""
        if not _RE_PARTIDO.fullmatch(partido_id):
            raise ValidacionError("Identificador de partido inválido.")
        sql = ("SELECT equipo_id, minuto, posesion_pct, tiros, tiros_arco, pases_completados, "
               "pases_intentados, faltas, corners, goles, time FROM estadisticas_partido "
               f"WHERE partido_id = '{partido_id}' AND fuente = 'simulacion' ORDER BY equipo_id, minuto LIMIT 500")
        with operacion(FUENTE, "muestras_partido", _traducir):
            return self.consultar(sql)
