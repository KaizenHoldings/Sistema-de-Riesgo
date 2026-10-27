/**
 * Tipos que reflejan los esquemas Pydantic del backend (`api/schemas/`).
 *
 * Los importes viajan como cadena porque `Dinero` se serializa cuantizado a
 * céntimos: convertirlos a `number` en el borde perdería esa precisión, así que
 * se formatean con `formatearDinero` en el momento de pintarlos.
 */

export type Texto = string | null;
export type Numero = number | null;

/** Cliente del registro KYC. */
export interface Cliente {
  id: number | null;
  fecha_registro: Texto;
  tipo: Texto;
  nombre: Texto;
  cedula_rif: Texto;
  fecha_nacimiento: Texto;
  nacionalidad: Texto;
  telefono: Texto;
  email: Texto;
  direccion: Texto;
  actividad_economica: Texto;
  nombre_rep: Texto;
  cedula_rep: Texto;
  cargo_rep: Texto;
  docs_json: Texto;
  kyc_status: Texto;
  obs_kyc: Texto;
  kyc_aprobado_por: Texto;
  kyc_fecha: Texto;
}

/** Campos comunes a las dos líneas de producto. */
export interface ExpedienteBase {
  id: number | null;
  fecha: Texto;
  cliente: Texto;
  cliente_id: number | null;
  monto: string | null;
  moneda: Texto;
  descripcion: Texto;
  /** Expediente del que procede esta reevaluación, si la hay. */
  parent_expediente_id: number | null;
  status_comp: number | null;
  status_leg: number | null;
  status_riesgo: number | null;
  riesgo_aml: Texto;
  obs_comp: Texto;
  obs_leg: Texto;
  ltv_ratio: Numero;
  score_f: Numero;
  rm_score: Numero;
  obs_riesgo: Texto;
  dictamen: Texto;
  estado_workflow: Texto;
  tasa_sugerida: Numero;
  tasa_aprobada: Numero;
  aprobado_por: Texto;
  fecha_decision: Texto;
  /** Motivo escrito al devolver o rechazar el expediente. */
  obs_decision: Texto;
  /** Etapa a la que se devolvió, cuando el dictamen es una revisión. */
  devuelto_a: Texto;
  plazo_meses: number | null;
  cuota_est: string | null;
  estado_cobranza: Texto;
  eliminado: boolean;
}

export interface ExpedienteCorporativo extends ExpedienteBase {
  rif: Texto;
  v_garantia: string | null;
  dscr: Numero;
  margen_ebitda: Numero;
}

export interface ExpedienteAutomotriz extends ExpedienteBase {
  cedula: Texto;
  marca: Texto;
  modelo: Texto;
  anio: number | null;
  precio_vehiculo: string | null;
  dti_ratio: Numero;
}

/** Línea de producto tal y como la nombra el backend. */
export type TipoExpediente = "corp" | "auto";

/** Los ocho agregados del tablero. */
export interface MetricasTablero {
  clientes: number;
  creditos_total: number;
  creditos_corporativos: number;
  creditos_automotrices: number;
  listos_comite: number;
  frenados_cumplimiento: number;
  frenados_riesgo: number;
  frenados_legal: number;
}

/** Agregado `{dictamen: {n, monto}}` que devuelve el resumen de expedientes. */
export type ResumenPorDictamen = Record<string, { n: number; monto: number }>;

/** Cuotas vencidas y por vencer dentro de la ventana consultada. */
export interface ResumenVencimientos {
  n_vencidas: number;
  monto_vencido: number;
  n_proximas: number;
  monto_proximo: number;
}

/** Tramos de antigüedad de la deuda; el backend devuelve siempre los cuatro. */
export type TramosAging = Record<
  string,
  { n: number; monto: number; prom_dias: number }
>;

/** Estado del circuito de evaluación de un expediente. */
export interface EstadoWorkflow {
  estado_workflow: Texto;
  dictamen: Texto;
  status_comp: number | null;
}

/** Parámetro del motor de scoring (peso, tasa base o factor de riesgo). */
export interface ConfigParametro {
  clave: string;
  valor: number | null;
}

/** Cuenta de acceso. El hash de la contraseña nunca sale del backend. */
export interface UsuarioCuenta {
  usuario: string;
  rol: Texto;
}

/** Tarea abierta para una etapa del circuito. */
export interface TareaWorkflow {
  id: number | null;
  expediente_id: number;
  tipo_expediente: string;
  etapa: string;
  estado: string;
  origen: Texto;
  observaciones: Texto;
  creado_por: Texto;
  fecha_creacion: Texto;
  fecha_cierre: Texto;
}

/** Respuesta común de las transiciones del circuito. */
export interface ResultadoTransicion {
  expediente_id: number;
  tipo: string;
  estado_workflow?: string;
  tareas_abiertas?: number;
  dictamen?: string;
  devuelto_a?: string;
  etapa?: string;
}

/**
 * Cuota del plan de amortización francés.
 *
 * Cuota, capital, interés y saldo llegan como cadena por la misma razón que los
 * montos del expediente: van cuantizados a céntimos desde el backend.
 */
export interface PlanPago {
  id: number | null;
  expediente_id: number;
  tipo_expediente: string;
  periodo: number | null;
  fecha_pago: Texto;
  cuota: string | null;
  capital: string | null;
  interes: string | null;
  saldo: string | null;
  estado: Texto;
}

export interface GestionCobranza {
  id: number | null;
  expediente_id: number;
  tipo_expediente: TipoExpediente;
  fecha: Texto;
  tipo_gestion: Texto;
  responsable: Texto;
  resultado: Texto;
  proxima_accion: Texto;
  fecha_proxima: Texto;
  obs: Texto;
}

export interface PagoRecibido {
  id: number | null;
  expediente_id: number;
  tipo_expediente: TipoExpediente;
  fecha_pago: Texto;
  monto: number;
  referencia: Texto;
}

/** Archivo del repositorio documental de un cliente. */
export interface DocumentoCliente {
  id: number | null;
  cliente_id: number;
  doc_name: Texto;
  file_name: string;
  carpeta: Texto;
  fecha_carga: Texto;
  fecha_sync: Texto;
  sp_sync_status: string;
}
