from pydantic import BaseModel, ConfigDict, Field

from app.dominio import ids


class SesionNueva(BaseModel):
    model_config = ConfigDict(extra="forbid")
    usuario_id: str = Field(pattern=ids.ID_USUARIO, description="Usuario con el que se entra, por ejemplo U0000001")
