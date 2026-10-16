from app.errors import SesionNoVigente


class SesionesService:
    def __init__(self, repo):
        self._repo = repo

    def obtener(self, usuario_id: str) -> dict:
        datos = self._repo.obtener_sesion(usuario_id)
        if datos is None:
            raise SesionNoVigente(f"No existe una sesión vigente para '{usuario_id}' (inexistente o expirada).")
        if datos.get("estado_acceso") == "CERRADA":
            raise SesionNoVigente(f"La sesión de '{usuario_id}' fue cerrada.")
        return {  # whitelist: token_ref y cualquier otro campo interno no salen de la API
            "usuario_id": datos["usuario_id"], "session_id": datos["session_id"], "rol": datos["rol"],
            "estado_acceso": datos["estado_acceso"], "creado_en": datos["creado_en"],
            "ultimo_acceso": datos["ultimo_acceso"], "acciones": int(datos.get("acciones", 0)),
            "ttl_segundos": datos.get("ttl"),
        }

    def invalidar(self, usuario_id: str) -> None:
        self._repo.invalidar_sesion(usuario_id)
