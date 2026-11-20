"""Cassandra: comentarios de los partidos, en dos datacenters (`america` y `europa`).

Cada usuario escribe y lee en el datacenter de su región, con consistencia LOCAL_ONE: no espera a la otra
región, que recibe la copia por detrás. Si su región no responde, se atiende desde la otra y se informa cuál
atendió: los comentarios priorizan seguir funcionando antes que la cercanía.
"""
from app import metricas
from app.adapters.base import operacion
from app.config.settings import Settings
from app.dominio.regiones import REGIONES, otra
from app.errors import ApiError, DependenciaNoDisponible, DependenciaTimeout

FUENTE = "cassandra"
# Por nombre: el módulo del driver que las define (cassandra.cluster) no carga en Windows sin libev.
_SIN_REGION = {"NoHostAvailable", "Unavailable", "ConnectionException", "ConnectionShutdown",
               "UnresolvableContactPoints", "RegionSinConexion"}


class RegionSinConexion(Exception):
    """No se pudo conectar a la región (caída antes del primer uso, nombre que no resuelve, etc.)."""
_DEMORA = {"OperationTimedOut", "ReadTimeout", "WriteTimeout"}

_CONSULTAS = {
    "insertar": "INSERT INTO fixture2030.comentarios_por_partido_pais (partido_id, pais, ventana, creado_en, comentario_id, "
                "usuario_nombre, contenido, origen) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
    "listar": "SELECT comentario_id, usuario_nombre, contenido, creado_en, origen FROM fixture2030.comentarios_por_partido_pais "
              "WHERE partido_id = ? AND pais = ? AND ventana = ? AND creado_en < ? LIMIT ?",
    "listar_instante": "SELECT comentario_id, usuario_nombre, contenido, creado_en, origen "
                       "FROM fixture2030.comentarios_por_partido_pais "
                       "WHERE partido_id = ? AND pais = ? AND ventana = ? AND creado_en = ?",
    "ping": "SELECT now() FROM system.local",
}


def _es_de_region(exc: Exception) -> bool:
    return type(exc).__name__ in _SIN_REGION | _DEMORA


def _traducir(exc: Exception) -> ApiError | None:
    nombre = type(exc).__name__
    if nombre in _DEMORA:
        return DependenciaTimeout(FUENTE)
    if nombre in _SIN_REGION or type(exc).__module__.startswith("cassandra"):
        return DependenciaNoDisponible(FUENTE)
    return None


class CassandraAdapter:
    fuente = FUENTE

    def __init__(self, settings: Settings):
        self._s = settings
        self._sesiones: dict = {}
        self._preparadas: dict = {}

    def _sesion(self, region: str):
        if region not in self._sesiones:
            try:
                self._sesiones[region] = self._conectar(region)
            except Exception as exc:  # cualquier falla al conectar cuenta como región caída: atiende la otra
                raise RegionSinConexion(region) from exc
        return self._sesiones[region]

    def _conectar(self, region: str):
        """Conexión a una región, al primer uso. Si falla, `_sesion` la informa como región caída."""
        from cassandra import ConsistencyLevel
        from cassandra.cluster import EXEC_PROFILE_DEFAULT, Cluster, ExecutionProfile
        from cassandra.policies import DCAwareRoundRobinPolicy, TokenAwarePolicy

        perfil = ExecutionProfile(
            load_balancing_policy=TokenAwarePolicy(DCAwareRoundRobinPolicy(local_dc=region)),
            consistency_level=ConsistencyLevel.LOCAL_ONE, request_timeout=self._s.timeout_segundos)
        contacto = self._s.cassandra_america if region == "america" else self._s.cassandra_europa
        cluster = Cluster([contacto], port=self._s.cassandra_puerto, protocol_version=4,
                          connect_timeout=self._s.timeout_segundos,
                          execution_profiles={EXEC_PROFILE_DEFAULT: perfil})
        return cluster.connect()

    def _preparada(self, sesion, nombre: str):
        clave = (id(sesion), nombre)
        if clave not in self._preparadas:
            self._preparadas[clave] = sesion.prepare(_CONSULTAS[nombre])
        return self._preparadas[clave]

    def _en(self, region: str, nombre: str, parametros: tuple) -> list:
        sesion = self._sesion(region)
        return list(sesion.execute(self._preparada(sesion, nombre), parametros))

    def _ejecutar(self, region: str, nombre: str, parametros: tuple) -> tuple[list, str]:
        """Ejecuta en la región pedida y, si no responde, en la otra. Devuelve (filas, región que atendió)."""
        with operacion(FUENTE, nombre, _traducir):
            try:
                return self._en(region, nombre, parametros), region
            except Exception as exc:
                if not _es_de_region(exc):
                    raise
                respaldo = otra(region)
                metricas.CASSANDRA_CAMBIO_REGION.labels(region, respaldo).inc()
                return self._en(respaldo, nombre, parametros), respaldo

    def guardar_comentario(self, region: str, c: dict) -> str:
        _, atendio = self._ejecutar(region, "insertar", (
            c["partido_id"], c["pais"], c["ventana"], c["creado_en"], c["comentario_id"], c["usuario_nombre"],
            c["contenido"], c["origen"]))
        return atendio

    def comentarios(self, region: str, partido_id: str, pais: str, ventana, antes_de,
                    limite: int) -> tuple[list[dict], str]:
        filas, atendio = self._ejecutar(region, "listar", (partido_id, pais, ventana, antes_de, int(limite)))
        return self._comentarios(filas, pais), atendio

    def comentarios_del_instante(self, region: str, partido_id: str, pais: str, ventana,
                                 instante) -> tuple[list[dict], str]:
        """Todos los comentarios de esa tribuna con exactamente esa hora. La hora se guarda al milisegundo, así
        que puede haber varios: el historial los pide para no partir ese grupo entre dos páginas."""
        filas, atendio = self._ejecutar(region, "listar_instante", (partido_id, pais, ventana, instante))
        return self._comentarios(filas, pais), atendio

    @staticmethod
    def _comentarios(filas, pais: str) -> list[dict]:
        return [{"comentario_id": str(f.comentario_id), "usuario_nombre": f.usuario_nombre, "contenido": f.contenido,
                 "creado_en": f.creado_en, "origen": f.origen or "usuario", "pais": pais} for f in filas]

    def ping_region(self, region: str) -> None:
        """Sin cambio de región: el estado de salud tiene que decir si ESTA región responde."""
        with operacion(FUENTE, f"ping_{region}", _traducir):
            self._en(region, "ping", ())


class _SaludRegion:
    """Envoltorio para /health/dependencias: una entrada por datacenter."""

    def __init__(self, cassandra, region: str):
        self._c, self._region = cassandra, region

    def ping(self) -> None:
        self._c.ping_region(self._region)


def salud_por_region(cassandra) -> dict:
    return {f"cassandra_{region}": _SaludRegion(cassandra, region) for region in REGIONES}
