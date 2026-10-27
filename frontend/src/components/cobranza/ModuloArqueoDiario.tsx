"use client";

import { useState, useMemo } from "react";
import { useArqueoDiario, descargarReciboPdf } from "@/hooks/useCobranzas";
import { Girador, SkeletonTabla } from "@/components/ui/Skeleton";
import { useAvisos } from "@/components/ui/Toast";
import { guardarComo } from "@/utils/descargas";
import { ApiError } from "@/utils/apiClient";
import { formatearDinero } from "@/utils/format";
import { IconoBalanza, IconoDescargar } from "@/components/ui/Iconos";
import { BuscadorTabla } from "@/components/ui/BuscadorTabla";

export function ModuloArqueoDiario() {
  const hoyStr = new Date().toISOString().slice(0, 10);
  const [fecha, setFecha] = useState(hoyStr);
  const [busqueda, setBusqueda] = useState("");
  const { arqueo, cargando, recargar } = useArqueoDiario(fecha);
  const { notificar, notificarError } = useAvisos();
  const [descargandoId, setDescargandoId] = useState<number | null>(null);

  const transacciones = arqueo?.transacciones || [];
  const totalTransacciones = transacciones.length;

  const transaccionesFiltradas = useMemo(() => {
    if (!busqueda.trim()) return transacciones;
    const q = busqueda.toLowerCase().trim();
    return transacciones.filter(
      (t) =>
        t.recibo.toLowerCase().includes(q) ||
        t.expediente.toLowerCase().includes(q) ||
        t.referencia.toLowerCase().includes(q) ||
        t.cajero.toLowerCase().includes(q) ||
        t.monto_usd.toString().includes(q) ||
        t.monto_ves.toString().includes(q),
    );
  }, [transacciones, busqueda]);

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

  return (
    <section className="rounded-xl border border-borde bg-white p-5 shadow-sm space-y-5">
      {/* ── Encabezado y Selector de Fecha ────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-borde pb-4">
        <div>
          <h3 className="text-sm font-bold text-kaizen-900 flex items-center gap-2">
            <IconoBalanza className="h-4 w-4 text-kaizen-800" />
            <span>Módulo de Arqueo Diario y Cierre de Caja</span>
          </h3>
          <p className="mt-0.5 text-xs text-tinta-suave">
            Listado y auditoría de todas las operaciones y cobros registrados en ventanilla durante la jornada.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold text-tinta-suave">Fecha:</label>
            <input
              type="date"
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
              className="rounded border border-borde bg-white px-2.5 py-1 text-xs text-kaizen-900 outline-none focus:border-kaizen-600"
            />
          </div>

          <button
            type="button"
            onClick={recargar}
            className="rounded border border-borde bg-slate-50 px-2.5 py-1 text-xs font-medium text-kaizen-800 hover:bg-slate-100 transition"
          >
            Actualizar
          </button>
        </div>
      </div>

      {cargando ? (
        <SkeletonTabla filas={4} />
      ) : (
        /* ── Transacciones Registradas en la Jornada ─────────────────────── */
        <div className="space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <h4 className="text-xs font-bold text-kaizen-900 uppercase tracking-wider">
              Transacciones Registradas en la Jornada ({totalTransacciones})
            </h4>

            {totalTransacciones > 0 && (
              <div className="flex items-center gap-3 text-xs text-tinta-suave">
                <span>
                  Total USD:{" "}
                  <strong className="text-verde-trazo font-bold">
                    {formatearDinero(arqueo?.total_usd || 0)}
                  </strong>
                </span>
                <span className="text-slate-300">|</span>
                <span>
                  Total VES:{" "}
                  <strong className="text-kaizen-900 font-bold">
                    Bs. {(arqueo?.total_ves || 0).toLocaleString("es-VE", { minimumFractionDigits: 2 })}
                  </strong>
                </span>
              </div>
            )}
          </div>

          {totalTransacciones > 0 && (
            <div className="w-full sm:max-w-md">
              <BuscadorTabla
                valor={busqueda}
                alCambiar={setBusqueda}
                placeholder="Buscar por recibo, expediente, referencia, cajero o monto..."
                conteoFiltrado={transaccionesFiltradas.length}
                conteoTotal={totalTransacciones}
              />
            </div>
          )}

          {!arqueo?.transacciones || arqueo.transacciones.length === 0 ? (
            <div className="rounded-lg border border-dashed border-borde p-8 text-center text-xs text-tinta-suave">
              No hay cobros registrados en la fecha seleccionada ({fecha}).
            </div>
          ) : transaccionesFiltradas.length === 0 ? (
            <div className="rounded-lg border border-dashed border-borde p-8 text-center text-xs text-tinta-suave">
              No se encontraron transacciones que coincidan con &ldquo;{busqueda}&rdquo;.
            </div>
          ) : (
            <div className="overflow-x-auto border border-borde rounded-lg">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-borde text-tinta-suave uppercase font-semibold">
                  <tr>
                    <th className="p-3">Recibo</th>
                    <th className="p-3">Expediente</th>
                    <th className="p-3">Monto USD</th>
                    <th className="p-3">Equivalente VES</th>
                    <th className="p-3">Métodos / Referencias</th>
                    <th className="p-3">Cajero</th>
                    <th className="p-3 text-center">Comprobante</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {transaccionesFiltradas.map((t) => (
                    <tr key={t.id} className="hover:bg-slate-50 transition">
                      <td className="p-3 font-bold text-kaizen-900">{t.recibo}</td>
                      <td className="p-3 font-medium text-kaizen-800">{t.expediente}</td>
                      <td className="p-3 tabular-nums font-bold text-verde-trazo">
                        {formatearDinero(t.monto_usd)}
                      </td>
                      <td className="p-3 tabular-nums text-tinta-suave">
                        Bs. {t.monto_ves.toLocaleString("es-VE", { minimumFractionDigits: 2 })}
                      </td>
                      <td className="p-3 font-mono text-[11px] text-slate-700">
                        {t.referencia || "—"}
                      </td>
                      <td className="p-3 text-tinta-suave">{t.cajero}</td>
                      <td className="p-3 text-center">
                        <button
                          type="button"
                          disabled={descargandoId === t.id}
                          onClick={() => void manejarDescarga(t.id)}
                          className="inline-flex items-center gap-1.5 rounded border border-borde bg-white px-2.5 py-1 text-[11px] font-semibold text-kaizen-800 hover:bg-kaizen-50 hover:border-kaizen-400 transition disabled:opacity-50"
                        >
                          {descargandoId === t.id ? (
                            <Girador />
                          ) : (
                            <IconoDescargar className="h-3 w-3" />
                          )}
                          <span>Recibo PDF</span>
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
  );
}
