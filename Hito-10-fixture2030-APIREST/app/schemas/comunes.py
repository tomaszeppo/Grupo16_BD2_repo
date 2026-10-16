from typing import Annotated

from fastapi import Path, Query

IdPartido = Annotated[
    str, Path(pattern=r"^P-\d{2,3}$", description="Identificador de partido (P-01, P-02, …)", examples=["P-01"])
]
CodigoEquipo = Annotated[
    str, Path(pattern=r"^[A-Z]{3}$", description="Código FIFA de tres letras", examples=["ARG"])
]
IdUsuario = Annotated[
    str, Path(pattern=r"^U\d{3,6}$", description="Identificador de usuario (U001, …)", examples=["U001"])
]
LimitQuery = Annotated[int, Query(ge=1, le=100, description="Máximo de elementos por página (1–100)")]
