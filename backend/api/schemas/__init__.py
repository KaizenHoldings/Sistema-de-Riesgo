"""
Esquemas Pydantic v2 de las diez tablas del modelo.

Se exponen aquí para poder importarlos como `from api.schemas import Cliente`.
"""

from .base import ModeloKFG, Dinero
from .cliente import Cliente, DocumentoCliente
from .expediente import ExpedienteCorporativo, ExpedienteAutomotriz
from .cobranza import PlanPago, GestionCobranza, PagoRecibido
from .workflow import TareaWorkflow
from .sistema import Usuario, ConfigParametro

__all__ = [
    "ModeloKFG", "Dinero",
    "Cliente", "DocumentoCliente",
    "ExpedienteCorporativo", "ExpedienteAutomotriz",
    "PlanPago", "GestionCobranza", "PagoRecibido",
    "TareaWorkflow",
    "Usuario", "ConfigParametro",
]
