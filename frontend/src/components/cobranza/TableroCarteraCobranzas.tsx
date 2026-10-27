"use client";

import { useMemo, useState } from "react";
import {
  useArqueoDiario,
  useTasaCambio,
  useUltimosCobros,
  useAlertasCobro,
  descargarReciboPdf,
} from "@/hooks/useCobranzas";
import { useResumenExpedientes } from "@/hooks/useExpedientes";
import { useAging, useVencimientos } from "@/hooks/useCartera";
import { Girador, SkeletonMetricas, SkeletonTabla } from "@/components/ui/Skeleton";
import { Insignia } from "@/components/ui/Semaforo";
import { useAvisos } from "@/components/ui/Toast";
import { guardarComo } from "@/utils/descargas";
import { ApiError } from "@/utils/apiClient";
import {
  formatearDinero,
  formatearEntero,
  formatearFecha,
} from "@/utils/format";
import {
  IconoTarjeta,
  IconoBalanza,
  IconoRefrescar,
  IconoTrending,
  IconoDocumento,
  IconoAlerta,
  IconoTelefono,
  IconoDescargar,
  IconoFlechaDerecha,
  IconoCheck,
} from "@/components/ui/Iconos";
import { BuscadorTabla } from "@/components/ui/BuscadorTabla";

interface Props {
  alIrACaja: (expId?: number, tipo?: "corp" | "auto") => void;
  alIrAArqueo: () => void;
  alIrAPagados?: () => void;
}

export function TableroCarteraCobranzas({ alIrACaja, alIrAArqueo, alIrAPagados }: Props) {
  const { tasa: tasaCambio, cargando: cargandoTasa } = useTasaCambio();
  const hoyStr = new Date().toISOString().slice(0, 10);
  const { arqueo, cargando: cargandoArqueo, recargar: recargarArqueo } = useArqueoDiario(hoyStr);
  const { cobros, cargando: cargandoCobros, recargar: recargarCobros } = useUltimosCobros(15);
  const { alertas, cargando: cargandoAlertas, recargar: recargarAlertas } = useAlertasCobro(30);

  const [busquedaCobros, setBusquedaCobros] = useState("");
  const [busquedaAlertas, setBusquedaAlertas] = useState("");

  const cobrosFiltrados = useMemo(() => {
    if (!busquedaCobros.trim()) return cobros;
    const q = busquedaCobros.toLowerCase().trim();
    return cobros.filter((c) => {
      const rec = String(c.numero_recibo || "").toLowerCase();
      const cli = String(c.cliente || "").toLowerCase();
      const caj = String(c.cajero || "").toLowerCase();
      const met = String(c.metodo || "").toLowerCase();
      const mon = String(c.monto_usd || "").toLowerCase();
      const monVes = String(c.monto_ves || "").toLowerCase();
      return (
        rec.includes(q) ||
        cli.includes(q) ||
        caj.includes(q) ||
        met.includes(q) ||
        mon.includes(q) ||
        monVes.includes(q)
      );
    });
  }, [cobros, busquedaCobros]);

  const alertasFiltradas = useMemo(() => {
    if (!busquedaAlertas.trim()) return alertas;
    const q = busquedaAlertas.toLowerCase().trim();
    return alertas.filter((a) => {
      const cli = String(a.cliente || "").toLowerCase();
      const cod = String(a.codigo_credito || "").toLowerCase();
      const tel = String(a.telefono || "").toLowerCase();
      const est = String(a.dias_texto || "").toLowerCase();
      const cuo = String(a.cuota || "").toLowerCase();
      return (
        cli.includes(q) ||
        cod.includes(q) ||
        tel.includes(q) ||
        est.includes(q) ||
        cuo.includes(q)
      );
    });
  }, [alertas, busquedaAlertas]);

  const corporativos = useResumenExpedientes("corporativos");
  const automotrices = useResumenExpedientes("automotrices");
  const vencimientos = useVencimientos(30);
  const aging = useAging();

  const { notificar, notificarError } = useAvisos();
  const [descargandoId, setDescargandoId] = useState<number | null>(null);

  // Meta de cobro diaria estimada (por defecto $5,000 USD)
  const metaDiariaUsd = 5000.0;
  const recaudoHoyUsd = arqueo?.total_usd || 0;
  const recaudoHoyVes = arqueo?.total_ves || (recaudoHoyUsd * (tasaCambio.USD_VES || 45.45));
  const porcentajeMeta = Math.min(Math.round((recaudoHoyUsd / metaDiariaUsd) * 100), 100);

  // Cartera Total Activa y Morosidad
  const resumenCartera = useMemo(() => {
    const aprobado = (r: Record<string, { n: number; monto: number }> | null) =>
      r?.APROBADO ?? { n: 0, monto: 0 };
    const corp = aprobado(corporativos.datos);
    const auto = aprobado(automotrices.datos);
    const totalMonto = corp.monto + auto.monto;
    const montoVencido = vencimientos.datos?.monto_vencido ?? 0;
    const indiceMora = totalMonto > 0 ? (montoVencido / totalMonto) * 100 : 0;

    return {
      totalMonto,
      montoVencido,
      indiceMora: Number(indiceMora.toFixed(1)),
      totalActivos: corp.n + auto.n,
    };
  }, [corporativos.datos, automotrices.datos, vencimientos.datos]);

  const manejarDescargaRecibo = async (pagoId: number) => {
    setDescargandoId(pagoId);
    try {
      const archivo = await descargarReciboPdf(pagoId);
      guardarComo(archivo);
      notificar("exito", "Recibo Descargado", `Se descargó el comprobante #${pagoId}.`);
    } catch (err: unknown) {
      notificarError(
        err instanceof ApiError ? err : new ApiError(0, "No se pudo descargar el recibo."),
      );
    } finally {
      setDescargandoId(null);
    }
  };

  const recargarTodo = () => {
    recargarArqueo();
    recargarCobros();
    recargarAlertas();
    aging.recargar();
    vencimientos.recargar();
  };

  return (
    <div className="space-y-8">
      {/* ── 3. BARRA DE ACCIONES RÁPIDAS Y OPERATIVAS ──────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-xl border border-kaizen-800 bg-kaizen-900 p-4 text-white shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <span className="flex h-2 w-2 rounded-full bg-verde-trazo ring-2 ring-emerald-500/20" />
            <h2 className="text-xs font-bold tracking-wider uppercase text-white">
              Centro de Operación y Monitoreo Financiero
            </h2>
          </div>
          <p className="text-xs text-slate-400">
            Jornada operativa del {new Date().toLocaleDateString("es-VE", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            onClick={() => alIrACaja()}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 px-3.5 py-2 text-xs font-semibold text-white shadow-sm transition active:scale-95"
          >
            <IconoTarjeta className="h-4 w-4" />
            <span>Nueva Operación (Caja Mixta)</span>
          </button>

          <button
            type="button"
            onClick={() => alIrAArqueo()}
            className="inline-flex items-center gap-2 rounded-lg bg-kaizen-800 hover:bg-kaizen-700 px-3.5 py-2 text-xs font-semibold text-slate-200 border border-kaizen-700 transition active:scale-95"
          >
            <IconoBalanza className="h-4 w-4" />
            <span>Arqueo / Cierre de Turno</span>
          </button>

          {alIrAPagados && (
            <button
              type="button"
              onClick={alIrAPagados}
              className="inline-flex items-center gap-2 rounded-lg bg-emerald-800 hover:bg-emerald-700 px-3.5 py-2 text-xs font-semibold text-white shadow-xs border border-emerald-600/40 transition active:scale-95"
            >
              <IconoCheck className="h-4 w-4 text-emerald-300" />
              <span>Créditos Pagados</span>
            </button>
          )}

          <button
            type="button"
            onClick={recargarTodo}
            title="Refrescar datos en tiempo real"
            className="rounded-lg bg-kaizen-800 hover:bg-kaizen-700 p-2 text-slate-300 border border-kaizen-700 transition active:scale-95"
          >
            <IconoRefrescar className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* ── 1. INDICADORES DE GESTIÓN DEL DÍA (KPIS RÁPIDOS) ───────────── */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold text-kaizen-900 uppercase tracking-wider flex items-center gap-2">
            <IconoTrending className="h-4 w-4 text-kaizen-800" />
            <span>Indicadores de Gestión del Día (Jornada Actual)</span>
          </h3>
          <span className="text-[11px] text-tinta-suave">
            Actualización al segundo
          </span>
        </div>

        {cargandoArqueo || cargandoTasa ? (
          <SkeletonMetricas tarjetas={4} />
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {/* KPI 1: Recaudo Total del Día */}
            <div className="rounded-xl border border-borde bg-white p-5 shadow-sm space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold text-tinta-suave uppercase">
                <span>Recaudo Total del Día</span>
                <span className="rounded bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-verde-trazo border border-emerald-200">
                  Ingreso Hoy
                </span>
              </div>
              <div className="text-2xl font-black text-kaizen-900 tabular-nums">
                {formatearDinero(recaudoHoyUsd)}
              </div>
              <div className="text-xs text-tinta-suave flex items-center justify-between pt-1 border-t border-slate-100">
                <span>Equivalente VES:</span>
                <span className="font-bold text-kaizen-800 tabular-nums">
                  Bs. {recaudoHoyVes.toLocaleString("es-VE", { minimumFractionDigits: 2 })}
                </span>
              </div>
            </div>

            {/* KPI 2: Meta de Cobro Diaria */}
            <div className="rounded-xl border border-borde bg-white p-5 shadow-sm space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold text-tinta-suave uppercase">
                <span>Meta de Cobro Diaria</span>
                <span className="font-bold text-kaizen-900 tabular-nums">
                  {porcentajeMeta}%
                </span>
              </div>
              <div className="text-2xl font-black text-kaizen-900 tabular-nums">
                {formatearDinero(recaudoHoyUsd)} <span className="text-xs font-normal text-tinta-suave">/ {formatearDinero(metaDiariaUsd)}</span>
              </div>
              <div className="space-y-1 pt-1 border-t border-slate-100">
                <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      porcentajeMeta >= 80 ? "bg-verde-trazo" : porcentajeMeta >= 40 ? "bg-ambar-trazo" : "bg-kaizen-600"
                    }`}
                    style={{ width: `${porcentajeMeta}%` }}
                  />
                </div>
                <p className="text-[10px] text-tinta-suave text-right">
                  {porcentajeMeta >= 100 ? "Meta diaria alcanzada" : `Faltan ${formatearDinero(Math.max(0, metaDiariaUsd - recaudoHoyUsd))}`}
                </p>
              </div>
            </div>

            {/* KPI 3: Transacciones Procesadas */}
            <div className="rounded-xl border border-borde bg-white p-5 shadow-sm space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold text-tinta-suave uppercase">
                <span>Transacciones Procesadas</span>
                <span className="rounded bg-blue-50 px-2 py-0.5 text-[10px] font-bold text-kaizen-800 border border-blue-200">
                  Caja
                </span>
              </div>
              <div className="text-2xl font-black text-kaizen-900 tabular-nums">
                {formatearEntero(arqueo?.total_transacciones || 0)} <span className="text-xs font-normal text-tinta-suave">recibos</span>
              </div>
              <div className="text-xs text-tinta-suave flex items-center justify-between pt-1 border-t border-slate-100">
                <span>Clientes atendidos hoy:</span>
                <span className="font-bold text-kaizen-800 tabular-nums">
                  {arqueo?.total_transacciones || 0}
                </span>
              </div>
            </div>

            {/* KPI 4: Tasa de Cambio Oficial Activa */}
            <div className="rounded-xl border border-borde bg-white p-5 shadow-sm space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold text-tinta-suave uppercase">
                <span>Tasa Oficial Activa (BCV)</span>
                <span className="rounded bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-700 border border-amber-200">
                  Oficial
                </span>
              </div>
              <div className="text-2xl font-black text-kaizen-900 tabular-nums">
                {tasaCambio.USD_VES.toFixed(2)} <span className="text-xs font-normal text-tinta-suave">Bs./USD</span>
              </div>
              <div className="text-xs text-tinta-suave flex items-center justify-between pt-1 border-t border-slate-100">
                <span>Regla de conversión:</span>
                <span className="font-semibold text-verde-trazo">Fijada e inmodificable</span>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* ── 2. ESTADO GENERAL DE LA CARTERA (SALUD DEL NEGOCIO) ────────── */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold text-kaizen-900 uppercase tracking-wider flex items-center gap-2">
            <IconoBalanza className="h-4 w-4 text-kaizen-800" />
            <span>Estado General de la Cartera (La Salud de tu Negocio)</span>
          </h3>
          <span className="text-[11px] text-tinta-suave">
            Total en calle: <strong className="text-kaizen-900">{formatearDinero(resumenCartera.totalMonto)}</strong>
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Tarjeta de Índice de Morosidad */}
          <div className="rounded-xl border border-borde bg-white p-5 shadow-sm flex flex-col justify-between space-y-4">
            <div>
              <p className="text-xs font-semibold text-tinta-suave uppercase">Índice de Morosidad Actual</p>
              <div className="mt-2 flex items-baseline gap-3">
                <span className={`text-4xl font-black tabular-nums ${
                  resumenCartera.indiceMora <= 5 ? "text-verde-trazo" : resumenCartera.indiceMora <= 15 ? "text-ambar-trazo" : "text-rojo-trazo"
                }`}>
                  {resumenCartera.indiceMora}%
                </span>
                <span className="text-xs text-tinta-suave font-medium">
                  del capital colocado
                </span>
              </div>
            </div>

            <div className="space-y-2 rounded-lg bg-slate-50 p-3 text-xs border border-slate-100">
              <div className="flex justify-between">
                <span className="text-tinta-suave">Cartera Sana / Al día:</span>
                <span className="font-bold text-verde-trazo tabular-nums">
                  {formatearDinero(Math.max(0, resumenCartera.totalMonto - resumenCartera.montoVencido))}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-tinta-suave">Cartera Vencida (En Mora):</span>
                <span className="font-bold text-rojo-trazo tabular-nums">
                  {formatearDinero(resumenCartera.montoVencido)}
                </span>
              </div>
              <div className="flex justify-between border-t border-slate-200 pt-1">
                <span className="text-tinta-suave font-semibold">Créditos Activos:</span>
                <span className="font-bold text-kaizen-900 tabular-nums">
                  {formatearEntero(resumenCartera.totalActivos)}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2 text-[11px]">
              <span className={`h-2 w-2 rounded-full ${
                resumenCartera.indiceMora <= 5 ? "bg-verde-trazo" : resumenCartera.indiceMora <= 15 ? "bg-ambar-trazo" : "bg-rojo-trazo"
              }`} />
              <span className="text-tinta-suave font-medium">
                {resumenCartera.indiceMora <= 5
                  ? "Cartera saludable (mora controlada inferior al 5%)."
                  : resumenCartera.indiceMora <= 15
                  ? "Atención requerida: acelerar cobranza en tramos tempranos."
                  : "Alerta crítica: mora elevada, focalizar gestión jurídica."}
              </span>
            </div>
          </div>

          {/* Gráfico de Edades de Mora (Segmentación por Tramos) */}
          <div className="lg:col-span-2 rounded-xl border border-borde bg-white p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-tinta-suave uppercase">Gráfico de Edades de Mora (Aging)</p>
                <p className="text-[11px] text-tinta-suave">Distribución del saldo vencido según los días de atraso</p>
              </div>
              <span className="text-xs font-bold text-rojo-trazo tabular-nums">
                Total Vencido: {formatearDinero(resumenCartera.montoVencido)}
              </span>
            </div>

            {aging.cargando ? (
              <SkeletonTabla filas={4} columnas={3} />
            ) : (
              <div className="space-y-3 pt-2">
                {[
                  { etiqueta: "Al día (Vence en ≤ 30 días)", monto: vencimientos.datos?.monto_proximo ?? 0, color: "bg-emerald-500", textoColor: "text-emerald-700" },
                  { etiqueta: "Mora Temprana (1 - 30 días)", monto: aging.datos?.["1-30 días"]?.monto ?? 0, color: "bg-amber-500", textoColor: "text-amber-700" },
                  { etiqueta: "Mora Media (31 - 60 días)", monto: aging.datos?.["31-60 días"]?.monto ?? 0, color: "bg-orange-500", textoColor: "text-orange-700" },
                  { etiqueta: "Mora Pesada (> 60 - 90+ días)", monto: (aging.datos?.["61-90 días"]?.monto ?? 0) + (aging.datos?.["> 90 días"]?.monto ?? 0), color: "bg-rose-600", textoColor: "text-rose-700" },
                ].map((item) => {
                  const baseCalculo = resumenCartera.totalMonto > 0 ? resumenCartera.totalMonto : 1;
                  const pct = Math.min(Math.round((item.monto / baseCalculo) * 100), 100);

                  return (
                    <div key={item.etiqueta} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-kaizen-900">{item.etiqueta}</span>
                        <div className="flex items-center gap-3">
                          <span className={`font-bold tabular-nums ${item.textoColor}`}>
                            {formatearDinero(item.monto)}
                          </span>
                          <span className="text-[11px] text-tinta-suave tabular-nums w-10 text-right">
                            {pct}%
                          </span>
                        </div>
                      </div>
                      <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${item.color} transition-all duration-500`}
                          style={{ width: `${Math.max(pct, item.monto > 0 ? 3 : 0)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ── 4. TABLAS DE MONITOREO EN TIEMPO REAL ────────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Tabla A: Últimos Cobros Recibidos (Historial Reciente) */}
        <section className="rounded-xl border border-borde bg-white p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-borde pb-3">
            <div>
              <h4 className="text-xs font-bold text-kaizen-900 uppercase tracking-wider flex items-center gap-2">
                <IconoDocumento className="h-4 w-4 text-kaizen-800" />
                <span>Últimos Cobros Recibidos (Auditoría Reciente)</span>
              </h4>
              <p className="text-[11px] text-tinta-suave">
                Monitoreo en vivo de pagos ingresados por cajeros y operadores
              </p>
            </div>
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[10px] font-semibold text-tinta">
              {cobros.length} registros
            </span>
          </div>

          {cargandoCobros ? (
            <SkeletonTabla filas={5} columnas={5} />
          ) : cobros.length === 0 ? (
            <div className="py-8 text-center text-xs text-tinta-suave italic">
              No hay cobros registrados en el sistema recientemente.
            </div>
          ) : (
            <div className="space-y-3">
              <BuscadorTabla
                valor={busquedaCobros}
                alCambiar={setBusquedaCobros}
                placeholder="Buscar por recibo, cliente, método, operador o monto..."
                conteoFiltrado={cobrosFiltrados.length}
                conteoTotal={cobros.length}
              />

              {cobrosFiltrados.length === 0 ? (
                <div className="rounded-lg border border-dashed border-borde p-6 text-center text-xs text-tinta-suave">
                  No se encontraron cobros que coincidan con &ldquo;{busquedaCobros}&rdquo;.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="border-b bg-slate-50 text-[10px] font-bold text-tinta-suave uppercase">
                      <tr>
                        <th className="py-2 px-2">Recibo</th>
                        <th>Cliente</th>
                        <th>Monto USD / VES</th>
                        <th>Método</th>
                        <th>Operador</th>
                        <th className="text-right px-2">Recibo</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {cobrosFiltrados.map((c) => (
                        <tr key={c.id} className="hover:bg-slate-50 transition">
                          <td className="py-2.5 px-2">
                            <span className="font-bold text-kaizen-900">{c.numero_recibo}</span>
                            <span className="block text-[10px] text-tinta-suave">{c.fecha} {c.hora}</span>
                          </td>
                          <td className="font-medium text-kaizen-900 max-w-[140px] truncate" title={c.cliente}>
                            {c.cliente}
                          </td>
                          <td className="tabular-nums">
                            <span className="font-bold text-verde-trazo block">
                              {formatearDinero(c.monto_usd)}
                            </span>
                            <span className="text-[10px] text-tinta-suave">
                              Bs. {c.monto_ves.toLocaleString("es-VE", { minimumFractionDigits: 2 })}
                            </span>
                          </td>
                          <td>
                            <span className="inline-block rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-tinta">
                              {c.metodo}
                            </span>
                          </td>
                          <td className="text-tinta-suave text-[11px]">{c.cajero}</td>
                          <td className="text-right px-2">
                            <button
                              type="button"
                              disabled={descargandoId === c.id}
                              onClick={() => void manejarDescargaRecibo(c.id)}
                              className="inline-flex items-center gap-1 rounded border border-kaizen-200 bg-kaizen-50 px-2 py-1 text-[10px] font-bold text-kaizen-800 hover:bg-kaizen-100 transition disabled:opacity-50"
                            >
                              {descargandoId === c.id ? <Girador /> : <IconoDescargar className="h-3 w-3" />}
                              <span>PDF</span>
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </section>

        {/* Tabla B: Próximos Vencimientos / Alertas de Cobro Preventivo */}
        <section className="rounded-xl border border-borde bg-white p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-borde pb-3">
            <div>
              <h4 className="text-xs font-bold text-kaizen-900 uppercase tracking-wider flex items-center gap-2">
                <IconoAlerta className="h-4 w-4 text-amber-600" />
                <span>Próximos Vencimientos y Alertas de Cobro</span>
              </h4>
              <p className="text-[11px] text-tinta-suave">
                Clientes prioritarios para gestión preventiva o cobro inmediato
              </p>
            </div>
            <span className="rounded-full bg-amber-50 px-2.5 py-0.5 text-[10px] font-bold text-amber-700 border border-amber-200">
              Prioridad
            </span>
          </div>

          {cargandoAlertas ? (
            <SkeletonTabla filas={5} columnas={5} />
          ) : alertas.length === 0 ? (
            <div className="py-8 text-center text-xs text-tinta-suave italic">
              No hay alertas de cobro pendientes: todas las cuotas están al día.
            </div>
          ) : (
            <div className="space-y-3">
              <BuscadorTabla
                valor={busquedaAlertas}
                alCambiar={setBusquedaAlertas}
                placeholder="Buscar por cliente, código, teléfono, estado..."
                conteoFiltrado={alertasFiltradas.length}
                conteoTotal={alertas.length}
              />

              {alertasFiltradas.length === 0 ? (
                <div className="rounded-lg border border-dashed border-borde p-6 text-center text-xs text-tinta-suave">
                  No se encontraron alertas que coincidan con &ldquo;{busquedaAlertas}&rdquo;.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="border-b bg-slate-50 text-[10px] font-bold text-tinta-suave uppercase">
                      <tr>
                        <th className="py-2 px-2">Cliente / Teléfono</th>
                        <th>Vencimiento</th>
                        <th>Cuota</th>
                        <th className="text-right px-2">Acción</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {alertasFiltradas.map((a) => (
                        <tr key={`${a.tipo_expediente}-${a.expediente_id}-${a.periodo}`} className="hover:bg-slate-50 transition">
                          <td className="py-2.5 px-2">
                            <span className="font-bold text-kaizen-900 block max-w-[150px] truncate" title={a.cliente}>
                              {a.cliente}
                            </span>
                            <div className="flex items-center gap-1.5 text-[10px] text-tinta-suave mt-0.5">
                              <span className="inline-flex items-center gap-1">
                                <IconoTelefono className="h-3 w-3 text-tinta-suave" />
                                {a.telefono || "S/T"}
                              </span>
                              <span>•</span>
                              <span className="font-mono">{a.codigo_credito}</span>
                            </div>
                          </td>
                          <td>
                            <Insignia
                              tono={a.estado_alerta === "vencido" ? "rojo" : a.estado_alerta === "hoy" ? "ambar" : "verde"}
                              texto={a.dias_texto}
                            />
                            <span className="block text-[10px] text-tinta-suave mt-0.5 tabular-nums">
                              {formatearFecha(a.fecha_pago)} (Cuota #{a.periodo})
                            </span>
                          </td>
                          <td className="font-bold tabular-nums text-kaizen-900">
                            {formatearDinero(a.cuota)}
                          </td>
                          <td className="text-right px-2">
                            <div className="flex items-center justify-end gap-1.5">
                              {a.telefono && a.telefono !== "No registrado" && (
                                <a
                                  href={`tel:${a.telefono}`}
                                  title="Llamar al cliente"
                                  className="rounded border border-slate-200 bg-slate-50 p-1.5 text-xs text-tinta hover:bg-slate-100 transition inline-flex items-center justify-center"
                                >
                                  <IconoTelefono className="h-3 w-3" />
                                </a>
                              )}
                              <button
                                type="button"
                                onClick={() => alIrACaja(a.expediente_id, a.tipo_expediente)}
                                className="inline-flex items-center gap-1 rounded bg-kaizen-800 px-2.5 py-1 text-[11px] font-bold text-white hover:bg-kaizen-900 transition"
                              >
                                <span>Cobrar</span>
                                <IconoFlechaDerecha className="h-3 w-3" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
