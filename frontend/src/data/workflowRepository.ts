/**
 * Repositorio del circuito de aprobación.
 *
 * Única pieza del frontend que conoce las rutas del backend para este dominio.
 * Habla en los nombres de campo que espera la API —los mismos de la versión
 * anterior— y devuelve las respuestas en crudo: interpretarlas es de la capa de
 * negocio, y presentarlas de la visual.
 *
 * No lanza errores propios ni los traduce: deja pasar el `ApiError` que produce
 * `apiClient`, que ya distingue 404, 409 y 422, para que el servicio decida qué
 * código de dominio le corresponde.
 */

import { apiClient } from "@/utils/apiClient";
import type {
  BICommitteeForm,
  EtapaDevolucion,
  EvaluacionGuardada,
  EvaluacionRiesgo,
  LegalForm,
  ResultadoScoring,
  ResultadoTransicion,
  RiskForm,
  TipoExpediente,
} from "@/business/workflows/types";
import type { ExpedienteCrudo } from "@/business/workflows/approvalWorkflow";
import type { TareaWorkflow } from "@/types/api";

function raiz(tipo: TipoExpediente, expId: number): string {
  return `/api/v1/workflow/${tipo}/${expId}`;
}

function recurso(tipo: TipoExpediente): string {
  return tipo === "corp" ? "corporativos" : "automotrices";
}

function motor(tipo: TipoExpediente): string {
  return tipo === "corp" ? "corporativo" : "automotriz";
}

/** Contrato que la capa de negocio consume. Permite sustituir la fuente. */
export interface WorkflowRepository {
  obtenerExpediente(
    tipo: TipoExpediente,
    expId: number,
    signal?: AbortSignal,
  ): Promise<ExpedienteCrudo>;
  obtenerTareas(
    tipo: TipoExpediente,
    expId: number,
    signal?: AbortSignal,
  ): Promise<TareaWorkflow[]>;
  certificarCumplimiento(
    tipo: TipoExpediente,
    expId: number,
    usuario: string,
    datos: Record<string, unknown>,
  ): Promise<ResultadoTransicion>;
  observarCumplimiento(
    tipo: TipoExpediente,
    expId: number,
    usuario: string,
    observaciones: string,
  ): Promise<ResultadoTransicion>;
  rechazarCumplimiento(
    tipo: TipoExpediente,
    expId: number,
    usuario: string,
    observaciones: string,
  ): Promise<ResultadoTransicion>;
  registrarLegal(
    tipo: TipoExpediente,
    expId: number,
    datos: LegalForm,
  ): Promise<ResultadoTransicion>;
  registrarRiesgo(
    tipo: TipoExpediente,
    expId: number,
    datos: RiskForm,
  ): Promise<ResultadoTransicion>;
  emitirDictamen(
    tipo: TipoExpediente,
    expId: number,
    usuario: string,
    datos: BICommitteeForm,
  ): Promise<ResultadoTransicion>;
  devolver(
    tipo: TipoExpediente,
    expId: number,
    usuario: string,
    etapaDestino: EtapaDevolucion,
    observaciones: string,
  ): Promise<ResultadoTransicion>;
  rechazar(
    tipo: TipoExpediente,
    expId: number,
    usuario: string,
    observaciones: string,
  ): Promise<ResultadoTransicion>;
  calcularScoring(
    tipo: TipoExpediente,
    entradas: Record<string, unknown>,
  ): Promise<ResultadoScoring>;
  /** Hoja de trabajo guardada, o `null` si el expediente aún no tiene. */
  obtenerEvaluacionRiesgo<T extends EvaluacionRiesgo>(
    tipo: TipoExpediente,
    expId: number,
    signal?: AbortSignal,
  ): Promise<EvaluacionGuardada<T> | null>;
  guardarEvaluacionRiesgo<T extends EvaluacionRiesgo>(
    tipo: TipoExpediente,
    expId: number,
    datos: T,
  ): Promise<EvaluacionGuardada<T>>;
}

export const workflowRepository: WorkflowRepository = {
  obtenerExpediente: (tipo, expId, signal) =>
    apiClient.get<ExpedienteCrudo>(
      `/api/v1/expedientes/${recurso(tipo)}/${expId}`,
      { signal },
    ),

  obtenerTareas: (tipo, expId, signal) =>
    apiClient.get<TareaWorkflow[]>(`${raiz(tipo, expId)}/tareas`, { signal }),

  certificarCumplimiento: (tipo, expId, usuario, datos) =>
    apiClient.post<ResultadoTransicion>(
      `${raiz(tipo, expId)}/cumplimiento/certificar`,
      { usuario, datos },
    ),

  observarCumplimiento: (tipo, expId, usuario, observaciones) =>
    apiClient.post<ResultadoTransicion>(
      `${raiz(tipo, expId)}/cumplimiento/observar`,
      { usuario, observaciones },
    ),

  rechazarCumplimiento: (tipo, expId, usuario, observaciones) =>
    apiClient.post<ResultadoTransicion>(
      `${raiz(tipo, expId)}/cumplimiento/rechazar`,
      { usuario, observaciones },
    ),

  registrarLegal: (tipo, expId, datos) =>
    apiClient.post<ResultadoTransicion>(`${raiz(tipo, expId)}/legal`, datos),

  registrarRiesgo: (tipo, expId, datos) =>
    apiClient.post<ResultadoTransicion>(`${raiz(tipo, expId)}/riesgo`, datos),

  emitirDictamen: (tipo, expId, usuario, datos) =>
    apiClient.post<ResultadoTransicion>(`${raiz(tipo, expId)}/dictamen`, {
      usuario,
      dictamen: datos.dictamen,
      tasa: datos.tasa,
      plazo: datos.plazo,
    }),

  devolver: (tipo, expId, usuario, etapaDestino, observaciones) =>
    apiClient.post<ResultadoTransicion>(`${raiz(tipo, expId)}/devolver`, {
      usuario,
      etapa_destino: etapaDestino,
      observaciones,
    }),

  rechazar: (tipo, expId, usuario, observaciones) =>
    apiClient.post<ResultadoTransicion>(`${raiz(tipo, expId)}/rechazar`, {
      usuario,
      observaciones,
    }),

  calcularScoring: (tipo, entradas) =>
    apiClient.post<ResultadoScoring>(
      `/api/v1/risk/scoring/${motor(tipo)}`,
      entradas,
    ),

  obtenerEvaluacionRiesgo: <T extends EvaluacionRiesgo>(
    tipo: TipoExpediente,
    expId: number,
    signal?: AbortSignal,
  ) =>
    apiClient.get<EvaluacionGuardada<T> | null>(
      `/api/v1/risk/evaluaciones/${motor(tipo)}/${expId}`,
      { signal },
    ),

  guardarEvaluacionRiesgo: <T extends EvaluacionRiesgo>(
    tipo: TipoExpediente,
    expId: number,
    datos: T,
  ) =>
    apiClient.put<EvaluacionGuardada<T>>(
      `/api/v1/risk/evaluaciones/${motor(tipo)}/${expId}`,
      datos,
    ),
};
