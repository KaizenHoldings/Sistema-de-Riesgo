"use client";

import { useState } from "react";
import type { CreditoPagado } from "@/hooks/useCobranzas";
import { descargarFiniquitoPdf } from "@/hooks/useCobranzas";
import { Modal } from "@/components/ui/Modal";
import { Girador } from "@/components/ui/Skeleton";
import { useAvisos } from "@/components/ui/Toast";
import { guardarComo } from "@/utils/descargas";
import { ApiError } from "@/utils/apiClient";
import { formatearDinero, formatearFecha } from "@/utils/format";
import {
  IconoDescargar,
  IconoCheck,
  IconoDocumento,
  IconoBalanza,
} from "@/components/ui/Iconos";

interface Props {
  abierto: boolean;
  alCerrar: () => void;
  credito: CreditoPagado | null;
  alVerHistorial?: (id: number, tipo: "corp" | "auto") => void;
}

export function ModalFiniquito({
  abierto,
  alCerrar,
  credito,
  alVerHistorial,
}: Props) {
  const { notificar, notificarError } = useAvisos();
  const [descargando, setDescargando] = useState(false);

  if (!credito) return null;

  const codSolvencia = `FIN-${credito.codigo_credito}-${new Date().getFullYear()}`;

  const manejarDescarga = async () => {
    setDescargando(true);
    try {
      const archivo = await descargarFiniquitoPdf(credito.id, credito.tipo);
      guardarComo(archivo);
      notificar(
        "exito",
        "Constancia de Solvencia Descargada",
        `Se descargó la constancia oficial de finiquito para ${credito.cliente}.`,
      );
    } catch (err: unknown) {
      notificarError(
        err instanceof ApiError
          ? err
          : new ApiError(0, "No se pudo descargar la constancia de finiquito."),
      );
    } finally {
      setDescargando(false);
    }
  };

  return (
    <Modal
      abierto={abierto}
      alCerrar={alCerrar}
      titulo="Certificado de Finiquito y Solvencia Legal"
      descripcion="Constancia oficial de extinción de obligaciones crediticias y saldo deudor en cero."
    >
      <div className="space-y-4 text-xs">
        {/* Cabecera del Certificado con sello de Solvencia */}
        <div className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-600 text-white shadow-xs">
                  <IconoCheck className="h-3.5 w-3.5" />
                </span>
                <span className="font-mono text-xs font-bold text-emerald-950 uppercase tracking-wide">
                  {codSolvencia}
                </span>
                <span className="rounded-full bg-emerald-600 px-2.5 py-0.5 text-[10px] font-bold text-white uppercase tracking-wider">
                  Crédito 100% Pagado
                </span>
              </div>
              <h3 className="text-base font-extrabold text-kaizen-900">
                {credito.cliente}
              </h3>
              <p className="text-tinta-suave text-[11px]">
                Doc / RIF: <span className="font-mono font-medium text-tinta">{credito.documento}</span> ·{" "}
                Crédito: <span className="font-mono font-bold text-kaizen-800">{credito.codigo_credito}</span> (
                {credito.tipo === "corp" ? "Corporativo" : "Automotriz"})
              </p>
            </div>

            <div className="text-left sm:text-right border-t sm:border-t-0 pt-2 sm:pt-0 border-emerald-200">
              <p className="text-[10px] font-semibold uppercase text-emerald-800">
                Fecha de Liquidación
              </p>
              <p className="text-sm font-bold text-emerald-950">
                {formatearFecha(credito.fecha_liquidacion)}
              </p>
              <p className="text-[10px] text-tinta-suave">
                Cajero: {credito.cajero_ultimo_cobro}
              </p>
            </div>
          </div>
        </div>

        {/* Resumen Financiero de la Operación */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          <div className="rounded-lg border border-borde bg-slate-50 p-2.5">
            <p className="text-[10px] font-semibold text-tinta-suave uppercase">
              Monto Original
            </p>
            <p className="text-sm font-bold text-kaizen-900 tabular-nums">
              {formatearDinero(credito.monto_original)}
            </p>
          </div>
          <div className="rounded-lg border border-borde bg-slate-50 p-2.5">
            <p className="text-[10px] font-semibold text-tinta-suave uppercase">
              Capital Amortizado
            </p>
            <p className="text-sm font-bold text-emerald-700 tabular-nums">
              {formatearDinero(credito.total_capital_pagado)}
            </p>
          </div>
          <div className="rounded-lg border border-borde bg-slate-50 p-2.5">
            <p className="text-[10px] font-semibold text-tinta-suave uppercase">
              Intereses Pagados
            </p>
            <p className="text-sm font-bold text-kaizen-800 tabular-nums">
              {formatearDinero(credito.total_intereses_pagados)}
            </p>
          </div>
          <div className="rounded-lg border border-emerald-300 bg-emerald-100/60 p-2.5">
            <p className="text-[10px] font-bold text-emerald-900 uppercase">
              Saldo Deudor Actual
            </p>
            <p className="text-sm font-extrabold text-emerald-800 tabular-nums">
              $ 0.00 USD
            </p>
          </div>
        </div>

        {/* Cumplimiento de Cuotas y Datos Contractuales */}
        <div className="rounded-lg border border-borde p-3.5 bg-white space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-kaizen-900">
              Cumplimiento del Plan de Amortización:
            </span>
            <span className="font-bold text-emerald-700">
              {credito.cuotas_pagadas} de {credito.cuotas_totales} cuotas liquidadas (100%)
            </span>
          </div>

          <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
            <div className="bg-emerald-600 h-2 rounded-full w-full"></div>
          </div>

          <div className="flex flex-wrap items-center justify-between text-[11px] text-tinta-suave pt-1">
            <span>Tasa de Interés: <strong className="text-tinta">{credito.tasa_aprobada}%</strong></span>
            <span>Plazo Pactado: <strong className="text-tinta">{credito.plazo_meses} meses</strong></span>
            <span>Comprobantes de Pago: <strong className="text-tinta">{credito.recibos_emitidos} recibos</strong></span>
            <span>Total Recaudado: <strong className="text-kaizen-900 font-bold tabular-nums">{formatearDinero(credito.total_pagado)}</strong></span>
          </div>
        </div>

        {/* Declaración Legal de No Adeudo */}
        <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-3 text-[11px] text-tinta-suave leading-relaxed">
          <p className="font-bold text-kaizen-900 text-xs mb-1 flex items-center gap-1.5">
            <IconoBalanza className="h-3.5 w-3.5 text-kaizen-800" />
            <span>Declaración Formal de Finiquito y Solvencia:</span>
          </p>
          <p>
            Kaizen Financial Group certifica de forma irrevocable que el cliente ha cancelado
            satisfactoriamente todas las cuotas, intereses y costos asociados a esta operación.
            El titular se encuentra libre de toda obligación pendiente por este contrato,
            procediendo a la liberación formal de cualquier garantía asociada.
          </p>
        </div>

        {/* Botones de Acción */}
        <div className="flex flex-col-reverse sm:flex-row sm:items-center sm:justify-between gap-2.5 pt-3 border-t border-borde">
          {alVerHistorial ? (
            <button
              type="button"
              onClick={() => {
                alCerrar();
                alVerHistorial(credito.id, credito.tipo);
              }}
              className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-borde bg-white px-3.5 py-2 text-xs font-semibold text-tinta hover:bg-slate-50 transition"
            >
              <IconoDocumento className="h-3.5 w-3.5" />
              <span>Ver Historial de Recibos</span>
            </button>
          ) : (
            <div></div>
          )}

          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={alCerrar}
              className="rounded-lg border border-borde bg-white px-3.5 py-2 text-xs font-semibold text-tinta hover:bg-slate-100 transition"
            >
              Cerrar
            </button>

            <button
              type="button"
              onClick={manejarDescarga}
              disabled={descargando}
              className="inline-flex items-center gap-2 rounded-lg bg-kaizen-900 px-4 py-2 text-xs font-bold text-white hover:bg-kaizen-800 transition shadow-xs disabled:opacity-50"
            >
              {descargando ? (
                <>
                  <Girador />
                  <span>Generando PDF...</span>
                </>
              ) : (
                <>
                  <IconoDescargar className="h-3.5 w-3.5" />
                  <span>Descargar Solvencia Oficial (PDF)</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
