"use client";

/**
 * Indicadores de cartera (`/api/v1/cobranza/indicadores/...`).
 *
 * Los agregados se calculan en el motor de base de datos con `GROUP BY` y
 * `DATEDIFF`; el frontend no recorre cuotas para totalizar nada.
 */

import { useCallback } from "react";

import { useApiQuery, type EstadoConsulta } from "@/hooks/useApiQuery";
import { apiClient } from "@/utils/apiClient";
import type { GestionCobranza, PagoRecibido, PlanPago, ResumenVencimientos, TramosAging } from "@/types/api";

export function useVencimientos(
  diasProximos = 30,
): EstadoConsulta<ResumenVencimientos> {
  const obtener = useCallback(
    (signal: AbortSignal) =>
      apiClient.get<ResumenVencimientos>("/api/v1/cobranza/indicadores/vencimientos", {
        signal,
        query: { dias_proximos: diasProximos },
      }),
    [diasProximos],
  );

  return useApiQuery(obtener, [diasProximos]);
}

export function useAging(): EstadoConsulta<TramosAging> {
  const obtener = useCallback(
    (signal: AbortSignal) =>
      apiClient.get<TramosAging>("/api/v1/cobranza/indicadores/aging", { signal }),
    [],
  );

  return useApiQuery(obtener, []);
}

/**
 * Cuota vencida tal y como la devuelve el motor.
 *
 * Trae los días de atraso ya calculados con `DATEDIFF`, pero no el id de la fila
 * ni el nombre del cliente: la consulta agrega sobre `plan_pagos` sin unir con
 * el expediente. Por eso el cobro se registra desde el plan consolidado, que sí
 * identifica cada cuota.
 */
export interface CuotaVencida {
  expediente_id: number;
  tipo_expediente: string;
  periodo: number | null;
  fecha_pago: string | null;
  cuota: number | null;
  dias_atraso: number;
}

export function useVencidos(): EstadoConsulta<CuotaVencida[]> {
  const obtener = useCallback(
    (signal: AbortSignal) =>
      apiClient.get<CuotaVencida[]>("/api/v1/cobranza/vencidos", { signal }),
    [],
  );
  return useApiQuery(obtener, []);
}

export interface FiltrosCuotas {
  pagina: number;
  porPagina: number;
  expedienteId?: number;
  tipo?: string;
  estado?: string;
}

export function useCuotas(filtros: FiltrosCuotas): EstadoConsulta<PlanPago[]> {
  const { pagina, porPagina, expedienteId, tipo, estado } = filtros;

  const obtener = useCallback(
    (signal: AbortSignal) =>
      apiClient.get<PlanPago[]>("/api/v1/cobranza/cuotas", {
        signal,
        query: {
          pagina,
          por_pagina: porPagina,
          expediente_id: expedienteId,
          tipo,
          estado,
        },
      }),
    [pagina, porPagina, expedienteId, tipo, estado],
  );

  return useApiQuery(obtener, [pagina, porPagina, expedienteId, tipo, estado]);
}

/**
 * Marca una cuota como cobrada. Devuelve el id porque el endpoint responde 204
 * y quien llama necesita distinguir el éxito del fallo.
 */
export async function marcarCuotaPagada(planId: number): Promise<number> {
  await apiClient.put<void>(`/api/v1/cobranza/cuotas/${planId}/pagada`);
  return planId;
}

export function useGestiones(): EstadoConsulta<GestionCobranza[]> {
  const obtener = useCallback(
    (signal: AbortSignal) =>
      apiClient.get<GestionCobranza[]>("/api/v1/cobranza/gestiones", {
        signal,
        query: { pagina: 1, por_pagina: 100 },
      }),
    [],
  );
  return useApiQuery(obtener, []);
}

export function registrarGestion(
  datos: Omit<GestionCobranza, "id">,
): Promise<GestionCobranza> {
  return apiClient.post("/api/v1/cobranza/gestiones", datos);
}

export function registrarPago(
  datos: Omit<PagoRecibido, "id">,
): Promise<PagoRecibido> {
  return apiClient.post("/api/v1/cobranza/pagos", datos);
}
