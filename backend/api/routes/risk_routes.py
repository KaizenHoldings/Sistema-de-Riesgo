"""
Rutas del motor de riesgo.

Cada endpoint es una capa de traducción de unas pocas líneas sobre
`RiskScoreService`: valida el cuerpo, convierte los importes `Decimal` a `float`
y devuelve tal cual el diccionario que produce el servicio. **No hay una sola
fórmula ni un solo umbral reimplementados aquí**: si un resultado cambiara, sería
porque cambió el servicio, no la ruta.

Los motores son rutas sin estado: no abren sesión de base de datos ni consultan
nada. La única excepción son las rutas de `/evaluaciones`, al final del módulo,
que guardan y recuperan el formulario de Riesgo de cada expediente.
"""

from datetime import datetime
import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, require_role
from api.routes._errores import a_http
from api.schemas.risk_schemas import (AltmanIn, EvaluacionRiesgoAutoIn,
                                      EvaluacionRiesgoAutoOut, EvaluacionRiesgoCorpIn,
                                      EvaluacionRiesgoCorpOut, IndicadoresIn,
                                      ScoringAutomotrizIn, ScoringCorporativoIn, a_float)
from database.daos_sqlserver import EvaluacionRiesgoAutoDAO, EvaluacionRiesgoCorpDAO
from database.db_core_sqlserver import get_db
from services.risk_score_service import RiskScoreService
from services.workflow_service import ErrorFlujo, TransicionInvalida, WorkflowService

# La lectura queda abierta a cualquier usuario autenticado, con la dependencia
# del router; cada escritura añade su propia exigencia de rol.
router = APIRouter(prefix="/api/v1/risk", tags=["Riesgo"], dependencies=[Depends(get_current_user)])
solo_riesgo = require_role("Riesgo", "Superadmin")
# Guardar la hoja de trabajo es del analista de Riesgo; Superadmin conserva,
# como en el resto de la API, acceso de escritura global.
escritura_riesgo = require_role("Riesgo", "Superadmin")


@router.post("/scoring/corporativo", summary="Scoring corporativo")
def scoring_corporativo(datos: ScoringCorporativoIn, _usuario: dict = Depends(solo_riesgo)) -> dict:
    """
    Evalúa un expediente corporativo.

    Devuelve el DSCR, el margen EBITDA, los tres scores parciales, el score
    final con el boost de la Matriz Kaizen, la tasa sugerida, la batería de
    indicadores y el Altman Z-Score.
    """
    return RiskScoreService.evaluar_corporativo(
        activos_corrientes=a_float(datos.activos_corrientes),
        pasivos_corrientes=a_float(datos.pasivos_corrientes),
        ebitda=a_float(datos.ebitda),
        gastos_financieros=a_float(datos.gastos_financieros),
        pasivos_totales=a_float(datos.pasivos_totales),
        patrimonio=a_float(datos.patrimonio),
        ingresos_mensuales=a_float(datos.ingresos_mensuales),
        cuota_mensual=a_float(datos.cuota_mensual),
        aplicar_estres=datos.aplicar_estres,
        kc_score=datos.kc_score,
        w_liq=datos.pesos.w_liq,
        w_sol=datos.pesos.w_sol,
        w_cob=datos.pesos.w_cob,
        boost_max=datos.pesos.boost_max,
        tasa_base=datos.pesos.tasa_base,
        factor_riesgo=datos.pesos.factor_riesgo,
        costo_ventas=a_float(datos.costo_ventas),
        depreciacion_amortizacion=a_float(datos.depreciacion_amortizacion),
        impuestos_estimados=a_float(datos.impuestos_estimados),
        utilidad_neta=a_float(datos.utilidad_neta),
        activos_totales=a_float(datos.activos_totales),
        caja_equivalentes=a_float(datos.caja_equivalentes),
        cuentas_por_cobrar=a_float(datos.cuentas_por_cobrar),
        cuentas_por_pagar=a_float(datos.cuentas_por_pagar),
        inventarios=a_float(datos.inventarios),
        deuda_financiera_total=a_float(datos.deuda_financiera_total),
        utilidades_retenidas=a_float(datos.utilidades_retenidas),
        valor_patrimonio_mercado=a_float(datos.valor_patrimonio_mercado),
        monto_credito=a_float(datos.monto_credito),
        tasa_interes_anual=datos.tasa_interes_anual,
        plazo_meses=datos.plazo_meses,
        meses_gracia=datos.meses_gracia)


@router.post("/scoring/automotriz", summary="Scoring automotriz")
def scoring_automotriz(datos: ScoringAutomotrizIn, _usuario: dict = Depends(solo_riesgo)) -> dict:
    """
    Evalúa un expediente automotriz.

    Devuelve el ingreso libre, el DTI, el PTI con su tramo, los scores de
    capacidad y LTV, el score final y la tasa sugerida.
    """
    return RiskScoreService.evaluar_automotriz(
        ingreso_mensual=a_float(datos.ingreso_mensual),
        gastos_fijos=a_float(datos.gastos_fijos),
        cuota_mensual=a_float(datos.cuota_mensual),
        ltv_ratio=datos.ltv_ratio,
        estabilidad_laboral=datos.estabilidad_laboral,
        aplicar_estres=datos.aplicar_estres,
        kc_score=datos.kc_score,
        w_cap=datos.pesos.w_cap,
        w_ltv=datos.pesos.w_ltv,
        w_est=datos.pesos.w_est,
        boost_max=datos.pesos.boost_max,
        tasa_base=datos.pesos.tasa_base,
        factor_riesgo=datos.pesos.factor_riesgo)


@router.post("/indicadores", summary="Batería de indicadores financieros")
def indicadores(datos: IndicadoresIn, _usuario: dict = Depends(solo_riesgo)) -> dict:
    """
    Calcula los indicadores agrupados en Liquidez, Endeudamiento, Rentabilidad,
    Ciclo de Conversión de Efectivo y Análisis DuPont, cada uno con su fórmula
    y su semáforo institucional.
    """
    return RiskScoreService.calcular_indicadores(
        activos_corrientes=a_float(datos.activos_corrientes),
        pasivos_corrientes=a_float(datos.pasivos_corrientes),
        pasivos_totales=a_float(datos.pasivos_totales),
        patrimonio=a_float(datos.patrimonio),
        activos_totales=a_float(datos.activos_totales),
        caja_equivalentes=a_float(datos.caja_equivalentes),
        cuentas_por_cobrar=a_float(datos.cuentas_por_cobrar),
        inventarios=a_float(datos.inventarios),
        cuentas_por_pagar=a_float(datos.cuentas_por_pagar),
        deuda_financiera_total=a_float(datos.deuda_financiera_total),
        ebitda=a_float(datos.ebitda),
        depreciacion_amortizacion=a_float(datos.depreciacion_amortizacion),
        ingresos_ventas=a_float(datos.ingresos_ventas),
        costo_ventas=a_float(datos.costo_ventas),
        utilidad_neta=a_float(datos.utilidad_neta))


@router.post("/altman", summary="Altman Z-Score para empresas privadas")
def altman(datos: AltmanIn, _usuario: dict = Depends(solo_riesgo)) -> dict:
    """
    Calcula el Z-Score en su variante para empresas no cotizadas.

    Devuelve el valor, la zona —angustia, gris o segura—, las cinco componentes
    con su coeficiente y su aporte, y las siete magnitudes de partida.
    """
    return RiskScoreService.calcular_altman_z(
        activos_corrientes=a_float(datos.activos_corrientes),
        pasivos_corrientes=a_float(datos.pasivos_corrientes),
        activos_totales=a_float(datos.activos_totales),
        utilidades_retenidas=a_float(datos.utilidades_retenidas),
        ebitda=a_float(datos.ebitda),
        depreciacion_amortizacion=a_float(datos.depreciacion_amortizacion),
        patrimonio=a_float(datos.patrimonio),
        pasivos_totales=a_float(datos.pasivos_totales),
        ingresos_ventas=a_float(datos.ingresos_ventas),
        valor_patrimonio_mercado=a_float(datos.valor_patrimonio_mercado))


# ── Evaluaciones guardadas ────────────────────────────────────────────
def _exigir_abierto(exp_id: int, tipo: str, db: Session) -> None:
    """
    El expediente debe existir (404), no estar firmado por Riesgo y seguir sin
    dictamen (409 en los dos casos).

    Firmada la etapa, la hoja respalda unas cifras ya registradas en el
    expediente; con el Comité pronunciado, una decisión tomada. En ambos casos
    reescribirla dejaría una evaluación que no es la que se valoró.
    """
    registro = WorkflowService.obtener(exp_id, tipo, session=db)
    dictamen = str(registro.get('dictamen') or 'PENDIENTE')
    if dictamen != 'PENDIENTE':
        # Aprobado, denegado o frenado: el expediente ya no se edita, se
        # reevalúa, que abre uno nuevo.
        raise TransicionInvalida(
            f"El expediente está en {dictamen}: su evaluación de Riesgo no "
            "admite cambios. Solicite una reevaluación.")
    if registro.get('status_riesgo') == 1:
        raise TransicionInvalida(
            "La etapa de Riesgo ya está firmada: su evaluación no admite "
            "cambios. Devuelva el expediente a Crédito para rehacerla.")


def _ahora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _guardar(dao, tipo: str, exp_id: int, datos: dict, usuario: dict, db: Session) -> None:
    try:
        _exigir_abierto(exp_id, tipo, db)
        dao.upsert(exp_id, datos, usuario=usuario["user"], fecha=_ahora(), session=db)
    except ErrorFlujo as e:
        db.rollback()
        raise a_http(e) from e
    except Exception:
        db.rollback()
        raise
    db.commit()


@router.get("/evaluaciones/corporativo/{exp_id}", response_model=EvaluacionRiesgoCorpOut | None,
            summary="Evaluación de Riesgo corporativa guardada")
def obtener_evaluacion_corporativa(exp_id: int, db: Session = Depends(get_db)):
    """
    Formulario guardado del expediente, o `null` si aún no se guardó ninguno.

    Responde 404 si el expediente no existe: así se distingue un expediente sin
    evaluación de uno inexistente.
    """
    try:
        WorkflowService.obtener(exp_id, 'corp', session=db)
    except ErrorFlujo as e:
        raise a_http(e) from e
    fila = EvaluacionRiesgoCorpDAO.get_by_expediente(exp_id, session=db)
    if fila is None:
        return None
    try:
        fila['entradas_ihp'] = json.loads(fila.pop('entradas_ihp_json') or '{}')
    except ValueError:
        fila['entradas_ihp'] = {}
    return fila


@router.put("/evaluaciones/corporativo/{exp_id}", response_model=EvaluacionRiesgoCorpOut,
            summary="Guarda la evaluación de Riesgo corporativa")
def guardar_evaluacion_corporativa(exp_id: int, cuerpo: EvaluacionRiesgoCorpIn,
                                   usuario: dict = Depends(escritura_riesgo),
                                   db: Session = Depends(get_db)):
    """Inserta o reemplaza el formulario del expediente. No firma la etapa."""
    datos = cuerpo.model_dump(exclude={'pesos', 'entradas_ihp'})
    datos['entradas_ihp_json'] = json.dumps(cuerpo.entradas_ihp)
    _guardar(EvaluacionRiesgoCorpDAO, 'corp', exp_id, datos, usuario, db)
    return obtener_evaluacion_corporativa(exp_id, db)


@router.get("/evaluaciones/automotriz/{exp_id}", response_model=EvaluacionRiesgoAutoOut | None,
            summary="Evaluación de Riesgo automotriz guardada")
def obtener_evaluacion_automotriz(exp_id: int, db: Session = Depends(get_db)):
    """Formulario guardado del expediente, o `null` si aún no se guardó ninguno."""
    try:
        WorkflowService.obtener(exp_id, 'auto', session=db)
    except ErrorFlujo as e:
        raise a_http(e) from e
    return EvaluacionRiesgoAutoDAO.get_by_expediente(exp_id, session=db)


@router.put("/evaluaciones/automotriz/{exp_id}", response_model=EvaluacionRiesgoAutoOut,
            summary="Guarda la evaluación de Riesgo automotriz")
def guardar_evaluacion_automotriz(exp_id: int, cuerpo: EvaluacionRiesgoAutoIn,
                                  usuario: dict = Depends(escritura_riesgo),
                                  db: Session = Depends(get_db)):
    """Inserta o reemplaza el formulario del expediente. No firma la etapa."""
    datos = cuerpo.model_dump(exclude={'pesos'})
    _guardar(EvaluacionRiesgoAutoDAO, 'auto', exp_id, datos, usuario, db)
    return obtener_evaluacion_automotriz(exp_id, db)
