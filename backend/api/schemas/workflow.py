"""Esquema de `tareas_workflow`."""

from .base import Entero, ModeloKFG, Texto


class TareaWorkflow(ModeloKFG):
    """
    Tarea abierta para una etapa del circuito.

    Cumplimiento genera de golpe las de 'Crédito' y 'Legal Fase 1' al certificar.
    """

    id: Entero = None
    expediente_id: int
    tipo_expediente: str
    etapa: str
    estado: str = "PENDIENTE"
    origen: Texto = None
    observaciones: Texto = None
    creado_por: Texto = None
    fecha_creacion: Texto = None
    fecha_cierre: Texto = None
