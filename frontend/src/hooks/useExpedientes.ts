"use client";

/**
 * Lectura de expedientes de crédito.
 *
 * El backend expone las dos líneas de producto por separado —`/corporativos` y
 * `/automotrices`— porque viven en tablas con columnas distintas. El hook
 * conserva esa separación en lugar de mezclarlas en una lista difusa.
 */

import { useCallback } from "react";

import { useApiQuery, type EstadoConsulta } from "@/hooks/useApiQuery";
import { apiClient } from "@/utils/apiClient";
import type {
  ExpedienteAutomotriz,
  ExpedienteCorporativo,
  ResumenPorDictamen,
  TipoExpediente,
} from "@/types/api";

/**
 * Pestaña de la bandeja.
 *
 * El recorte lo decide el backend con el rol del token: «pendiente» es lo que
 * espera la firma de quien consulta —para Comercial, lo que le han devuelto—,
 * e «histórico» lo ya resuelto por su parte. «all» devuelve la cartera entera y
 * el backend solo se la concede a quien hace seguimiento y no firma.
 */
export type VistaExpedientes = "pending" | "history" | "all";

export interface FiltrosExpedientes {
  pagina: number;
  porPagina: number;
  vista?: VistaExpedientes;
  dictamen?: string;
  cliente?: string;
  firmasCompletas?: boolean;
}

function query(filtros: FiltrosExpedientes) {
  return {
    pagina: filtros.pagina,
    por_pagina: filtros.porPagina,
    view_mode: filtros.vista,
    dictamen: filtros.dictamen,
    cliente: filtros.cliente,
    firmas_completas: filtros.firmasCompletas,
  };
}

export function useExpedientesCorporativos(
  filtros: FiltrosExpedientes,
): EstadoConsulta<ExpedienteCorporativo[]> {
  const { pagina, porPagina, vista, dictamen, cliente, firmasCompletas } = filtros;

  const obtener = useCallback(
    (signal: AbortSignal) =>
      apiClient.get<ExpedienteCorporativo[]>("/api/v1/expedientes/corporativos", {
        signal,
        query: query({ pagina, porPagina, vista, dictamen, cliente, firmasCompletas }),
      }),
    [pagina, porPagina, vista, dictamen, cliente, firmasCompletas],
  );

  return useApiQuery(obtener, [
    pagina,
    porPagina,
    vista,
    dictamen,
    cliente,
    firmasCompletas,
  ]);
}

export function useExpedientesAutomotrices(
  filtros: FiltrosExpedientes,
): EstadoConsulta<ExpedienteAutomotriz[]> {
  const { pagina, porPagina, vista, dictamen, cliente, firmasCompletas } = filtros;

  const obtener = useCallback(
    (signal: AbortSignal) =>
      apiClient.get<ExpedienteAutomotriz[]>("/api/v1/expedientes/automotrices", {
        signal,
        query: query({ pagina, porPagina, vista, dictamen, cliente, firmasCompletas }),
      }),
    [pagina, porPagina, vista, dictamen, cliente, firmasCompletas],
  );

  return useApiQuery(obtener, [
    pagina,
    porPagina,
    vista,
    dictamen,
    cliente,
    firmasCompletas,
  ]);
}

/** Resumen agregado por dictamen de una de las dos líneas de producto. */
export function useResumenExpedientes(
  linea: "corporativos" | "automotrices",
): EstadoConsulta<ResumenPorDictamen> {
  const obtener = useCallback(
    (signal: AbortSignal) =>
      apiClient.get<ResumenPorDictamen>(`/api/v1/expedientes/${linea}/resumen`, {
        signal,
      }),
    [linea],
  );

  return useApiQuery(obtener, [linea]);
}

/** Ficha de un expediente corporativo. */
export function useExpedienteCorporativo(
  expId: number,
  habilitado = true,
): EstadoConsulta<ExpedienteCorporativo> {
  const obtener = useCallback(
    (signal: AbortSignal) =>
      apiClient.get<ExpedienteCorporativo>(
        `/api/v1/expedientes/corporativos/${expId}`,
        { signal },
      ),
    [expId],
  );
  return useApiQuery(obtener, [expId], habilitado);
}

/** Ficha de un expediente automotriz. */
export function useExpedienteAutomotriz(
  expId: number,
  habilitado = true,
): EstadoConsulta<ExpedienteAutomotriz> {
  const obtener = useCallback(
    (signal: AbortSignal) =>
      apiClient.get<ExpedienteAutomotriz>(
        `/api/v1/expedientes/automotrices/${expId}`,
        { signal },
      ),
    [expId],
  );
  return useApiQuery(obtener, [expId], habilitado);
}

/** Expediente nuevo abierto por una reevaluación. */
export interface Reevaluacion {
  expediente_id: number;
  tipo: TipoExpediente;
  parent_expediente_id: number;
}

/**
 * Reabre una solicitud rechazada o devuelta en un expediente nuevo.
 *
 * El original no se modifica: queda como histórico y el nuevo lo referencia.
 * El backend responde 409 si el expediente no está en un estado reevaluable y
 * 403 si el rol no es Comercial.
 */
export async function solicitarReevaluacion(
  tipo: TipoExpediente,
  expId: number,
): Promise<Reevaluacion> {
  const recurso = tipo === "corp" ? "corporativos" : "automotrices";
  return apiClient.post<Reevaluacion>(
    `/api/v1/expedientes/${recurso}/${expId}/reevaluar`,
  );
}
