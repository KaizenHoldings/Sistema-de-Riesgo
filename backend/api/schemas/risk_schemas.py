"""
Esquemas de petición y respuesta de los motores financieros.

Los importes entran como `Dinero` (`Decimal` cuantizado a céntimos) y se
convierten a `float` justo al invocar `RiskScoreService`, que trabaja en coma
flotante. Esa conversión es deliberada y ocurre **solo en la frontera**: el
motor recibe exactamente los mismos valores que le pasa hoy la interfaz, de modo
que el resultado no cambia ni un decimal.

Los pesos, umbrales y factores viajan como `float` porque son parámetros de
configuración del modelo, no dinero.
"""

from decimal import Decimal

from pydantic import Field

from .base import ModeloKFG


def a_float(valor):
    """Convierte un importe `Decimal` a `float` para entregarlo al motor."""
    if valor is None:
        return 0.0
    return float(valor) if isinstance(valor, Decimal) else float(valor)


class PesosCorporativos(ModeloKFG):
    """Parámetros del motor corporativo, tal como viven en `config_parametros`."""

    w_liq: float = 1.0
    w_sol: float = 1.0
    w_cob: float = 1.0
    boost_max: float = 20.0
    tasa_base: float = 12.0
    factor_riesgo: float = 2.0


class PesosAutomotrices(ModeloKFG):
    """Parámetros del motor automotriz."""

    w_cap: float = 1.0
    w_ltv: float = 1.0
    w_est: float = 1.0
    boost_max: float = 20.0
    tasa_base: float = 10.0
    factor_riesgo: float = 1.5


class BalanceCorporativo(ModeloKFG):
    """Magnitudes contables comunes al scoring, los indicadores y el Altman."""

    activos_corrientes: Decimal = Decimal("0")
    pasivos_corrientes: Decimal = Decimal("0")
    pasivos_totales: Decimal = Decimal("0")
    patrimonio: Decimal = Decimal("0")
    activos_totales: Decimal = Decimal("0")
    caja_equivalentes: Decimal = Decimal("0")
    cuentas_por_cobrar: Decimal = Decimal("0")
    cuentas_por_pagar: Decimal = Decimal("0")
    inventarios: Decimal = Decimal("0")
    deuda_financiera_total: Decimal = Decimal("0")
    utilidades_retenidas: Decimal = Decimal("0")
    valor_patrimonio_mercado: Decimal = Decimal("0")

    ebitda: Decimal = Decimal("0")
    gastos_financieros: Decimal = Decimal("0")
    depreciacion_amortizacion: Decimal = Decimal("0")
    costo_ventas: Decimal = Decimal("0")
    impuestos_estimados: Decimal = Decimal("0")
    utilidad_neta: Decimal = Decimal("0")


class ScoringCorporativoIn(BalanceCorporativo):
    """Cuerpo de `POST /api/v1/risk/scoring/corporativo`."""

    ingresos_mensuales: Decimal = Decimal("0")
    cuota_mensual: Decimal = Decimal("0")
    aplicar_estres: bool = False
    kc_score: float = Field(default=0.0, ge=0, le=10,
                            description="Matriz Kaizen Institucional, de 0 a 10")

    # Estructura del crédito (informativa)
    monto_credito: Decimal = Decimal("0")
    tasa_interes_anual: float = 0.0
    plazo_meses: int = 0
    meses_gracia: int = 0

    pesos: PesosCorporativos = PesosCorporativos()


class ScoringAutomotrizIn(ModeloKFG):
    """Cuerpo de `POST /api/v1/risk/scoring/automotriz`."""

    ingreso_mensual: Decimal = Decimal("0")
    gastos_fijos: Decimal = Decimal("0")
    cuota_mensual: Decimal = Decimal("0")
    ltv_ratio: float = 0.0
    estabilidad_laboral: float = Field(default=0.0, ge=0, le=10)
    aplicar_estres: bool = False
    kc_score: float = Field(default=0.0, ge=0, le=10)

    pesos: PesosAutomotrices = PesosAutomotrices()


class _FormularioRiesgo(ModeloKFG):
    """Campos del formulario de Riesgo que no alimentan al motor."""

    moneda: str = Field(default="USD", max_length=10)
    covenants: str = ""
    obs_riesgo: str = ""


class EvaluacionRiesgoCorpIn(_FormularioRiesgo, ScoringCorporativoIn):
    """
    Cuerpo de `PUT /api/v1/risk/evaluaciones/corporativo/{exp_id}`.

    Es el mismo cuerpo del scoring más lo que el analista escribe aparte y las
    partidas IHP de las que se derivaron las magnitudes. `pesos` se hereda pero
    no se guarda: los parámetros del modelo pertenecen a `config_parametros`.
    """

    entradas_ihp: dict[str, float] = Field(
        default_factory=dict, max_length=100,
        description="Partidas IHP tecleadas, por nombre de campo del formulario")


class EvaluacionRiesgoAutoIn(_FormularioRiesgo, ScoringAutomotrizIn):
    """Cuerpo de `PUT /api/v1/risk/evaluaciones/automotriz/{exp_id}`."""


class _Auditoria(ModeloKFG):
    expediente_id: int
    actualizado_por: str = ""
    fecha_actualizacion: str = ""


class EvaluacionRiesgoCorpOut(_Auditoria, EvaluacionRiesgoCorpIn):
    """Evaluación corporativa guardada."""

    # La respuesta no devuelve pesos que nunca se guardaron.
    pesos: None = Field(default=None, exclude=True)


class EvaluacionRiesgoAutoOut(_Auditoria, EvaluacionRiesgoAutoIn):
    """Evaluación automotriz guardada."""

    pesos: None = Field(default=None, exclude=True)


class IndicadoresIn(BalanceCorporativo):
    """Cuerpo de `POST /api/v1/risk/indicadores`."""

    ingresos_ventas: Decimal = Decimal("0")


class AltmanIn(BalanceCorporativo):
    """Cuerpo de `POST /api/v1/risk/altman`."""

    ingresos_ventas: Decimal = Decimal("0")


class AmortizacionIn(ModeloKFG):
    """Cuerpo de `POST /api/v1/amortization/calculate`."""

    monto: Decimal = Field(gt=0, description="Capital financiado")
    tasa_anual: float = Field(ge=0, description="Tasa nominal anual en porcentaje")
    plazo_meses: int = Field(gt=0, le=600)
    fecha_inicio: str | None = Field(
        default=None, description="Fecha base AAAA-MM-DD; hoy si se omite")


class AmortizacionPersistirIn(AmortizacionIn):
    """Cuerpo de `POST /api/v1/amortization/persist`: calcula y guarda."""

    expediente_id: int
    tipo_expediente: str = Field(pattern="^(corp|auto)$")


class CuotaOut(ModeloKFG):
    """Una cuota del plan de amortización."""

    periodo: int
    fecha_pago: str
    cuota: float
    capital: float
    interes: float
    saldo: float
    estado: str = "PENDIENTE"


class PlanAmortizacionOut(ModeloKFG):
    """Respuesta del cálculo: la tabla y sus totales."""

    n_cuotas: int
    cuota_mensual: float
    total_a_pagar: float
    total_intereses: float
    cuotas: list[CuotaOut]
