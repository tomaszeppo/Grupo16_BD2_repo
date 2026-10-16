from pydantic import BaseModel, Field


class Sesion(BaseModel):
    usuario_id: str
    session_id: str
    rol: str
    estado_acceso: str = Field(examples=["ACTIVA"])
    creado_en: str
    ultimo_acceso: str
    acciones: int
    ttl_segundos: int | None = Field(description="Segundos restantes antes de que expire por inactividad")
