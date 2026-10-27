"""
Traducción de los errores de dominio a códigos HTTP.

Un solo sitio decide el mapeo, de modo que todas las rutas responden igual ante
el mismo tipo de problema:

* `ExpedienteNoEncontrado` -> **404**, el recurso no existe.
* `TransicionInvalida`     -> **409**, el estado actual no admite la operación.
* `DatosInsuficientes`     -> **422**, falta información obligatoria.

Las validaciones de forma —tipos, rangos, campos ausentes— las resuelve Pydantic
antes de entrar al manejador y también devuelven 422.
"""

from fastapi import HTTPException

from services.workflow_service import (DatosInsuficientes, ErrorFlujo,
                                       ExpedienteNoEncontrado, TransicionInvalida)

CODIGOS = {
    ExpedienteNoEncontrado: 404,
    TransicionInvalida: 409,
    DatosInsuficientes: 422,
}


def a_http(error: ErrorFlujo) -> HTTPException:
    """Convierte un error de negocio en su `HTTPException` equivalente."""
    for tipo, codigo in CODIGOS.items():
        if isinstance(error, tipo):
            return HTTPException(status_code=codigo, detail=str(error))
    return HTTPException(status_code=409, detail=str(error))


def a_http_datos(error: TypeError) -> HTTPException:
    """
    Traduce a **422** el `TypeError` que lanza un DAO cuando el cuerpo libre de
    una firma —Legal o Riesgo— trae campos que no existen o le faltan los
    obligatorios. Sin esto el fallo saldría como un 500 opaco.
    """
    return HTTPException(
        status_code=422,
        detail=f"Los campos enviados no corresponden a la firma solicitada: {error}")
