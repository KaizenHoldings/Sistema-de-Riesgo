"use client";

/**
 * Métricas del tablero.
 *
 * Una sola lectura para los ocho indicadores: el backend los agrega con COUNT y
 * los sirve juntos, de modo que la pantalla no encadena ocho peticiones ni deja
 * tarjetas cargando a distinto ritmo.
 */

import { useCallback } from "react";

import { useApiQuery, type EstadoConsulta } from "@/hooks/useApiQuery";
import { apiClient } from "@/utils/apiClient";
import type { MetricasTablero } from "@/types/api";

export function useMetricasTablero(): EstadoConsulta<MetricasTablero> {
  const obtener = useCallback(
    (signal: AbortSignal) =>
      apiClient.get<MetricasTablero>("/api/v1/dashboard/metrics", { signal }),
    [],
  );
  return useApiQuery(obtener, []);
}
