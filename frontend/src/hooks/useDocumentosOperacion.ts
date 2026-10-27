"use client";

/**
 * Documentos de la operación, por expediente.
 *
 * Son los papeles que sustentan una solicitud concreta —estados financieros,
 * avalúos, títulos de la garantía— y que Legal descarga para inspeccionarlos.
 * No se confunden con el repositorio KYC del cliente, que es una lista cerrada
 * de requisitos y vive en `useDocumentos`.
 */

import { useCallback } from "react";

import { useApiQuery, type EstadoConsulta } from "@/hooks/useApiQuery";
import { apiClient, type Descarga } from "@/utils/apiClient";
import type { TipoExpediente } from "@/types/api";

export interface DocumentoOperacion {
  id: number;
  expediente_id: number;
  tipo_expediente: string;
  file_name: string;
  carpeta: string;
  tamano_bytes: number;
  cargado_por: string;
  fecha_carga: string;
  /** Estado frente a SharePoint: el backend usa los mismos rotulos del KYC. */
  sp_sync_status: string;
  fecha_sync: string;
}

function raiz(tipo: TipoExpediente, expId: number): string {
  return `/api/v1/expedientes/${tipo}/${expId}/documentos`;
}

export function useDocumentosOperacion(
  tipo: TipoExpediente,
  expId: number,
  /** La pantalla de alta declara el hook antes de tener expediente. */
  habilitado = true,
): EstadoConsulta<DocumentoOperacion[]> {
  const obtener = useCallback(
    (signal: AbortSignal) =>
      apiClient.get<DocumentoOperacion[]>(raiz(tipo, expId), { signal }),
    [tipo, expId],
  );
  return useApiQuery(obtener, [tipo, expId], habilitado);
}

/**
 * Sube uno o varios archivos y devuelve la lista ya actualizada.
 *
 * Van todos en la misma petición: así la pantalla no queda a medio camino si
 * falla el tercero de cinco, y vuelve a pintarse con lo que el servidor confirma
 * que tiene guardado.
 */
export async function cargarDocumentosOperacion(
  tipo: TipoExpediente,
  expId: number,
  archivos: File[],
  /** Fracción enviada, de 0 a 1, para pintar el avance. */
  alProgreso?: (fraccion: number) => void,
): Promise<DocumentoOperacion[]> {
  const formulario = new FormData();
  for (const archivo of archivos) {
    formulario.append("archivos", archivo, archivo.name);
  }
  return apiClient.subirConProgreso<DocumentoOperacion[]>(
    raiz(tipo, expId),
    formulario,
    alProgreso,
  );
}

export function descargarDocumentoOperacion(
  tipo: TipoExpediente,
  expId: number,
  docId: number,
): Promise<Descarga> {
  return apiClient.descargar(`${raiz(tipo, expId)}/${docId}/descargar`);
}

/**
 * Sube el documento al SharePoint del cliente y devuelve su registro ya marcado.
 *
 * Uno a uno, como en el repositorio KYC: si falla la red con el tercero, los dos
 * primeros siguen contando como sincronizados porque de verdad lo están.
 */
export function sincronizarDocumentoOperacion(
  tipo: TipoExpediente,
  expId: number,
  docId: number,
): Promise<DocumentoOperacion> {
  return apiClient.post<DocumentoOperacion>(
    `${raiz(tipo, expId)}/${docId}/sincronizar`,
  );
}

/** Baja lógica: el archivo se conserva, pero deja de ofrecerse. */
export function retirarDocumentoOperacion(
  tipo: TipoExpediente,
  expId: number,
  docId: number,
): Promise<void> {
  return apiClient.delete<void>(`${raiz(tipo, expId)}/${docId}`);
}
