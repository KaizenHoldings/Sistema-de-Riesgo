"""Esquemas de `usuarios` y `config_parametros`."""

from pydantic import Field

from .base import ModeloKFG, Numero, Texto


class Usuario(ModeloKFG):
    """
    Cuenta de acceso. El hash bcrypt nunca debe salir en una respuesta: se
    declara aparte del modelo de lectura para no exponerlo por descuido.
    """

    usuario: str = Field(alias="user")
    rol: Texto = Field(default=None, alias="role")


class ConfigParametro(ModeloKFG):
    """Parámetro del motor de scoring (peso, tasa base o factor de riesgo)."""

    clave: str
    valor: Numero = 0
