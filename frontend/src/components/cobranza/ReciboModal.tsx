"use client";

import { useState } from "react";
import type { ResultadoPago } from "@/hooks/useCobranzas";
import { descargarReciboPdf } from "@/hooks/useCobranzas";
import { Modal } from "@/components/ui/Modal";
import { Girador } from "@/components/ui/Skeleton";
import { useAvisos } from "@/components/ui/Toast";
import { guardarComo } from "@/utils/descargas";
import { ApiError } from "@/utils/apiClient";
import { formatearDinero, formatearFecha } from "@/utils/format";
import { IconoDescargar } from "@/components/ui/Iconos";

interface Props {
  abierto: boolean;
  alCerrar: () => void;
  recibo: ResultadoPago | null;
}

export function ReciboModal({ abierto, alCerrar, recibo }: Props) {
  const { notificar, notificarError } = useAvisos();
  const [descargando, setDescargando] = useState(false);

  if (!recibo) return null;

  const manejarDescarga = async () => {
    setDescargando(true);
    try {
      const archivo = await descargarReciboPdf(recibo.pago_id);
      guardarComo(archivo);
      notificar("exito", "Recibo Descargado", `Se generó el comprobante ${recibo.numero_recibo}.`);
    } catch (err: unknown) {
      notificarError(
        err instanceof ApiError ? err : new ApiError(0, "No se pudo descargar el recibo oficial."),
      );
    } finally {
      setDescargando(false);
    }
  };

  const c = recibo.cascada;

  return (
    <Modal
      abierto={abierto}
      alCerrar={alCerrar}
      titulo={`Comprobante de Caja Oficial: ${recibo.numero_recibo}`}
      descripcion="Pago procesado exitosamente e imputado bajo estricta cascada legal."
    >
      <div className="space-y-4 text-xs">
        {/* Cabecera del comprobante */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-borde pb-3">
          <div>
            <p className="font-bold text-sm text-kaizen-900">{recibo.cliente}</p>
            <p className="text-tinta-suave">
              Expediente: {recibo.tipo_expediente.toUpperCase()} #{recibo.expediente_id} · Fecha: {formatearFecha(recibo.fecha)}
            </p>
          </div>
          <div className="text-right">
            <span className="rounded-full bg-verde-fondo px-2.5 py-0.5 text-xs font-bold text-verde-trazo">
              ✓ Pago Confirmado
            </span>
            <p className="mt-1 text-[11px] text-tinta-suave">Cajero: {recibo.cajero}</p>
          </div>
        </div>

        {/* Total Pagado */}
        <div className="rounded-lg bg-kaizen-50 p-3 flex justify-between items-center">
          <div>
            <p className="text-tinta-suave font-semibold">Total Ingresado en Caja:</p>
            <p className="text-xl font-extrabold text-kaizen-900 tabular-nums">
              {formatearDinero(recibo.monto_total_usd)}
            </p>
          </div>
          <div className="text-right text-[11px] text-tinta-suave">
            <p>Tasa aplicada: {recibo.tasa_cambio.toFixed(2)} VES/USD</p>
            <p className="font-semibold text-kaizen-800 tabular-nums">
              ≈ Bs. {recibo.monto_total_ves.toLocaleString("es-VE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
          </div>
        </div>

        {/* Desglose de Cascada Legal */}
        <div>
          <h4 className="font-bold text-kaizen-900 uppercase text-[11px] tracking-wider mb-2">
            Distribución del Pago (Cascada Legal):
          </h4>
          <div className="divide-y divide-slate-100 rounded-lg border border-borde">
            <div className="flex justify-between p-2">
              <span className="text-tinta-suave">1. Gastos de Cobranza y Honorarios:</span>
              <span className="font-semibold tabular-nums">{formatearDinero(c.gastos_cobranza)}</span>
            </div>
            <div className="flex justify-between p-2">
              <span className="text-tinta-suave">2. Intereses de Mora Acumulados:</span>
              <span className="font-semibold tabular-nums">{formatearDinero(c.intereses_mora)}</span>
            </div>
            <div className="flex justify-between p-2">
              <span className="text-tinta-suave">3. Intereses Corrientes del Período:</span>
              <span className="font-semibold tabular-nums">{formatearDinero(c.interes_corriente)}</span>
            </div>
            <div className="flex justify-between p-2 bg-verde-fondo/40 font-bold text-kaizen-900">
              <span>4. Abono Efectivo a Capital:</span>
              <span className="tabular-nums text-verde-trazo">{formatearDinero(c.abono_capital)}</span>
            </div>
          </div>
        </div>

        {/* Estado de Deuda: Saldo Anterior - Pago = Nuevo Saldo */}
        <div className="rounded-lg border border-borde bg-slate-50 p-3 space-y-1">
          <p className="text-[11px] font-bold text-kaizen-900 uppercase">
            Estado Actualizado de la Deuda:
          </p>
          <div className="flex items-center justify-between text-xs">
            <span>Saldo Anterior:</span>
            <span className="font-semibold tabular-nums">{formatearDinero(c.saldo_anterior)}</span>
          </div>
          <div className="flex items-center justify-between text-xs text-verde-trazo font-semibold">
            <span>Menos Pago Realizado:</span>
            <span className="tabular-nums">- {formatearDinero(recibo.monto_total_usd)}</span>
          </div>
          <div className="flex items-center justify-between border-t border-borde pt-1 text-sm font-extrabold text-kaizen-900">
            <span>NUEVO SALDO DE CAPITAL:</span>
            <span className="tabular-nums text-base">{formatearDinero(c.nuevo_saldo)}</span>
          </div>
        </div>

        {/* Botones de Acción */}
        <div className="flex justify-end gap-3 pt-3 border-t border-borde">
          <button
            type="button"
            onClick={alCerrar}
            className="rounded-lg border border-borde px-4 py-2 font-semibold text-tinta hover:bg-slate-100"
          >
            Aceptar y Cerrar
          </button>
          <button
            type="button"
            disabled={descargando}
            onClick={() => void manejarDescarga()}
            className="inline-flex items-center gap-2 rounded-lg bg-kaizen-800 px-5 py-2 font-bold text-white shadow-sm hover:bg-kaizen-900 transition"
          >
            {descargando ? <Girador /> : <IconoDescargar className="h-4 w-4" />}
            <span>{descargando ? "Generando PDF…" : "Descargar Recibo Oficial (PDF)"}</span>
          </button>
        </div>
      </div>
    </Modal>
  );
}
