"use client";

import { useState, useMemo } from "react";
import type { TipoExpediente } from "@/types/api";
import {
  useHistorialPagos,
  useResumenFinanciero,
  descargarReciboPdf,
  type MetodoPagoPayload,
  type ResumenFinanciero,
} from "@/hooks/useCobranzas";
import { Girador, SkeletonTabla } from "@/components/ui/Skeleton";
import { SinResultados } from "@/components/ui/Alerta";
import { useAvisos } from "@/components/ui/Toast";
import { guardarComo } from "@/utils/descargas";
import { ApiError } from "@/utils/apiClient";
import { formatearDinero, formatearFecha } from "@/utils/format";
import { IconoDescargar, IconoDocumento } from "@/components/ui/Iconos";
import { ResumenProgresoCredito } from "@/components/cobranza/ResumenProgresoCredito";
import { BuscadorTabla } from "@/components/ui/BuscadorTabla";

interface Props {
  tipo: TipoExpediente | null;
  expId: number | null;
  resumen?: ResumenFinanciero | null;
}

export function HistorialCobros({ tipo, expId, resumen: resumenProp }: Props) {
  const { pagos, cargando: cargandoPagos, recargar: recargarPagos } = useHistorialPagos(tipo, expId);
  const { resumen: resumenCargado, cargando: cargandoResumen, recargar: recargarResumen } = useResumenFinanciero(
    resumenProp ? null : tipo,
    resumenProp ? null : expId,
  );
  const resumenEfectivo = resumenProp || resumenCargado;

  const { notificar, notificarError } = useAvisos();
  const [descargandoId, setDescargandoId] = useState<number | null>(null);
  const [busqueda, setBusqueda] = useState("");

  const pagosFiltrados = useMemo(() => {
    if (!busqueda.trim()) return pagos;
    const q = busqueda.toLowerCase().trim();
    return pagos.filter((p) => {
      const rec = String(p.numero_recibo || "").toLowerCase();
      const fec = String(p.fecha_pago || "").toLowerCase();
      const caj = String(p.cajero || "").toLowerCase();
      const mon = String(p.monto || "").toLowerCase();
      const monVes = String(p.monto_ves || "").toLowerCase();
      const metodosStr = JSON.stringify(p.metodos || []).toLowerCase();
      return (
        rec.includes(q) ||
        fec.includes(q) ||
        caj.includes(q) ||
        mon.includes(q) ||
        monVes.includes(q) ||
        metodosStr.includes(q)
      );
    });
  }, [pagos, busqueda]);

  const manejarDescarga = async (pagoId: number) => {
    setDescargandoId(pagoId);
    try {
      const archivo = await descargarReciboPdf(pagoId);
      guardarComo(archivo);
      notificar("exito", "Recibo descargado", `El comprobante #${pagoId} se descargó correctamente.`);
    } catch (err: unknown) {
      notificarError(
        err instanceof ApiError ? err : new ApiError(0, "No se pudo descargar el recibo."),
      );
    } finally {
      setDescargandoId(null);
    }
  };

  const recargarTodo = () => {
    recargarPagos();
    recargarResumen();
  };

  if (!tipo || !expId) {
    return (
      <div className="rounded-xl border border-borde bg-white p-6 shadow-sm text-center text-xs text-tinta-suave">
        Seleccione un crédito en el buscador o en la lista de cobro para consultar su historial de amortización y pagos.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ── 1. Resumen de Progreso: Dinero que falta, Cuotas cubiertas y Meses del crédito ── */}
      {cargandoResumen ? (
        <div className="rounded-xl border border-borde bg-white p-6 text-center">
          <Girador />
          <p className="mt-2 text-xs text-tinta-suave">Cargando datos de amortización del crédito...</p>
        </div>
      ) : resumenEfectivo ? (
        <ResumenProgresoCredito resumen={resumenEfectivo} />
      ) : null}

      {/* ── 2. Registro Cronológico de Pagos y Recibos Oficiales ───────── */}
      <section className="rounded-xl border border-borde bg-white p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-borde pb-3">
          <div>
            <h3 className="text-sm font-bold text-kaizen-900 flex items-center gap-2">
              <IconoDocumento className="h-4 w-4 text-kaizen-800" />
              <span>Bitácora de Recibos y Pagos Aplicados</span>
            </h3>
            <p className="mt-0.5 text-xs text-tinta-suave">
              Historial de cobranzas procesadas en ventanilla y caja mixta con comprobantes PDF descargables.
            </p>
          </div>
          <button
            type="button"
            onClick={recargarTodo}
            className="rounded border border-borde px-2.5 py-1 text-xs font-semibold text-tinta hover:bg-slate-50 transition"
          >
            Actualizar
          </button>
        </div>

        {cargandoPagos ? (
          <SkeletonTabla filas={4} />
        ) : pagos.length === 0 ? (
          <SinResultados mensaje="No se han registrado pagos para este crédito aún." />
        ) : (
          <div className="space-y-3">
            <div className="w-full sm:max-w-md">
              <BuscadorTabla
                valor={busqueda}
                alCambiar={setBusqueda}
                placeholder="Buscar por recibo, fecha, método, cajero o monto..."
                conteoFiltrado={pagosFiltrados.length}
                conteoTotal={pagos.length}
              />
            </div>

            {pagosFiltrados.length === 0 ? (
              <div className="rounded-lg border border-dashed border-borde p-6 text-center text-xs text-tinta-suave">
                No se encontraron recibos o pagos que coincidan con &ldquo;{busqueda}&rdquo;.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b text-tinta-suave uppercase font-semibold">
                    <tr>
                      <th className="py-2.5">Recibo</th>
                      <th>Fecha</th>
                      <th>Monto USD</th>
                      <th>Equivalente VES</th>
                      <th>Métodos / Referencias</th>
                      <th>Cajero</th>
                      <th className="text-right">Comprobante</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {pagosFiltrados.map((p) => {
                  const pagoId = Number(p.id);
                  const metodos = Array.isArray(p.metodos) ? p.metodos : [];
                  const estaDescargando = descargandoId === pagoId;

                  return (
                    <tr key={pagoId} className="hover:bg-slate-50">
                      <td className="py-2.5 font-bold text-kaizen-900">{p.numero_recibo as string}</td>
                      <td>{formatearFecha(p.fecha_pago as string)}</td>
                      <td className="tabular-nums font-bold text-verde-trazo">
                        {formatearDinero(Number(p.monto))}
                      </td>
                      <td className="tabular-nums text-tinta-suave">
                        Bs. {Number(p.monto_ves || 0).toLocaleString("es-VE", { minimumFractionDigits: 2 })}
                      </td>
                      <td>
                        <div className="flex flex-wrap gap-1">
                          {metodos.map((m: MetodoPagoPayload, idx: number) => (
                            <span
                              key={idx}
                              className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-tinta font-medium"
                            >
                              {m.tipo?.toUpperCase()}: {m.referencia || m.lote || `${m.monto} ${m.moneda}`}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="text-tinta-suave">{(p.cajero as string) || "Caja"}</td>
                      <td className="text-right">
                        <button
                          type="button"
                          disabled={estaDescargando}
                          onClick={() => void manejarDescarga(pagoId)}
                          className="inline-flex items-center gap-1.5 rounded border border-kaizen-200 bg-kaizen-50 px-2.5 py-1 text-[11px] font-semibold text-kaizen-800 hover:bg-kaizen-100 disabled:opacity-50"
                        >
                          {estaDescargando ? <Girador /> : <IconoDescargar className="h-3.5 w-3.5" />}
                          <span>{estaDescargando ? "Descargando…" : "Recibo PDF"}</span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    )}
  </section>
</div>
);
}
