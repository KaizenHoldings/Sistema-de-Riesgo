"use client";

/**
 * Formulario del Comité BI.
 *
 * Decisión final del circuito. Aprobar exige las tres firmas —el backend lo
 * comprueba y responde 409 si falta alguna—, y al aprobar se genera el plan de
 * amortización con la tasa y el plazo que aquí se fijan, igual que en la versión
 * anterior. Rechazar solo requiere que Cumplimiento haya certificado, porque un
 * expediente puede desestimarse en cualquier punto posterior.
 *
 * Si el expediente está cerrado o finalizado, opera en modo solo lectura.
 */

import { useState } from "react";

import { DocumentosCreditoComite } from "@/components/sections/DocumentosCreditoComite";
import {
  Bloque,
  CampoNumero,
  CampoSeleccion,
  CampoTextoLargo,
  aNumero,
} from "@/components/sections/campos";
import { BOTON } from "@/components/ui/Modal";
import { Girador } from "@/components/ui/Skeleton";
import {
  ETAPAS_DEVOLUCION,
  type BICommitteeForm,
  type EtapaDevolucion,
  type FirmasFlujo,
  type ServiceResult,
} from "@/business/workflows/types";
import type { TipoExpediente } from "@/types/api";

export function FormularioComiteBI({
  tipo,
  expId,
  clienteId,
  nombreCliente,
  firmas,
  tasaSugerida,
  plazoSugerido,
  enviando,
  bloqueado = false,
  dictamen = "PENDIENTE",
  tasaAprobada,
  plazoAprobado,
  onDictamen,
  onDevolver,
  onRechazar,
}: {
  tipo?: TipoExpediente;
  expId?: number;
  clienteId?: number | null;
  nombreCliente?: string;
  firmas: FirmasFlujo;
  tasaSugerida: number;
  plazoSugerido: number;
  enviando: boolean;
  bloqueado?: boolean;
  dictamen?: string;
  tasaAprobada?: number;
  plazoAprobado?: number;
  onDictamen: (form: BICommitteeForm) => Promise<ServiceResult<unknown>>;
  onDevolver: (
    etapa: EtapaDevolucion,
    observaciones: string,
  ) => Promise<ServiceResult<unknown>>;
  onRechazar: (motivo: string) => Promise<ServiceResult<unknown>>;
}) {
  const [tasa, setTasa] = useState(
    tasaAprobada !== undefined && tasaAprobada !== null
      ? Number(tasaAprobada).toFixed(2)
      : tasaSugerida.toFixed(2),
  );
  const [plazo, setPlazo] = useState(
    String(plazoAprobado || plazoSugerido || 36),
  );
  const [etapa, setEtapa] = useState<EtapaDevolucion>(ETAPAS_DEVOLUCION[0]);
  const [justificacion, setJustificacion] = useState("");

  const faltan = [
    !firmas.cumplimiento && "Cumplimiento",
    !firmas.legal && "Legal",
    !firmas.riesgo && "Riesgo",
  ].filter(Boolean) as string[];

  const sinJustificacion = justificacion.trim().length === 0;

  return (
    <form
      className="rounded-xl border border-borde bg-white p-5 shadow-sm"
      onSubmit={(evento) => {
        evento.preventDefault();
        if (!bloqueado) {
          void onDictamen({
            dictamen: "APROBADO",
            tasa: aNumero(tasa),
            plazo: aNumero(plazo),
          });
        }
      }}
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-kaizen-900">Comité BI</h3>
          <p className="mt-1 text-xs text-tinta-suave">
            Dictamen final del circuito.
          </p>
        </div>
        {bloqueado && (
          <span className="rounded-full bg-verde-fondo px-3 py-1 text-xs font-semibold text-verde-trazo">
            Dictamen: {dictamen}
          </span>
        )}
      </div>

      {bloqueado ? (
        <div className="mt-4 rounded-lg border border-verde-trazo/30 bg-verde-fondo p-3 text-xs text-verde-trazo">
          ✓ Dictamen final emitido ({dictamen}). El formulario se muestra en modo solo lectura.
        </div>
      ) : (
        faltan.length > 0 && (
          <p className="mt-4 rounded-lg bg-ambar-fondo px-4 py-3 text-sm text-ambar-trazo">
            Faltan las firmas de {faltan.join(", ")}. La aprobación será rechazada
            por el servicio mientras el circuito no esté completo.
          </p>
        )
      )}

      {tipo && expId && (
        <div className="mt-5">
          <DocumentosCreditoComite
            tipo={tipo}
            expId={expId}
            clienteId={clienteId}
            nombreCliente={nombreCliente}
          />
        </div>
      )}

      <Bloque titulo="Condiciones aprobadas">
        <CampoNumero
          rotulo="Tasa aprobada (%)"
          valor={tasa}
          alCambiar={setTasa}
          minimo={0}
          deshabilitado={bloqueado}
          ayuda={`Riesgo propuso ${tasaSugerida.toFixed(2)}%.`}
        />
        <CampoNumero
          rotulo="Plazo (meses)"
          valor={plazo}
          alCambiar={setPlazo}
          paso="1"
          minimo={1}
          deshabilitado={bloqueado}
          ayuda="Número de cuotas del plan francés."
        />
      </Bloque>

      {!bloqueado && (
        <>
          <div className="mt-6 flex flex-wrap gap-3 border-t border-borde pt-5">
            <button type="submit" className={BOTON.primario} disabled={enviando}>
              {enviando && <Girador />}
              Aprobar y generar el plan
            </button>
          </div>

          <div className="mt-6 border-t border-borde pt-5">
            <h4 className="text-sm font-semibold text-kaizen-900">
              Devolver o rechazar
            </h4>
            <p className="mt-1 text-xs text-tinta-suave">
              Devolver reabre la etapa indicada con una tarea nueva; rechazar cierra
              el expediente y anula las tareas abiertas. Ambas exigen justificación.
            </p>

            <div className="mt-3 grid gap-4 sm:grid-cols-2">
              <CampoSeleccion
                rotulo="Etapa destino"
                valor={etapa}
                opciones={ETAPAS_DEVOLUCION}
                alCambiar={(v) => setEtapa(v as EtapaDevolucion)}
              />
            </div>

            <div className="mt-4">
              <CampoTextoLargo
                rotulo="Justificación"
                valor={justificacion}
                alCambiar={setJustificacion}
                marcador="Qué debe revisarse en la etapa de destino, o motivo del rechazo."
                filas={3}
              />
            </div>

            <div className="mt-4 flex flex-wrap gap-3">
              <button
                type="button"
                className={BOTON.neutro}
                disabled={enviando || sinJustificacion}
                onClick={() => void onDevolver(etapa, justificacion)}
              >
                Devolver a {etapa}
              </button>
              <button
                type="button"
                className={BOTON.peligro}
                disabled={enviando || sinJustificacion}
                onClick={() => void onRechazar(justificacion)}
              >
                Rechazar solicitud
              </button>
            </div>
          </div>
        </>
      )}
    </form>
  );
}
