"use client";

import { useState, useMemo } from "react";
import type { ResumenFinanciero } from "@/hooks/useCobranzas";
import { formatearDinero, formatearFecha } from "@/utils/format";
import { Modal } from "@/components/ui/Modal";
import { IconoCheck, IconoAlerta } from "@/components/ui/Iconos";
import { ResumenProgresoCredito } from "@/components/cobranza/ResumenProgresoCredito";
import { BuscadorTabla } from "@/components/ui/BuscadorTabla";

interface Props {
  resumen: ResumenFinanciero;
  alSeleccionarParaPagar?: (montoSugerido: number, tipoPago: "cuota" | "al_dia" | "liquidacion") => void;
}

export function PanelInformacionFinanciera({
  resumen,
  alSeleccionarParaPagar,
}: Props) {
  const [modalLiquidacion, setModalLiquidacion] = useState(false);
  const [verPlanCompleto, setVerPlanCompleto] = useState(false);
  const [busquedaCuota, setBusquedaCuota] = useState("");

  const cuotasFiltradas = useMemo(() => {
    const cuotas = resumen.plan_pagos || [];
    if (!busquedaCuota.trim()) return cuotas;
    const q = busquedaCuota.toLowerCase().trim();
    return cuotas.filter((c) => {
      const periodoStr = String(c.periodo || "").toLowerCase();
      const fechaStr = String(c.fecha_pago || "").toLowerCase();
      const estadoStr = String(c.estado || "").toLowerCase();
      const montoStr = String(c.cuota || "").toLowerCase();
      return (
        periodoStr.includes(q) ||
        fechaStr.includes(q) ||
        estadoStr.includes(q) ||
        montoStr.includes(q)
      );
    });
  }, [resumen.plan_pagos, busquedaCuota]);

  const enMora = resumen.dias_atraso > 0 || resumen.num_cuotas_vencidas > 0;

  return (
    <section className="space-y-4">
      {/* ── 1. Resumen de Progreso: Dinero que falta, Cuotas cubiertas, Meses y Avance ── */}
      <ResumenProgresoCredito resumen={resumen} />

      {/* ── 2. Acciones de Liquidación Anticipada ─────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-xl border border-kaizen-200 bg-white p-4 shadow-xs">
        <div>
          <span className="text-xs font-semibold text-tinta-suave uppercase tracking-wider">
            Proyección de Finiquito / Liquidación Total Anticipada Hoy
          </span>
          <div className="flex items-baseline gap-2 mt-0.5">
            <span className="text-lg font-bold text-verde-trazo tabular-nums">
              {formatearDinero(resumen.proyeccion_cancelacion_total)}
            </span>
            <span className="text-xs text-tinta-suave">
              (Ahorro de {formatearDinero(resumen.ahorro_intereses_no_causados)} en intereses futuros no devengados)
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setModalLiquidacion(true)}
            className="rounded-lg border border-kaizen-300 bg-kaizen-50 px-3 py-1.5 text-xs font-semibold text-kaizen-800 hover:bg-kaizen-100 transition"
          >
            Ver desglose de finiquito
          </button>
          {alSeleccionarParaPagar && (
            <button
              type="button"
              onClick={() => alSeleccionarParaPagar(resumen.proyeccion_cancelacion_total, "liquidacion")}
              className="rounded-lg bg-verde-trazo px-3 py-1.5 text-xs font-bold text-white hover:brightness-95 transition"
            >
              Liquidar Todo
            </button>
          )}
        </div>
      </div>

      {/* ── 2. Alerta de Deuda Vencida (Desglose) ────────────────────── */}
      {enMora ? (
        <div className="rounded-xl border border-rojo-trazo/30 bg-rojo-fondo/60 p-4 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-rojo-trazo text-white">
                  <IconoAlerta className="h-3.5 w-3.5" />
                </span>
                <h4 className="text-sm font-bold text-rojo-trazo">
                  Alerta: Expediente en Mora ({resumen.dias_atraso} días de atraso)
                </h4>
              </div>
              <p className="mt-1 text-xs text-tinta">
                Tiene <strong>{resumen.num_cuotas_vencidas} cuota(s) vencida(s)</strong> por {formatearDinero(resumen.monto_cuotas_vencidas)}.
                {resumen.intereses_mora > 0 && ` + Mora: ${formatearDinero(resumen.intereses_mora)}`}
                {resumen.gastos_cobranza > 0 && ` + Gastos cobranza: ${formatearDinero(resumen.gastos_cobranza)}`}.
              </p>
            </div>

            <div className="flex items-center gap-3 shrink-0">
              <div className="text-right">
                <p className="text-xs text-tinta-suave">Monto exacto para estar al día:</p>
                <p className="text-base font-extrabold text-rojo-trazo tabular-nums">
                  {formatearDinero(resumen.monto_ponerse_al_dia)}
                </p>
              </div>
              {alSeleccionarParaPagar && (
                <button
                  type="button"
                  onClick={() => alSeleccionarParaPagar(resumen.monto_ponerse_al_dia, "al_dia")}
                  className="rounded-lg bg-rojo-trazo px-4 py-2 text-xs font-bold text-white shadow-sm hover:brightness-90 transition"
                >
                  Cobrar Monto al Día
                </button>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-xl border border-verde-trazo/30 bg-verde-fondo/50 p-3.5 flex items-center justify-between text-xs text-verde-trazo">
          <div className="flex items-center gap-2">
            <IconoCheck className="h-4 w-4 shrink-0" />
            <span className="font-semibold">
              El cliente se encuentra al día con sus compromisos de pago.
            </span>
          </div>
          {alSeleccionarParaPagar && resumen.monto_proxima_cuota > 0 && (
            <button
              type="button"
              onClick={() => alSeleccionarParaPagar(resumen.monto_proxima_cuota, "cuota")}
              className="font-bold underline hover:opacity-80"
            >
              Cargar cuota actual ({formatearDinero(resumen.monto_proxima_cuota)}) en caja
            </button>
          )}
        </div>
      )}

      {/* ── 3. Plan de Pagos e Historial de Cuotas (Colapsable) ──────── */}
      <div className="rounded-xl border border-borde bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-xs font-bold text-kaizen-900 uppercase tracking-wider">
              Estructura de Cuotas y Amortización ({resumen.cuotas_pagadas} de {resumen.cuotas_totales} cuotas pagadas)
            </h4>
            <p className="text-xs text-tinta-suave">
              Visualice los períodos del crédito, vencimientos y estados de pago.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setVerPlanCompleto((v) => !v)}
            className="text-xs font-semibold text-kaizen-700 hover:text-kaizen-900"
          >
            {verPlanCompleto ? "Ocultar cuotas ▲" : "Ver detalle de cuotas ▼"}
          </button>
        </div>

        {verPlanCompleto && (
          <div className="mt-4 space-y-3 border-t border-borde pt-3">
            <div className="w-full sm:max-w-xs">
              <BuscadorTabla
                valor={busquedaCuota}
                alCambiar={setBusquedaCuota}
                placeholder="Buscar cuota, fecha, estado..."
                conteoFiltrado={cuotasFiltradas.length}
                conteoTotal={resumen.plan_pagos.length}
              />
            </div>

            {cuotasFiltradas.length === 0 ? (
              <div className="rounded-lg border border-dashed border-borde p-6 text-center text-xs text-tinta-suave">
                No se encontraron cuotas que coincidan con &ldquo;{busquedaCuota}&rdquo;.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b text-tinta-suave uppercase font-semibold">
                    <tr>
                      <th className="py-2">N°</th>
                      <th>Fecha Pago</th>
                      <th>Cuota</th>
                      <th>Capital</th>
                      <th>Interés</th>
                      <th>Saldo</th>
                      <th>Estado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {cuotasFiltradas.map((cuota) => (
                      <tr
                        key={cuota.id ?? cuota.periodo}
                        className={
                          cuota.estado === "PAGADO"
                            ? "bg-slate-50 text-tinta-suave"
                            : cuota.estado === "PAGADO_ANTICIPADO"
                            ? "bg-kaizen-50/50 text-kaizen-700 font-medium"
                            : "text-tinta font-medium"
                        }
                      >
                        <td className="py-1.5 font-bold">{cuota.periodo}</td>
                        <td>{formatearFecha(cuota.fecha_pago)}</td>
                        <td className="tabular-nums font-semibold">{formatearDinero(cuota.cuota)}</td>
                        <td className="tabular-nums">{formatearDinero(cuota.capital)}</td>
                        <td className="tabular-nums">{formatearDinero(cuota.interes)}</td>
                        <td className="tabular-nums">{formatearDinero(cuota.saldo)}</td>
                        <td>
                          <span
                            className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                              cuota.estado === "PAGADO" || cuota.estado === "PAGADO_ANTICIPADO"
                                ? "bg-verde-fondo text-verde-trazo"
                                : "bg-ambar-fondo text-ambar-trazo"
                            }`}
                          >
                            {cuota.estado}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Modal de Proyección de Liquidación Total ─────────────────── */}
      <Modal
        abierto={modalLiquidacion}
        alCerrar={() => setModalLiquidacion(false)}
        titulo="Proyección de Liquidación Inmediata del Crédito"
        descripcion="Cálculo financiero para cancelar la totalidad de la deuda hoy, restando los intereses futuros no causados."
      >
        <div className="space-y-4 text-xs">
          <div className="rounded-lg border border-verde-trazo/30 bg-verde-fondo/60 p-3">
            <p className="font-semibold text-verde-trazo">
              Ahorro de Intereses No Causados para el Cliente:
            </p>
            <p className="text-xl font-extrabold text-verde-trazo tabular-nums">
              {formatearDinero(resumen.ahorro_intereses_no_causados)}
            </p>
            <p className="mt-0.5 text-[11px] text-tinta-suave">
              Al liquidar hoy, se exonera la totalidad de los intereses de los períodos futuros restantes.
            </p>
          </div>

          <div className="space-y-2 border-t border-borde pt-3">
            <div className="flex justify-between py-1">
              <span className="text-tinta-suave">Capital Insoluto Pendiente:</span>
              <span className="font-semibold tabular-nums">{formatearDinero(resumen.saldo_capital)}</span>
            </div>
            {resumen.intereses_mora > 0 && (
              <div className="flex justify-between py-1 text-rojo-trazo">
                <span>Intereses de Mora Acumulados:</span>
                <span className="font-semibold tabular-nums">+ {formatearDinero(resumen.intereses_mora)}</span>
              </div>
            )}
            {resumen.gastos_cobranza > 0 && (
              <div className="flex justify-between py-1 text-rojo-trazo">
                <span>Gastos de Cobranza Administrativos:</span>
                <span className="font-semibold tabular-nums">+ {formatearDinero(resumen.gastos_cobranza)}</span>
              </div>
            )}
            <div className="flex justify-between py-2 border-t border-borde text-sm font-bold text-kaizen-900">
              <span>Monto Total para Finiquitar Hoy:</span>
              <span className="text-base text-verde-trazo tabular-nums">
                {formatearDinero(resumen.proyeccion_cancelacion_total)}
              </span>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-3">
            <button
              type="button"
              onClick={() => setModalLiquidacion(false)}
              className="rounded-lg border border-borde px-4 py-2 font-semibold text-tinta hover:bg-slate-100"
            >
              Cerrar
            </button>
            {alSeleccionarParaPagar && (
              <button
                type="button"
                onClick={() => {
                  setModalLiquidacion(false);
                  alSeleccionarParaPagar(resumen.proyeccion_cancelacion_total, "liquidacion");
                }}
                className="rounded-lg bg-verde-trazo px-4 py-2 font-bold text-white hover:brightness-90"
              >
                Cargar Liquidación en Caja
              </button>
            )}
          </div>
        </div>
      </Modal>
    </section>
  );
}
