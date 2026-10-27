"use client";

/**
 * Sonda de vida del backend (`/health`).
 *
 * Sirve para que la barra lateral distinga un backend caído de una consulta sin
 * resultados, que es la confusión más habitual al levantar el entorno.
 */

import { useCallback } from "react";

import { useApiQuery, type EstadoConsulta } from "@/hooks/useApiQuery";
import { apiClient } from "@/utils/apiClient";

export interface Salud {
  estado: string;
  version: string;
}

export function useSalud(): EstadoConsulta<Salud> {
  const obtener = useCallback(
    (signal: AbortSignal) => apiClient.get<Salud>("/health", { signal }),
    [],
  );

  return useApiQuery(obtener, []);
}
