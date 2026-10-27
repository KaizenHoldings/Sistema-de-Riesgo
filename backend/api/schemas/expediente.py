"""
Esquemas de los dos tipos de expediente.

Los importes —monto, garantía, cuota, ingresos— van tipados como `Dinero`, que
es `Decimal` cuantizado a céntimos. Los ratios, scores y porcentajes van como
`Numero`, que admite nulo y filtra `NaN`.
"""

from .base import Dinero, Entero, ModeloKFG, Numero, Texto


class ExpedienteBase(ModeloKFG):
    """Campos comunes a las dos líneas de producto."""

    id: Entero = None
    fecha: Texto = None
    cliente: Texto = None
    cliente_id: Entero = None
    monto: Dinero = 0
    moneda: Texto = "USD"
    descripcion: Texto = None
    # Reevaluación: expediente del que se clonó este, o nulo si nació de una
    # solicitud nueva.
    parent_expediente_id: Entero = None

    # Firmas del circuito de evaluación
    status_comp: Entero = 0
    status_leg: Entero = 0
    status_riesgo: Entero = 0

    # Cumplimiento
    riesgo_aml: Texto = "Bajo"
    origen_fondos: Texto = None
    check_pep: Entero = 0
    check_sanciones: Entero = 0
    obs_comp: Texto = None

    # Legal y riesgo
    obs_leg: Texto = None
    ltv_ratio: Numero = 0
    status_riesgo_obs: Texto = None
    score_f: Numero = 0
    rm_score: Numero = 0
    obs_riesgo: Texto = None
    estres_aplicado: Entero = 0
    covenants: Texto = None

    # Decisión y precio
    dictamen: Texto = "PENDIENTE"
    estado_workflow: Texto = "EN EVALUACIÓN - CUMPLIMIENTO"
    tasa_sugerida: Numero = 0
    tasa_aprobada: Numero = 0
    aprobado_por: Texto = None
    fecha_decision: Texto = None
    obs_decision: Texto = None
    devuelto_a: Texto = None

    # Cartera
    plazo_meses: Entero = None
    cuota_est: Dinero = 0
    plan_generado: Entero = 0
    estado_cobranza: Texto = "Al día"
    tipo_producto: Texto = None
    eliminado: bool = False


class ExpedienteCorporativo(ExpedienteBase):
    """Expediente corporativo: balance, garantías y métricas de cobertura."""

    rif: Texto = None

    # Balance anualizado
    ac: Dinero = 0
    pc: Dinero = 0
    eb: Dinero = 0
    gf: Dinero = 0
    pt: Dinero = 0
    pa: Dinero = 0
    ing_mensuales: Dinero = 0
    ingresos_mensuales: Dinero = 0

    # Garantías
    garantias_json: Texto = "[]"
    v_garantia: Dinero = 0
    custodia_fisica: Entero = 0
    fecha_vencimiento_garantia: Texto = None

    # Métricas calculadas
    dscr: Numero = 0
    margen_ebitda: Numero = 0


class ExpedienteAutomotriz(ExpedienteBase):
    """Expediente automotriz: vehículo, seguro y capacidad de pago personal."""

    cedula: Texto = None
    ocupacion: Texto = None
    empleador: Texto = None
    telefono: Texto = None

    # Vehículo
    marca: Texto = None
    modelo: Texto = None
    anio: Entero = 0
    vin: Texto = None
    vehiculo_placa: Texto = None
    tipo_vehiculo: Texto = "Nuevo"
    precio_vehiculo: Dinero = 0
    enganche: Dinero = 0

    # Seguro y prenda
    seguro_vehiculo: Entero = 0
    registro_lien: Entero = 0
    fecha_vencimiento_seguro: Texto = None
    seguro_empresa: Texto = None
    seguro_poliza: Texto = None
    seguro_vigencia: Texto = None

    # Capacidad de pago
    ingreso_mensual: Dinero = 0
    gastos_mensuales: Dinero = 0
    dti_ratio: Numero = 0
    estabilidad_laboral: Numero = 0
