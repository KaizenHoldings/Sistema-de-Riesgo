"""
Base común de los esquemas Pydantic v2 de KFG Risk Architect.

Dos decisiones gobiernan todos los modelos de este paquete:

1. **Los importes son `Decimal`, nunca `float`.** Las columnas de la base son
   `FLOAT`, así que arrastran el error de coma flotante —un saldo llega como
   `5242.349999999999`—. Al tipar el campo como `Decimal` con dos decimales, el
   valor se cuantiza al entrar y deja de acumular ese error en la serialización.

2. **Todo campo numérico opcional es `| None`.** Las columnas vacías llegan como
   `NaN` desde el motor, y `json.dumps` emite el literal `NaN`, que un
   `JSON.parse` estricto rechaza. El validador de este módulo convierte `NaN` e
   `inf` en `None`, de modo que el JSON sale con `null`.
"""

from decimal import Decimal
from math import isfinite
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, PlainSerializer

CENTIMO = Decimal("0.01")


def _sin_nan(v: Any) -> Any:
    """Convierte `NaN` e infinitos en `None`; deja el resto intacto."""
    if isinstance(v, float) and not isfinite(v):
        return None
    # `NaN` de numpy/pandas llega como float; los `None` pasan de largo
    return v


def _a_decimal(v: Any) -> Any:
    """Normaliza un importe a `Decimal` con dos decimales."""
    v = _sin_nan(v)
    if v is None or isinstance(v, Decimal):
        return v.quantize(CENTIMO) if isinstance(v, Decimal) else v
    if isinstance(v, (int, float, str)):
        try:
            return Decimal(str(v)).quantize(CENTIMO)
        except Exception:
            return None
    return v


# Importe monetario: entra como float/str/Decimal y queda cuantizado a céntimos.
# Admite nulo porque una columna FLOAT vacía llega como NaN y debe resolverse a
# `null`, no reventar la validación. Se serializa como cadena para no volver a
# perder precisión al pasar por JSON.
Dinero = Annotated[
    Decimal | None,
    BeforeValidator(_a_decimal),
    PlainSerializer(lambda d: None if d is None else format(d, "f"),
                    return_type=str | None, when_used="json"),
]

# Magnitud numérica no monetaria (ratios, scores, porcentajes): admite nulo y
# nunca deja pasar un `NaN`.
Numero = Annotated[float | None, BeforeValidator(_sin_nan)]

# Entero opcional saneado
Entero = Annotated[int | None, BeforeValidator(_sin_nan)]

# Texto opcional saneado: los `NaN` de columnas de texto vacías pasan a None
Texto = Annotated[str | None, BeforeValidator(_sin_nan)]


class ModeloKFG(BaseModel):
    """
    Configuración compartida por todos los esquemas.

    `from_attributes` permite construirlos desde filas de SQLAlchemy además de
    desde diccionarios; `populate_by_name` deja usar los alias de columna.
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="ignore",
    )
