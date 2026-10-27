/**
 * Modelo de dominio del circuito de aprobación de créditos.
 *
 * Reproduce el flujo de la versión anterior de la plataforma: Cumplimiento es la
 * primera revisión formal y, al certificar, abre **a la vez** las evaluaciones de
 * Crédito (Riesgo) y Legal; con las tres firmas registradas el Comité
 * emite dictamen. En cualquier punto posterior a Cumplimiento el expediente
 * puede devolverse a una etapa previa o rechazarse.
 *
 * Los nombres de campo de los formularios son los mismos que espera la capa de
 * datos del backend, heredados de la versión anterior: renombrarlos aquí
 * obligaría a una traducción por cada envío y a mantener dos vocabularios.
 */

/** Contrato de respuesta común a todos los métodos de servicio. */
export type ServiceResult<T> =
  | { success: true; data: T }
  | { success: false; error: { code: string; message: string } };

/** Línea de producto. Determina qué formularios de Legal y Riesgo aplican. */
export type TipoExpediente = "corp" | "auto";

/** Etapas del circuito, en el orden en que se recorren. */
export type EtapaFlujo = "cumplimiento" | "credito_legal" | "comite" | "cerrado";

/** Situación de un paso del circuito de cara al visualizador. */
export type EstadoPaso = "completado" | "en_curso" | "pendiente" | "rechazado";

/** Acciones que el circuito admite según la etapa en la que esté. */
export type AccionFlujo =
  | "certificar_cumplimiento"
  | "observar_cumplimiento"
  | "rechazar_cumplimiento"
  | "registrar_legal"
  | "registrar_riesgo"
  | "emitir_dictamen"
  | "devolver"
  | "rechazar";

/** Etapas a las que el Comité puede devolver un expediente. */
export const ETAPAS_DEVOLUCION = [
  "Cumplimiento",
  "Legal",
  "Crédito",
] as const;

/**
 * Etapas a las que puede devolver Legal.
 *
 * Evalúa en paralelo con Riesgo, así que no reabre una etapa simultánea a la
 * suya: manda el expediente atrás, a quien lo presentó o a quien lo certificó.
 * El backend aplica la misma restricción.
 */
export const ETAPAS_DEVOLUCION_LEGAL = ["Comercial", "Cumplimiento"] as const;

export type EtapaDevolucion =
  | (typeof ETAPAS_DEVOLUCION)[number]
  | (typeof ETAPAS_DEVOLUCION_LEGAL)[number];

// ── Formularios ───────────────────────────────────────────────────────

/**
 * Cumplimiento: debida diligencia AML/CFT.
 *
 * Los datos de ocupación y empleador solo se piden en la línea automotriz,
 * donde el sujeto de crédito es una persona natural.
 */
export interface ComplianceForm {
  riesgo_aml: "Bajo" | "Medio" | "Alto";
  origen_fondos: string;
  check_pep: boolean;
  check_sanciones: boolean;
  obs: string;
  ocupacion?: string;
  empleador?: string;
  telefono?: string;
}

/** Legal, línea corporativa: garantías y cobertura. */
export interface LegalCorpForm {
  garantias_json: string;
  v_garantia: number;
  ltv_ratio: number;
  fecha_vencimiento_garantia: string;
  custodia_fisica: boolean;
  obs_leg: string;
}

/** Legal, línea automotriz: vehículo, seguro y prenda. */
export interface LegalAutoForm {
  marca: string;
  modelo: string;
  anio: number;
  vin: string;
  vehiculo_placa: string;
  tipo_vehiculo: "Nuevo" | "Usado";
  precio_vehiculo: number;
  enganche: number;
  plazo_meses: number;
  ltv_ratio: number;
  seguro_vehiculo: boolean;
  registro_lien: boolean;
  fecha_vencimiento_seguro: string;
  seguro_empresa: string;
  seguro_poliza: string;
  seguro_vigencia: string;
  obs_leg: string;
}

export type LegalForm = LegalCorpForm | LegalAutoForm;

/** Riesgo, línea corporativa: balance, cobertura y precio sugerido. */
export interface RiskCorpForm {
  score_f: number;
  rm_score: number;
  ac: number;
  pc: number;
  eb: number;
  gf: number;
  pt: number;
  pa: number;
  ing_mensuales: number;
  cuota_est: number;
  moneda: string;
  estres_aplicado: boolean;
  dscr: number;
  margen_ebitda: number;
  tasa_sugerida: number;
  covenants: string;
  obs_riesgo: string;
}

/** Riesgo, línea automotriz: capacidad de pago personal. */
export interface RiskAutoForm {
  score_f: number;
  rm_score: number;
  ingreso_mensual: number;
  gastos_mensuales: number;
  cuota_est: number;
  dti_ratio: number;
  estabilidad_laboral: number;
  estres_aplicado: boolean;
  tasa_sugerida: number;
  moneda: string;
  covenants: string;
  obs_riesgo: string;
}

export type RiskForm = RiskCorpForm | RiskAutoForm;

/**
 * Hoja de trabajo de Riesgo, corporativa, tal como se guarda en
 * `evaluaciones_riesgo_corp`.
 *
 * Son las magnitudes del scoring —derivadas de los estados IHP— más lo que el
 * analista escribe aparte y las propias partidas IHP, que son lo único desde lo
 * que puede reconstruirse el formulario.
 */
export interface EvaluacionRiesgoCorp {
  /** Las 16 magnitudes que produce `aEntradasScoring`. */
  [magnitud: string]: number | boolean | string | Record<string, number>;
  ingresos_mensuales: number;
  cuota_mensual: number;
  aplicar_estres: boolean;
  kc_score: number;
  moneda: string;
  covenants: string;
  obs_riesgo: string;
  entradas_ihp: Record<string, number>;
}

/** Hoja de trabajo de Riesgo, automotriz (`evaluaciones_riesgo_auto`). */
export interface EvaluacionRiesgoAuto {
  ingreso_mensual: number;
  gastos_fijos: number;
  cuota_mensual: number;
  ltv_ratio: number;
  estabilidad_laboral: number;
  aplicar_estres: boolean;
  kc_score: number;
  moneda: string;
  covenants: string;
  obs_riesgo: string;
}

export type EvaluacionRiesgo = EvaluacionRiesgoCorp | EvaluacionRiesgoAuto;

/**
 * Evaluación leída del backend.
 *
 * Los importes llegan como cadena —el backend los serializa como `Decimal` para
 * no perder céntimos—, así que todo campo numérico admite ambos tipos.
 */
export type EvaluacionGuardada<T> = {
  [K in keyof T]: T[K] extends number ? number | string : T[K];
} & {
  expediente_id: number;
  actualizado_por: string;
  fecha_actualizacion: string;
};

/** Comité BI: decisión final y condiciones de la operación. */
export interface BICommitteeForm {
  dictamen: "APROBADO" | "RECHAZADO";
  tasa: number;
  plazo: number;
}

/** Justificación escrita, obligatoria en observaciones, devoluciones y rechazos. */
export interface JustificacionForm {
  observaciones: string;
  etapa_destino?: EtapaDevolucion;
}

// ── Estado del circuito ───────────────────────────────────────────────

/** Un paso del circuito, ya resuelto para el visualizador. */
export interface PasoFlujo {
  clave: EtapaFlujo;
  titulo: string;
  descripcion: string;
  estado: EstadoPaso;
  firmadoPor?: string | null;
  fecha?: string | null;
}

/** Firmas registradas sobre el expediente. */
export interface FirmasFlujo {
  cumplimiento: boolean;
  legal: boolean;
  riesgo: boolean;
}

/** Tarea abierta por el circuito para una etapa. */
export interface TareaFlujo {
  id: number | null;
  etapa: string;
  estado: string;
  origen: string | null;
  observaciones: string | null;
  fecha_creacion: string | null;
}

/**
 * Estado completo del circuito para un expediente.
 *
 * `accionesPermitidas` es una guía para la interfaz, no una autorización: quien
 * decide si una transición es legítima es el servicio de flujo del backend, y
 * cualquiera de estas acciones puede ser rechazada al ejecutarse.
 */
export interface ApprovalWorkflow {
  expedienteId: number;
  tipo: TipoExpediente;
  cliente: string;
  /**
   * Cliente del padrón al que pertenece el expediente.
   *
   * Es nulo en los expedientes que se dieron de alta sin ligar a una ficha de
   * cliente, y sin él no hay checklist documental que consultar.
   */
  clienteId: number | null;
  monto: string | null;
  etapaActual: EtapaFlujo;
  estadoWorkflow: string;
  dictamen: string;
  firmas: FirmasFlujo;
  pasos: PasoFlujo[];
  accionesPermitidas: AccionFlujo[];
  tareas: TareaFlujo[];
  aprobadoPor: string | null;
  fechaDecision: string | null;
  tasaSugerida: number;
  plazoMeses: number | null;
  /** Datos completos del expediente para inicializar formularios o solo lectura. */
  expediente?: Record<string, unknown>;
}

/** Resultado de una transición, tal y como lo devuelve el backend. */
export interface ResultadoTransicion {
  expediente_id: number;
  tipo: string;
  estado_workflow?: string;
  tareas_abiertas?: number;
  dictamen?: string;
  devuelto_a?: string;
  etapa?: string;
}

/** Cálculo del motor de riesgo, previo al registro de la firma. */
export interface ResultadoScoring {
  score_final: number;
  tasa_sugerida: number;
  dscr?: number;
  margen_ebitda?: number;
  dti?: number;
  score_base?: number;
  ingreso_libre?: number;
  pti?: number;
  score_capacidad?: number;
  tramo_pti?: {
    nivel: string;
    color: string;
    label: string;
  };
  tramo_dti?: {
    nivel: string;
    delta: string;
    delta_color: string;
  };
  indicadores?: Record<string, IndicadorFinanciero[]>;
  altman?: AltmanZScore;
}

export interface IndicadorFinanciero {
  clave: string;
  nombre: string;
  categoria?: string;
  valor?: number;
  valor_fmt?: string;
  formula?: string;
  detalle?: string;
  /** «Referencial» o nulo cuando no hay umbral o no se pudo calcular. */
  semaforo?: "Verde" | "Amarillo" | "Rojo" | "Referencial" | null;
  emoji?: string;
}

export interface AltmanComponente {
  clave: string;
  etiqueta: string;
  formula: string;
  coeficiente: number;
  valor: number;
  valor_fmt: string;
  aporte: number;
  aporte_fmt: string;
}

export interface AltmanZScore {
  z: number;
  z_fmt: string;
  zona: string;
  semaforo: "Verde" | "Amarillo" | "Rojo" | null;
  emoji: string;
  formula: string;
  detalle: string;
  componentes: AltmanComponente[];
  variables_base: Record<string, number>;
}
