"""Esquemas de `plan_pagos`, `gestiones_cobranza` y `pagos_recibidos`."""

from .base import Dinero, Entero, ModeloKFG, Texto


class PlanPago(ModeloKFG):
    """
    Cuota del plan de amortización francés.

    Cuota, capital, interés y saldo van como `Dinero`: son las magnitudes donde
    el error de coma flotante se acumulaba cuota a cuota.
    """

    id: Entero = None
    expediente_id: int
    tipo_expediente: str
    periodo: Entero = None
    fecha_pago: Texto = None
    cuota: Dinero = 0
    capital: Dinero = 0
    interes: Dinero = 0
    saldo: Dinero = 0
    estado: Texto = "PENDIENTE"


class GestionCobranza(ModeloKFG):
    """Registro de una gestión de cobro sobre un expediente."""

    id: Entero = None
    expediente_id: int
    tipo_expediente: str
    fecha: Texto = None
    tipo_gestion: Texto = "Llamada"
    responsable: Texto = None
    resultado: Texto = None
    proxima_accion: Texto = None
    fecha_proxima: Texto = None
    obs: Texto = None


class PagoRecibido(ModeloKFG):
    """Pago aplicado a un expediente."""

    id: Entero = None
    expediente_id: int
    tipo_expediente: str
    fecha_pago: Texto = None
    monto: Dinero = 0
    referencia: Texto = None
