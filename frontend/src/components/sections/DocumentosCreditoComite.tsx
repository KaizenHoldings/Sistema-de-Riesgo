"use client";

/**
 * Visualizador de toda la documentación asociada al crédito para el Comité BI.
 *
 * Permite a los miembros del comité consultar y descargar todos los recaudos
 * antes de emitir su dictamen de aprobación, devolución o rechazo:
 * 1. Documentos de la Operación (contratos firmados, avalúos, facturas, etc.).
 * 2. Documentos del Checklist KYC del solicitante.
 * 3. Descarga directa del Contrato para Firma y del Acta de Crédito en PDF.
 */

import Link from "next/link";
import { useState } from "react";

import { Alerta } from "@/components/ui/Alerta";
import {
  IconoAlerta,
  IconoCheck,
  IconoDescargar,
  IconoDocumento,
} from "@/components/ui/Iconos";
import { BOTON } from "@/components/ui/Modal";
import { Girador, SkeletonTabla } from "@/components/ui/Skeleton";
import { useAvisos } from "@/components/ui/Toast";
import {
  descargarActa,
  descargarContrato,
  descargarDocumento,
  useChecklist,
  type ItemChecklist,
} from "@/hooks/useDocumentos";
import {
  descargarDocumentoOperacion,
  useDocumentosOperacion,
  type DocumentoOperacion,
} from "@/hooks/useDocumentosOperacion";
import type { TipoExpediente } from "@/types/api";
import { ApiError } from "@/utils/apiClient";
import { guardarComo } from "@/utils/descargas";
import { formatearFecha } from "@/utils/format";

type SubPestana = "operacion" | "kyc";

function tamanoLegible(bytes: number): string {
  if (!bytes || bytes <= 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function tonoSincronia(estado: string): string {
  if (estado === "Sincronizado") return "bg-verde-fondo text-verde-trazo border-verde-trazo/30";
  if (estado === "Desactualizado") return "bg-ambar-fondo text-ambar-trazo border-ambar-trazo/30";
  return "bg-neutro-fondo text-neutro-trazo border-borde";
}

export function DocumentosCreditoComite({
  tipo,
  expId,
  clienteId,
  nombreCliente,
}: {
  tipo: TipoExpediente;
  expId: number;
  clienteId?: number | null;
  nombreCliente?: string;
}) {
  const { notificar, notificarError } = useAvisos();
  const [subPestana, setSubPestana] = useState<SubPestana>("operacion");

  // Documentos de la operación (avaluos, facturas, contratos firmados por el cliente)
  const opConsulta = useDocumentosOperacion(tipo, expId);
  const docsOperacion = opConsulta.datos ?? [];

  // Documentos del cliente (Checklist KYC)
  const tieneCliente = typeof clienteId === "number" && clienteId > 0;
  const kycConsulta = useChecklist(clienteId ?? 0, tieneCliente);
  const checklist = kycConsulta.datos;

  // Estados de descarga activa
  const [descargandoOpId, setDescargandoOpId] = useState<number | null>(null);
  const [descargandoKycDoc, setDescargandoKycDoc] = useState<string | null>(null);
  const [descargandoContrato, setDescargandoContrato] = useState(false);
  const [descargandoActa, setDescargandoActa] = useState(false);

  // Manejador descarga operación
  const manejarDescargaOp = async (doc: DocumentoOperacion) => {
    setDescargandoOpId(doc.id);
    try {
      const descarga = await descargarDocumentoOperacion(tipo, expId, doc.id);
      guardarComo({ ...descarga, nombre: doc.file_name ?? descarga.nombre });
      notificar("exito", "Documento descargado", `"${doc.file_name}"`);
    } catch (error: unknown) {
      notificarError(
        error instanceof ApiError
          ? error
          : new ApiError(0, "No se pudo descargar el documento de la operación."),
      );
    } finally {
      setDescargandoOpId(null);
    }
  };

  // Manejador descarga KYC cliente
  const manejarDescargaKyc = async (item: ItemChecklist) => {
    if (!tieneCliente || item.documento_id === null) return;
    setDescargandoKycDoc(item.doc_name);
    try {
      const descarga = await descargarDocumento(clienteId!, item.documento_id);
      guardarComo({ ...descarga, nombre: item.file_name ?? descarga.nombre });
      notificar("exito", "Documento KYC descargado", `"${item.doc_name}"`);
    } catch (error: unknown) {
      notificarError(
        error instanceof ApiError
          ? error
          : new ApiError(0, "No se pudo descargar el documento KYC del cliente."),
      );
    } finally {
      setDescargandoKycDoc(null);
    }
  };

  // Manejador descarga Contrato
  const manejarDescargaContrato = async () => {
    setDescargandoContrato(true);
    try {
      const descarga = await descargarContrato(tipo, expId);
      guardarComo(descarga);
      notificar("exito", "Contrato generado", "Contrato de crédito listo para firma.");
    } catch (error: unknown) {
      notificarError(
        error instanceof ApiError
          ? error
          : new ApiError(0, "No se pudo generar el contrato de crédito."),
      );
    } finally {
      setDescargandoContrato(false);
    }
  };

  // Manejador descarga Acta
  const manejarDescargaActa = async () => {
    setDescargandoActa(true);
    try {
      const descarga = await descargarActa(tipo, expId);
      guardarComo(descarga);
      notificar("exito", "Acta generada", "Acta de comité lista para descarga.");
    } catch (error: unknown) {
      notificarError(
        error instanceof ApiError
          ? error
          : new ApiError(0, "No se pudo generar el acta de comité."),
      );
    } finally {
      setDescargandoActa(false);
    }
  };

  const totalKycConArchivo = checklist?.completados ?? 0;
  const totalKycRequisitos = checklist?.total ?? 0;

  return (
    <section className="rounded-xl border border-kaizen-200 bg-white p-5 shadow-sm">
      {/* Encabezado y Acciones Institucionales Rápidas */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-kaizen-100 pb-4">
        <div className="flex items-start gap-3">
          <div className="rounded-lg bg-kaizen-50 p-2.5 text-kaizen-600 ring-1 ring-kaizen-100">
            <IconoDocumento className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-kaizen-900">
              Documentos asociados al crédito
            </h3>
            <p className="mt-0.5 text-xs text-tinta-suave">
              Expediente de la operación, recaudos KYC y minutas contractuales
              {nombreCliente ? ` de ${nombreCliente}` : ""}.
            </p>
          </div>
        </div>

        {/* Acciones directas de descarga institucional */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => void manejarDescargaContrato()}
            disabled={descargandoContrato}
            className={`${BOTON.neutro} text-xs py-1.5 px-3 flex items-center gap-1.5`}
            title="Descargar la plantilla de contrato de crédito para firma en PDF"
          >
            {descargandoContrato ? (
              <Girador />
            ) : (
              <IconoDescargar className="h-3.5 w-3.5" />
            )}
            <span>Contrato para firma</span>
          </button>

          <button
            type="button"
            onClick={() => void manejarDescargaActa()}
            disabled={descargandoActa}
            className={`${BOTON.neutro} text-xs py-1.5 px-3 flex items-center gap-1.5`}
            title="Descargar el acta de resolución del comité en PDF"
          >
            {descargandoActa ? (
              <Girador />
            ) : (
              <IconoDescargar className="h-3.5 w-3.5" />
            )}
            <span>Acta de crédito</span>
          </button>
        </div>
      </div>

      {/* Selector de subpestañas */}
      <div className="mt-4 flex flex-wrap gap-2 border-b border-borde pb-2">
        <button
          type="button"
          onClick={() => setSubPestana("operacion")}
          className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
            subPestana === "operacion"
              ? "bg-kaizen-900 text-white shadow-xs"
              : "text-tinta-suave hover:bg-lienzo hover:text-tinta"
          }`}
        >
          Documentos de la Operación ({docsOperacion.length})
        </button>

        <button
          type="button"
          onClick={() => setSubPestana("kyc")}
          className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
            subPestana === "kyc"
              ? "bg-kaizen-900 text-white shadow-xs"
              : "text-tinta-suave hover:bg-lienzo hover:text-tinta"
          }`}
        >
          Recaudos KYC del Solicitante{" "}
          {tieneCliente && totalKycRequisitos > 0
            ? `(${totalKycConArchivo}/${totalKycRequisitos})`
            : ""}
        </button>
      </div>

      {/* Contenido según la subpestaña seleccionada */}
      <div className="mt-4">
        {subPestana === "operacion" && (
          <div>
            <div className="mb-3 flex items-center justify-between text-xs text-tinta-suave">
              <span>
                Archivos aportados por Comercial y Legal para respaldar esta
                solicitud (garantías, avalúos, facturas, contratos firmados).
              </span>
              <button
                type="button"
                onClick={() => opConsulta.recargar()}
                className="font-medium text-kaizen-600 hover:text-kaizen-900"
              >
                Actualizar lista
              </button>
            </div>

            {opConsulta.cargando && docsOperacion.length === 0 ? (
              <SkeletonTabla columnas={3} filas={3} />
            ) : opConsulta.error ? (
              <Alerta
                error={opConsulta.error}
                alReintentar={opConsulta.recargar}
              />
            ) : docsOperacion.length === 0 ? (
              <div className="rounded-lg border border-dashed border-borde bg-lienzo p-5 text-center">
                <p className="text-sm font-medium text-tinta">
                  No hay documentos adjuntos en el expediente de la operación.
                </p>
                <p className="mt-1 text-xs text-tinta-suave">
                  Los recaudos de la garantía o contrato firmado no han sido
                  cargados aún por Comercial o Legal.
                </p>
              </div>
            ) : (
              <div className="grid gap-2.5 sm:grid-cols-2">
                {docsOperacion.map((doc) => {
                  const estaDescargando = descargandoOpId === doc.id;
                  return (
                    <div
                      key={doc.id}
                      className="flex flex-col justify-between rounded-lg border border-borde bg-white p-3.5 shadow-2xs transition hover:border-kaizen-300"
                    >
                      <div className="min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <p
                            className="truncate text-xs font-semibold text-tinta"
                            title={doc.file_name}
                          >
                            {doc.file_name}
                          </p>
                          <span
                            className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${tonoSincronia(
                              doc.sp_sync_status,
                            )}`}
                          >
                            {doc.sp_sync_status}
                          </span>
                        </div>
                        <p className="mt-1 text-[11px] text-tinta-suave">
                          {tamanoLegible(doc.tamano_bytes)} ·{" "}
                          {formatearFecha(doc.fecha_carga)}
                          {doc.cargado_por ? ` · Por: ${doc.cargado_por}` : ""}
                        </p>
                      </div>

                      <div className="mt-3 flex items-center justify-end border-t border-kaizen-50 pt-2.5">
                        <button
                          type="button"
                          onClick={() => void manejarDescargaOp(doc)}
                          disabled={estaDescargando}
                          className={`${BOTON.neutro} text-xs py-1 px-2.5 flex items-center gap-1`}
                        >
                          {estaDescargando ? (
                            <Girador />
                          ) : (
                            <IconoDescargar className="h-3 w-3" />
                          )}
                          <span>Descargar</span>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {subPestana === "kyc" && (
          <div>
            {!tieneCliente ? (
              <div className="rounded-lg border border-dashed border-borde bg-lienzo p-5 text-center">
                <p className="text-sm font-medium text-tinta">
                  Expediente sin cliente asociado en el padrón KYC.
                </p>
                <p className="mt-1 text-xs text-tinta-suave">
                  Esta solicitud no está enlazada con un cliente formal, por lo
                  que no cuenta con checklist KYC individual.
                </p>
              </div>
            ) : kycConsulta.cargando && !checklist ? (
              <SkeletonTabla columnas={3} filas={4} />
            ) : kycConsulta.error ? (
              <Alerta
                error={kycConsulta.error}
                alReintentar={kycConsulta.recargar}
              />
            ) : !checklist ? null : (
              <div>
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-medium text-tinta">
                      Avance KYC: {totalKycConArchivo} de {totalKycRequisitos}{" "}
                      recaudos con archivo
                    </span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                        checklist.kyc_status === "Aprobado"
                          ? "bg-verde-fondo text-verde-trazo"
                          : "bg-ambar-fondo text-ambar-trazo"
                      }`}
                    >
                      {checklist.kyc_status ?? "Pendiente"}
                    </span>
                  </div>

                  <Link
                    href={`/clients/${clienteId}`}
                    target="_blank"
                    className="text-xs font-semibold text-kaizen-600 hover:text-kaizen-900"
                  >
                    Ver perfil del cliente en padrón ↗
                  </Link>
                </div>

                <div className="space-y-1.5">
                  {checklist.items.map((item) => {
                    const cubierto = item.tiene_archivo;
                    const estaDescargando = descargandoKycDoc === item.doc_name;

                    return (
                      <div
                        key={item.doc_name}
                        className={`flex flex-wrap items-center justify-between gap-3 rounded-lg border px-3.5 py-2.5 transition ${
                          cubierto
                            ? "border-borde bg-white hover:border-kaizen-300"
                            : "border-ambar-trazo/20 bg-ambar-fondo/30"
                        }`}
                      >
                        <div className="flex min-w-0 flex-1 items-center gap-2.5">
                          <span
                            className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${
                              cubierto
                                ? "bg-verde-trazo text-white"
                                : "bg-ambar-trazo/20 text-ambar-trazo"
                            }`}
                          >
                            {cubierto ? (
                              <IconoCheck className="h-2.5 w-2.5" />
                            ) : (
                              <IconoAlerta className="h-2.5 w-2.5" />
                            )}
                          </span>
                          <div className="min-w-0">
                            <p className="truncate text-xs font-medium text-tinta">
                              {item.doc_name}
                            </p>
                            {item.file_name && (
                              <p className="truncate text-[11px] text-tinta-suave">
                                Archivo: {item.file_name}
                              </p>
                            )}
                          </div>
                        </div>

                        <div>
                          {cubierto && item.documento_id !== null ? (
                            <button
                              type="button"
                              onClick={() => void manejarDescargaKyc(item)}
                              disabled={estaDescargando}
                              className={`${BOTON.neutro} text-xs py-1 px-2.5 flex items-center gap-1`}
                            >
                              {estaDescargando ? (
                                <Girador />
                              ) : (
                                <IconoDescargar className="h-3 w-3" />
                              )}
                              <span>Descargar</span>
                            </button>
                          ) : (
                            <span className="text-[11px] font-medium text-ambar-trazo">
                              Pendiente
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
