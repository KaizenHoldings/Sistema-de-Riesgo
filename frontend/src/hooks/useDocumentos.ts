"use client";

/**
 * Checklist KYC y repositorio documental del cliente.
 *
 * El estado real de un requisito no es la casilla marcada sino la existencia del
 * archivo: el backend devuelve las dos cosas por separado —`marcado` y
 * `tiene_archivo`— y la interfaz distingue entre «cubierto» y «marcado a mano
 * sin adjuntar», igual que hacía la vista anterior.
 */

import { useCallback } from "react";

import { useApiQuery, type EstadoConsulta } from "@/hooks/useApiQuery";
import { apiClient, type Descarga } from "@/utils/apiClient";
import type { Cliente, DocumentoCliente } from "@/types/api";

export const SYNC_OK = "Sincronizado";
export const SYNC_PENDIENTE = "No Sincronizado";
export const SYNC_DESACTUALIZADO = "Desactualizado";

export interface ItemChecklist {
  doc_name: string;
  marcado: boolean;
  tiene_archivo: boolean;
  file_name: string | null;
  documento_id: number | null;
  sp_sync_status: string;
  aviso: string | null;
}

export interface Checklist {
  cliente_id: number;
  tipo: string | null;
  kyc_status: string | null;
  items: ItemChecklist[];
  completados: number;
  total: number;
}

export interface ResultadoCarga {
  archivo: string;
  carpeta: string;
  documento_id: number | null;
  sp_sync_status: string;
  kyc_status: string | null;
}

export function useChecklist(
  cliId: number,
  /**
   * Permite declarar el hook sin consultar. Lo necesita la revisión documental
   * del circuito, donde un expediente puede no estar ligado a ninguna ficha del
   * padrón y pedir el checklist del cliente 0 solo daría un 404.
   */
  habilitado = true,
): EstadoConsulta<Checklist> {
  const obtener = useCallback(
    (signal: AbortSignal) =>
      apiClient.get<Checklist>(`/api/v1/clientes/${cliId}/checklist`, { signal }),
    [cliId],
  );
  return useApiQuery(obtener, [cliId], habilitado);
}

export function useDocumentos(cliId: number): EstadoConsulta<DocumentoCliente[]> {
  const obtener = useCallback(
    (signal: AbortSignal) =>
      apiClient.get<DocumentoCliente[]>(`/api/v1/clientes/${cliId}/documentos`, {
        signal,
      }),
    [cliId],
  );
  return useApiQuery(obtener, [cliId]);
}

/** Sube el archivo de un requisito. Reemplaza el vigente si ya lo había. */
export function cargarDocumento(
  cliId: number,
  docName: string,
  archivo: File,
): Promise<ResultadoCarga> {
  const formulario = new FormData();
  formulario.append("doc_name", docName);
  formulario.append("archivo", archivo);
  return apiClient.postMultipart<ResultadoCarga>(
    `/api/v1/clientes/${cliId}/documentos`,
    formulario,
  );
}

export function descargarDocumento(
  cliId: number,
  docId: number,
): Promise<Descarga> {
  return apiClient.descargar(
    `/api/v1/clientes/${cliId}/documentos/${docId}/descargar`,
  );
}

export function sincronizarDocumento(
  cliId: number,
  docId: number,
): Promise<DocumentoCliente> {
  return apiClient.post<DocumentoCliente>(
    `/api/v1/clientes/${cliId}/documentos/${docId}/sincronizar`,
  );
}

export function actualizarMarcas(
  cliId: number,
  marcas: Record<string, boolean>,
): Promise<Checklist> {
  return apiClient.put<Checklist>(`/api/v1/clientes/${cliId}/checklist`, {
    marcas,
  });
}

export function aprobarKyc(
  cliId: number,
  observaciones: string,
): Promise<Cliente> {
  return apiClient.post<Cliente>(`/api/v1/clientes/${cliId}/kyc/aprobar`, {
    observaciones,
  });
}

/** Acta de crédito del expediente, en PDF. */
export function descargarActa(
  tipo: "corp" | "auto",
  expId: number,
): Promise<Descarga> {
  return apiClient.descargar(
    `/api/v1/reportes/expedientes/${tipo}/${expId}/acta`,
  );
}

/** Contrato de crédito a nombre del cliente, en PDF para firma. */
export function descargarContrato(
  tipo: "corp" | "auto",
  expId: number,
): Promise<Descarga> {
  return apiClient.descargar(
    `/api/v1/reportes/expedientes/${tipo}/${expId}/contrato`,
  );
}

