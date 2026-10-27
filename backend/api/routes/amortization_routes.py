"""
Rutas del plan de amortización francés.

`/calculate` es puramente matemática: no abre sesión ni escribe nada, así que
sirve para simular condiciones antes de aprobar. `/persist` calcula y guarda
dentro de una única transacción, inyectada con `Depends(get_db)`.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, require_role
from api.schemas.risk_schemas import (AmortizacionIn, AmortizacionPersistirIn,
                                      PlanAmortizacionOut, a_float)
from database.db_core_sqlserver import get_db
from services.risk_service import AmortizationService

router = APIRouter(prefix="/api/v1/amortization", tags=["Amortización"], dependencies=[Depends(get_current_user)])
puede_simular = require_role("Riesgo", "Comité", "Superadmin")
puede_persistir = require_role("Comité", "Superadmin")


def _resumir(plan: list[dict]) -> PlanAmortizacionOut:
    """Empaqueta la tabla con sus totales, sin recalcular ninguna cuota."""
    total_pagar = round(sum(c["cuota"] for c in plan), 2)
    total_interes = round(sum(c["interes"] for c in plan), 2)
    return PlanAmortizacionOut(
        n_cuotas=len(plan),
        cuota_mensual=plan[0]["cuota"] if plan else 0.0,
        total_a_pagar=total_pagar,
        total_intereses=total_interes,
        cuotas=plan)


@router.post("/calculate", response_model=PlanAmortizacionOut,
             summary="Calcula el plan sin guardarlo")
def calcular(datos: AmortizacionIn, _usuario: dict = Depends(puede_simular)) -> PlanAmortizacionOut:
    """
    Devuelve la tabla de amortización francesa para las condiciones dadas.

    Operación sin estado: no consulta ni escribe en la base.
    """
    plan = AmortizationService.calcular_plan(
        monto=a_float(datos.monto),
        tasa_anual=datos.tasa_anual,
        plazo_meses=datos.plazo_meses,
        fecha_inicio_str=datos.fecha_inicio)
    return _resumir(plan)


@router.post("/persist", response_model=PlanAmortizacionOut,
             summary="Calcula el plan y lo guarda en el expediente")
def calcular_y_persistir(datos: AmortizacionPersistirIn,
                         _usuario: dict = Depends(puede_persistir),
                         db: Session = Depends(get_db)) -> PlanAmortizacionOut:
    """
    Calcula el plan y lo escribe en `plan_pagos`, reemplazando el anterior.

    El borrado y la inserción comparten la sesión de la petición, de modo que un
    fallo a mitad no deja el expediente con medio plan.
    """
    plan = AmortizationService.calcular_plan(
        monto=a_float(datos.monto),
        tasa_anual=datos.tasa_anual,
        plazo_meses=datos.plazo_meses,
        fecha_inicio_str=datos.fecha_inicio)
    try:
        AmortizationService.persistir_plan(
            datos.expediente_id, datos.tipo_expediente, plan, session=db)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500,
                            detail=f"No se pudo guardar el plan: {e}") from e
    return _resumir(plan)
