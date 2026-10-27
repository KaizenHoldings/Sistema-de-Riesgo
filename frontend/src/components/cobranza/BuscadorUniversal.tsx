"use client";

import { useState } from "react";
import { buscarCreditos, type CreditoEncontrado, type TasaCambio } from "@/hooks/useCobranzas";
import { Girador } from "@/components/ui/Skeleton";
import { formatearDinero, textoOGuion } from "@/utils/format";
import { IconoBuscador, IconoCheck } from "@/components/ui/Iconos";

interface Props {
  tasaCambio: TasaCambio;
  monedaPago: "USD" | "VES" | "COP";
  alCambiarMoneda: (moneda: "USD" | "VES" | "COP") => void;
  alSeleccionarCredito: (credito: CreditoEncontrado) => void;
  creditoSeleccionadoId?: number | null;
}

export function BuscadorUniversal({
  tasaCambio,
  monedaPago,
  alCambiarMoneda,
  alSeleccionarCredito,
  creditoSeleccionadoId,
}: Props) {
  const [query, setQuery] = useState("");
  const [buscando, setBuscando] = useState(false);
  const [resultados, setResultados] = useState<CreditoEncontrado[]>([]);
  const [yaBusco, setYaBusco] = useState(false);

  const manejarBusqueda = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    setBuscando(true);
    setYaBusco(true);
    try {
      const res = await buscarCreditos(query.trim());
      setResultados(res);
    } catch {
      setResultados([]);
    } finally {
      setBuscando(false);
    }
  };

  return (
    <section className="rounded-xl border border-borde bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 className="text-sm font-bold text-kaizen-900 flex items-center gap-2">
            <IconoBuscador className="h-4 w-4 text-kaizen-800" />
            <span>Búsqueda Universal de Cartera y Parámetros</span>
          </h2>
          <p className="mt-0.5 text-xs text-tinta-suave">
            Localice clientes por Cédula, RIF, nombre completo, número de contrato o código de crédito.
          </p>
        </div>

        {/* Parámetros de Moneda y Tasa del Día */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 rounded-lg border border-borde bg-kaizen-50/60 px-3 py-1.5">
            <label className="text-xs font-semibold text-kaizen-900">Moneda:</label>
            <select
              value={monedaPago}
              onChange={(e) => alCambiarMoneda(e.target.value as "USD" | "VES" | "COP")}
              className="rounded bg-white px-2 py-0.5 text-xs font-bold text-kaizen-900 outline-none border border-kaizen-200"
            >
              <option value="USD">USD ($)</option>
              <option value="VES">VES (Bs.)</option>
              <option value="COP">COP (Pesos)</option>
            </select>
          </div>

          <div
            className="flex items-center gap-2 rounded-lg border border-verde-trazo/30 bg-verde-fondo px-3 py-1.5 text-xs"
            title="Tasa oficial conectada al Banco Central de Venezuela. Inmodificable por el cajero."
          >
            <span className="flex h-2 w-2 rounded-full bg-verde-trazo"></span>
            <span className="font-semibold text-verde-trazo">Tasa Oficial BCV:</span>
            <span className="font-bold text-kaizen-900 tabular-nums">
              {tasaCambio.USD_VES.toFixed(2)} VES/USD
            </span>
            <span className="text-[10px] text-tinta-suave uppercase font-semibold">
              (Fijada)
            </span>
          </div>
        </div>
      </div>

      {/* Barra de Búsqueda */}
      <form onSubmit={manejarBusqueda} className="mt-4 flex gap-2">
        <div className="relative flex-1">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ingrese Cédula, RIF (ej. J-12345678), nombre del cliente o código de crédito..."
            className="w-full rounded-lg border border-borde bg-white px-3.5 py-2 text-sm text-tinta placeholder:text-tinta-suave outline-none focus:border-kaizen-600 focus:ring-2 focus:ring-kaizen-600/20"
          />
          {query && (
            <button
              type="button"
              onClick={() => {
                setQuery("");
                setResultados([]);
                setYaBusco(false);
              }}
              className="absolute right-3 top-2.5 text-xs text-tinta-suave hover:text-kaizen-900"
            >
              ✕
            </button>
          )}
        </div>
        <button
          type="submit"
          disabled={buscando || !query.trim()}
          className="inline-flex items-center gap-2 rounded-lg bg-kaizen-800 px-5 py-2 text-sm font-semibold text-white transition hover:bg-kaizen-900 disabled:opacity-50"
        >
          {buscando ? <Girador /> : <IconoBuscador className="h-4 w-4" />}
          <span>{buscando ? "Buscando…" : "Buscar Crédito"}</span>
        </button>
      </form>

      {/* Resultados de la Búsqueda */}
      {yaBusco && (
        <div className="mt-4 border-t border-borde pt-3">
          {resultados.length === 0 ? (
            <p className="text-xs text-tinta-suave italic py-2">
              No se encontraron créditos registrados con el término «{query}».
            </p>
          ) : (
            <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
              <p className="text-xs font-semibold text-kaizen-800 mb-2">
                {resultados.length} crédito(s) localizado(s):
              </p>
              {resultados.map((c) => {
                const seleccionado = creditoSeleccionadoId === c.id;
                return (
                  <div
                    key={`${c.tipo}-${c.id}`}
                    onClick={() => alSeleccionarCredito(c)}
                    className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-lg border p-3 cursor-pointer transition ${
                      seleccionado
                        ? "border-kaizen-800 bg-kaizen-50 ring-2 ring-kaizen-800/10"
                        : "border-borde hover:border-kaizen-300 hover:bg-slate-50"
                    }`}
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm text-kaizen-900">
                          {c.cliente}
                        </span>
                        <span className="rounded bg-kaizen-100 px-2 py-0.5 text-[10px] font-bold text-kaizen-800 uppercase">
                          {c.codigo_credito}
                        </span>
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                            c.estado_cobranza === "Al día"
                              ? "bg-verde-fondo text-verde-trazo"
                              : "bg-rojo-fondo text-rojo-trazo"
                          }`}
                        >
                          {c.estado_cobranza}
                        </span>
                      </div>
                      <p className="mt-0.5 text-xs text-tinta-suave">
                        Doc: {textoOGuion(c.documento)} · Línea: {c.tipo === "corp" ? "Corporativo" : "Automotriz"} · Monto original: {formatearDinero(c.monto)} · Plazo: {c.plazo_meses} meses
                      </p>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      <div className="text-right">
                        <p className="text-xs text-tinta-suave">Saldo Capital</p>
                        <p className="text-sm font-bold text-kaizen-900 tabular-nums">
                          {formatearDinero(c.saldo_capital)}
                        </p>
                      </div>
                      <button
                        type="button"
                        className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold ${
                          seleccionado
                            ? "bg-kaizen-800 text-white"
                            : "border border-borde bg-white text-tinta hover:bg-kaizen-50"
                        }`}
                      >
                        {seleccionado ? (
                          <>
                            <IconoCheck className="h-3.5 w-3.5" />
                            <span>Seleccionado</span>
                          </>
                        ) : (
                          "Seleccionar"
                        )}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
