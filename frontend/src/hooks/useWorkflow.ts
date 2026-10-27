"use client";

/**
 * Transiciones del circuito de evaluación.
 *
 * Ninguna regla se decide aquí: las guardas viven en `services/workflow_service`
 * y el backend las devuelve como 404, 409 o 422, que `ApiError` ya distingue. El
 * frontend nunca deshabilita un botón dando por hecho el resultado de una
 * guarda; lo intenta y muestra el motivo exacto que responda el servicio.
 */

import { useCallback } from "react";

import { useApiQuery, type EstadoConsulta } from "@/hooks/useApiQuery";
import { apiClient } from "@/utils/apiClient";
import type {
  EstadoWorkflow,
  ResultadoTransicion,
  TareaWorkflow,
  TipoExpediente,
} from "@/types/api";

function raiz(tipo: TipoExpediente, expId: number): string {
  return `/api/v1/workflow/${tipo}/${expId}`;
}

export function useEstadoWorkflow(
  tipo: TipoExpediente,
  expId: number,
): EstadoConsulta<EstadoWorkflow> {
  const obtener = useCallback(
    (signal: AbortSignal) =>
      apiClient.get<EstadoWorkflow>(`${raiz(tipo, expId)}/estado`, { signal }),
    [tipo, expId],
  );
  return useApiQuery(obtener, [tipo, expId]);
}

export function useTareas(
  tipo: TipoExpediente,
  expId: number,
): EstadoConsulta<TareaWorkflow[]> {
  const obtener = useCallback(
    (signal: AbortSignal) =>
      apiClient.get<TareaWorkflow[]>(`${raiz(tipo, expId)}/tareas`, { signal }),
    [tipo, expId],
  );
  return useApiQuery(obtener, [tipo, expId]);
}

/** Cierra Cumplimiento y abre a la vez las evaluaciones de Crédito y Legal. */
export function certificarCumplimiento(
  tipo: TipoExpediente,
  expId: number,
  usuario: string,
): Promise<ResultadoTransicion> {
  return apiClient.post<ResultadoTransicion>(
    `${raiz(tipo, expId)}/cumplimiento/certificar`,
    { usuario },
  );
}

/** Devuelve el expediente al área comercial para subsanación. */
export function observarCumplimiento(
  tipo: TipoExpediente,
  expId: number,
  observaciones: string,
  usuario: string,
): Promise<ResultadoTransicion> {
  return apiClient.post<ResultadoTransicion>(
    `${raiz(tipo, expId)}/cumplimiento/observar`,
    { observaciones, usuario },
  );
}

/** Desestima el expediente en Cumplimiento y lo archiva. */
export function rechazarCumplimiento(
  tipo: TipoExpediente,
  expId: number,
  observaciones: string,
  usuario: string,
): Promise<ResultadoTransicion> {
  return apiClient.post<ResultadoTransicion>(
    `${raiz(tipo, expId)}/cumplimiento/rechazar`,
    { observaciones, usuario },
  );
}

/** Decisión del Comité. Aprobar exige las tres firmas del circuito. */
export function emitirDictamen(
  tipo: TipoExpediente,
  expId: number,
  dictamen: "APROBADO" | "RECHAZADO",
  usuario: string,
  tasa = 0,
  plazo: number | null = null,
): Promise<ResultadoTransicion> {
  return apiClient.post<ResultadoTransicion>(`${raiz(tipo, expId)}/dictamen`, {
    dictamen,
    usuario,
    tasa,
    plazo,
  });
}

/** Devuelve el expediente a una etapa previa, con justificación obligatoria. */
export function devolverExpediente(
  tipo: TipoExpediente,
  expId: number,
  etapaDestino: string,
  observaciones: string,
  usuario: string,
): Promise<ResultadoTransicion> {
  return apiClient.post<ResultadoTransicion>(`${raiz(tipo, expId)}/devolver`, {
    etapa_destino: etapaDestino,
    observaciones,
    usuario,
  });
}
