"use client";

/**
 * Lectura del padrón de clientes (`/api/v1/clientes`).
 *
 * La paginación y los filtros se resuelven en el motor de base de datos, así que
 * el hook se limita a trasladar los parámetros y a devolver la página pedida.
 */

import { useCallback } from "react";

import { useAccion, type EstadoAccion } from "@/hooks/useAccion";
import { useApiQuery, type EstadoConsulta } from "@/hooks/useApiQuery";
import { apiClient } from "@/utils/apiClient";
import type { Cliente, ExpedienteAutomotriz, ExpedienteCorporativo, TipoExpediente } from "@/types/api";

export type NuevoCliente = Omit<Cliente, "id" | "kyc_status" | "obs_kyc" | "kyc_aprobado_por" | "kyc_fecha">;

export interface NuevaSolicitud {
  tipo: TipoExpediente;
  cliente_id: number;
  cliente: string;
  documento: string;
  fecha: string;
  monto: number;
  descripcion: string;
}

export interface FiltrosClientes {
  pagina: number;
  porPagina: number;
  nombre?: string;
  tipo?: string;
  kycStatus?: string;
}

export function useClientes(filtros: FiltrosClientes): EstadoConsulta<Cliente[]> {
  const { pagina, porPagina, nombre, tipo, kycStatus } = filtros;

  const obtener = useCallback(
    (signal: AbortSignal) =>
      apiClient.get<Cliente[]>("/api/v1/clientes", {
        signal,
        query: {
          pagina,
          por_pagina: porPagina,
          nombre: nombre,
          tipo: tipo,
          kyc_status: kycStatus,
        },
      }),
    [pagina, porPagina, nombre, tipo, kycStatus],
  );

  return useApiQuery(obtener, [pagina, porPagina, nombre, tipo, kycStatus]);
}

/** Ficha de un cliente concreto. */
export function useCliente(cliId: number): EstadoConsulta<Cliente> {
  const obtener = useCallback(
    (signal: AbortSignal) =>
      apiClient.get<Cliente>(`/api/v1/clientes/${cliId}`, { signal }),
    [cliId],
  );

  return useApiQuery(obtener, [cliId]);
}

export function crearCliente(datos: NuevoCliente): Promise<Cliente> {
  return apiClient.post<Cliente>("/api/v1/clientes", datos);
}

export function crearSolicitud(
  datos: NuevaSolicitud,
): Promise<ExpedienteCorporativo | ExpedienteAutomotriz> {
  const ruta = datos.tipo === "corp" ? "corporativos" : "automotrices";
  return apiClient.post(`/api/v1/expedientes/${ruta}`, {
    fecha: datos.fecha,
    cliente: datos.cliente,
    cliente_id: datos.cliente_id,
    monto: datos.monto,
    descripcion: datos.descripcion,
    ...(datos.tipo === "corp"
      ? { rif: datos.documento }
      : { cedula: datos.documento }),
  });
}

/** Mutación reutilizable para el alta de clientes. */
export function useCrearCliente(): EstadoAccion<[NuevoCliente], Cliente> {
  return useAccion(crearCliente);
}

/** Mutación reutilizable para originar cualquiera de las dos líneas. */
export function useCrearSolicitud(): EstadoAccion<
  [NuevaSolicitud],
  ExpedienteCorporativo | ExpedienteAutomotriz
> {
  return useAccion(crearSolicitud);
}
