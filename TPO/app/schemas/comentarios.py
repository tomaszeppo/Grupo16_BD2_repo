import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NuevoComentario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    comentario_id: uuid.UUID = Field(description="Lo genera quien comenta; repetirlo en un reintento no duplica")
    contenido: str = Field(min_length=1, max_length=280)

    @field_validator("contenido")
    @classmethod
    def validar_contenido(cls, texto: str) -> str:
        texto = texto.strip()
        if not texto:
            raise ValueError("El comentario no puede estar vacío.")
        return texto
