"""
Métricas agregadas del tablero.

Ocho conteos que responden a una sola pregunta —en qué estado está la cartera de
solicitudes— y que se resuelven con COUNT en el motor. Se sirven juntos porque
el tablero los pinta juntos: ocho peticiones para ocho números serían ocho
viajes para una sola pantalla.

La lectura queda abierta a cualquier usuario autenticado: son agregados, no
expedientes, y el tablero es la primera pantalla de todos los roles.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_current_user
from api.schemas.base import ModeloKFG
from database.daos_sqlserver import MetricasDashboardDAO
from database.db_core_sqlserver import get_db

router = APIRouter(prefix="/api/v1/dashboard", tags=["Tablero"],
                   dependencies=[Depends(get_current_user)])


class MetricasTablero(ModeloKFG):
    """Los ocho agregados del tablero."""

    clientes: int
    creditos_total: int
    creditos_corporativos: int
    creditos_automotrices: int
    listos_comite: int
    frenados_cumplimiento: int
    frenados_riesgo: int
    frenados_legal: int


@router.get("/metrics", response_model=MetricasTablero,
            summary="Métricas agregadas del tablero")
def metricas(db: Session = Depends(get_db)) -> dict:
    """
    Clientes, solicitudes por línea, las listas para Comité y las paradas por
    etapa.

    Las tres últimas se deducen del estado en que quedó cada expediente: el
    esquema no registra quién lo detuvo. `MetricasDashboardDAO` documenta la
    regla exacta de atribución.
    """
    return MetricasDashboardDAO.resumen(session=db)
