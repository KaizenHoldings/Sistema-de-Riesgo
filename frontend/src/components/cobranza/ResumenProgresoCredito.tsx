"use client";

import type { ResumenFinanciero } from "@/hooks/useCobranzas";
import { formatearDinero, formatearFecha, textoOGuion } from "@/utils/format";
import {
  IconoDinero,
  IconoReloj,
  IconoCheck,
  IconoAlerta,
  IconoTrending,
} from "@/components/ui/Iconos";

interface Props {
  resumen: ResumenFinanciero;
  className?: string;
}

export function ResumenProgresoCredito({ resumen, className = "" }: Props) {
  const cuotasTotales = resumen.cuotas_totales || resumen.plazo_meses || 1;
  const cuotasPagadas = resumen.cuotas_pagadas || 0;
  const cuotasPendientes = Math.max(0, cuotasTotales - cuotasPagadas);

  const porcentajeCuotas = Math.min(100, Math.round((cuotasPagadas / cuotasTotales) * 100));

  const totalPagadoCliente =
    typeof resumen.total_pagado_cliente === "number" && resumen.total_pagado_cliente > 0
      ? resumen.total_pagado_cliente
      : Math.max(0, resumen.monto_original - resumen.saldo_capital);

  const capitalAmortizado =
    typeof resumen.capital_amortizado === "number" && resumen.capital_amortizado > 0
      ? resumen.capital_amortizado
      : Math.max(0, resumen.monto_original - resumen.saldo_capital);

  const interesesPagados =
    typeof resumen.intereses_pagados === "number" && resumen.intereses_pagados > 0
      ? resumen.intereses_pagados
      : Math.max(0, totalPagadoCliente - capitalAmortizado);

  const porcentajeCapital =
    resumen.monto_original > 0
      ? Math.min(100, Math.round((capitalAmortizado / resumen.monto_original) * 100))
      : 0;

  const enMora = resumen.dias_atraso > 0 || resumen.num_cuotas_vencidas > 0;

  return (
    <div className={`space-y-4 ${className}`}>
      {/* ── Encabezado del Crédito y Estado ─────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-xl border border-kaizen-200 bg-slate-50/70 p-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded bg-kaizen-800 px-2.5 py-1 text-xs font-bold text-white uppercase tracking-wider">
              {resumen.codigo_credito}
            </span>
            <span className="font-bold text-sm text-kaizen-900">{resumen.cliente}</span>
            <span className="rounded border border-kaizen-200 bg-white px-2 py-0.5 font-mono text-xs text-tinta">
              Doc: {textoOGuion(resumen.documento)}
            </span>
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-semibold inline-flex items-center gap-1 ${
                enMora
                  ? "bg-rojo-fondo text-rojo-trazo border border-rojo-trazo/20"
                  : "bg-verde-fondo text-verde-trazo border border-verde-trazo/20"
              }`}
            >
              {enMora ? (
                <>
                  <IconoAlerta className="h-3.5 w-3.5" />
                  <span>Mora ({resumen.dias_atraso} días)</span>
                </>
              ) : (
                <>
                  <IconoCheck className="h-3.5 w-3.5" />
                  <span>Crédito al día</span>
                </>
              )}
            </span>
          </div>
          <p className="mt-1 text-xs text-tinta-suave">
            Línea {resumen.tipo === "corp" ? "Corporativa" : "Automotriz"} · Tasa acordada:{" "}
            <strong className="text-kaizen-900">{resumen.tasa_aprobada}% anual</strong> · Aprobado por Comité
          </p>
        </div>

        <div className="text-left sm:text-right">
          <p className="text-[11px] text-tinta-suave uppercase font-semibold">Próximo Vencimiento</p>
          <p className="text-xs font-bold text-kaizen-900">
            {formatearFecha(resumen.fecha_proxima_cuota)}
          </p>
          {resumen.monto_proxima_cuota > 0 && (
            <p className="text-[11px] text-tinta-suave tabular-nums">
              Cuota: {formatearDinero(resumen.monto_proxima_cuota)}
            </p>
          )}
        </div>
      </div>

      {/* ── 4 Tarjetas de Métricas de Interés ───────────────────────── */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {/* Tarjeta 1: Dinero que le falta por pagar */}
        <div className="rounded-xl border border-borde bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-tinta-suave uppercase tracking-wider">
              Dinero que le Falta
            </span>
            <div className="rounded-md bg-kaizen-50 p-1.5 text-kaizen-800">
              <IconoDinero className="h-4 w-4" />
            </div>
          </div>
          <p className="mt-2 text-xl font-extrabold text-kaizen-900 tabular-nums">
            {formatearDinero(resumen.saldo_capital)}
          </p>
          <div className="mt-1 text-[11px] text-tinta-suave space-y-0.5">
            <p>Saldo Capital Pendiente</p>
            <p className="text-[10px] text-tinta-suave">
              Deuda total nominal: <strong>{formatearDinero(resumen.saldo_total_deuda)}</strong>
            </p>
          </div>
        </div>

        {/* Tarjeta 2: Cuotas Cubiertas vs Pendientes */}
        <div className="rounded-xl border border-borde bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-tinta-suave uppercase tracking-wider">
              Cuotas Cubiertas
            </span>
            <div className="rounded-md bg-verde-fondo p-1.5 text-verde-trazo">
              <IconoCheck className="h-4 w-4" />
            </div>
          </div>
          <p className="mt-2 text-xl font-extrabold text-verde-trazo tabular-nums">
            {cuotasPagadas}{" "}
            <span className="text-xs font-semibold text-tinta-suave">/ {cuotasTotales} cuotas</span>
          </p>
          <div className="mt-1 text-[11px] text-tinta-suave space-y-0.5">
            <p>
              <strong className="text-kaizen-900">{cuotasPendientes}</strong> cuotas restantes por pagar
            </p>
            <p className="text-[10px] text-tinta-suave">
              Avance: <strong>{porcentajeCuotas}%</strong> del plazo total
            </p>
          </div>
        </div>

        {/* Tarjeta 3: Duración y Meses del Crédito */}
        <div className="rounded-xl border border-borde bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-tinta-suave uppercase tracking-wider">
              Plazo del Crédito
            </span>
            <div className="rounded-md bg-kaizen-50 p-1.5 text-kaizen-800">
              <IconoReloj className="h-4 w-4" />
            </div>
          </div>
          <p className="mt-2 text-xl font-extrabold text-kaizen-900 tabular-nums">
            {resumen.plazo_meses}{" "}
            <span className="text-xs font-semibold text-tinta-suave">meses</span>
          </p>
          <div className="mt-1 text-[11px] text-tinta-suave space-y-0.5">
            <p>Tiempo pactado de amortización</p>
            <p className="text-[10px] text-tinta-suave">
              Tasa pactada: <strong>{resumen.tasa_aprobada}% anual</strong>
            </p>
          </div>
        </div>

        {/* Tarjeta 4: Total Pagado en Caja y Desglose */}
        <div className="rounded-xl border border-borde bg-white p-4 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-tinta-suave uppercase tracking-wider">
              Total Pagado en Caja
            </span>
            <div className="rounded-md bg-kaizen-50 p-1.5 text-kaizen-800">
              <IconoTrending className="h-4 w-4" />
            </div>
          </div>
          <p className="mt-2 text-xl font-extrabold text-kaizen-900 tabular-nums">
            {formatearDinero(totalPagadoCliente)}
          </p>
          <div className="mt-1 text-[11px] text-tinta-suave space-y-0.5">
            <p>
              Capital amortizado: <strong className="text-kaizen-900">{formatearDinero(capitalAmortizado)}</strong> ({porcentajeCapital}%)
            </p>
            <p className="text-[10px] text-tinta-suave">
              Intereses cubiertos: <strong className="text-tinta">{formatearDinero(interesesPagados)}</strong>
            </p>
          </div>
        </div>
      </div>

      {/* ── Barra de Progreso de Amortización ───────────────────────── */}
      <div className="rounded-xl border border-borde bg-white p-4 shadow-xs space-y-2">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between text-xs gap-1">
          <span className="font-semibold text-kaizen-900">
            Progreso de Pago y Amortización del Crédito
          </span>
          <span className="text-tinta-suave tabular-nums">
            Total pagado en caja: <strong className="text-kaizen-900">{formatearDinero(totalPagadoCliente)}</strong> ({cuotasPagadas} cuotas cubiertas)
          </span>
        </div>

        {/* Barra de Progreso */}
        <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-kaizen-800 transition-all duration-500 ease-out"
            style={{ width: `${porcentajeCuotas}%` }}
            title={`${porcentajeCuotas}% cubierto`}
          />
        </div>

        <div className="flex items-center justify-between text-[11px] text-tinta-suave">
          <span>
            Capital amortizado: <strong className="text-kaizen-800 font-semibold">{formatearDinero(capitalAmortizado)}</strong>
          </span>
          <span>
            Falta por amortizar a capital: <strong className="text-rojo-trazo font-semibold">{formatearDinero(resumen.saldo_capital)}</strong>
          </span>
          <span>Monto original: {formatearDinero(resumen.monto_original)} ({cuotasTotales} cuotas)</span>
        </div>
      </div>
    </div>
  );
}
