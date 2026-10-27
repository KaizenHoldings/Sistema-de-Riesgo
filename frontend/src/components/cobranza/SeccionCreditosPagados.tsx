"use client";

import { useState, useMemo } from "react";
import {
  useCreditosPagados,
  descargarFiniquitoPdf,
  type CreditoPagado,
} from "@/hooks/useCobranzas";
import { ModalFiniquito } from "@/components/cobranza/ModalFiniquito";
import { Girador, SkeletonMetricas, SkeletonTabla } from "@/components/ui/Skeleton";
import { useAvisos } from "@/components/ui/Toast";
import { guardarComo } from "@/utils/descargas";
import { ApiError } from "@/utils/apiClient";
import { formatearDinero, formatearFecha, textoOGuion } from "@/utils/format";
import {
  IconoBuscador,
  IconoCheck,
  IconoDescargar,
  IconoDocumento,
  IconoRefrescar,
  IconoChevronLeft,
  IconoChevronRight,
  IconoBalanza,
  IconoTrending,
} from "@/components/ui/Iconos";

interface Props {
  alVerHistorial?: (id: number, tipo: "corp" | "auto") => void;
}

const ITEMS_POR_PAGINA = 8;

export function SeccionCreditosPagados({ alVerHistorial }: Props) {
  const { resumen, creditos, cargando, recargar } = useCreditosPagados();
  const { notificar, notificarError } = useAvisos();

  const [filtroTexto, setFiltroTexto] = useState("");
  const [filtroTipo, setFiltroTipo] = useState<"todos" | "corp" | "auto">("todos");
  const [paginaActual, setPaginaActual] = useState(1);

  const [creditoModal, setCreditoModal] = useState<CreditoPagado | null>(null);
  const [modalAbierto, setModalAbierto] = useState(false);
  const [descargandoId, setDescargandoId] = useState<number | null>(null);

  // Filtrado reactivo en memoria
  const creditosFiltrados = useMemo(() => {
    let filtrados = creditos;

    if (filtroTipo !== "todos") {
      filtrados = filtrados.filter((c) => c.tipo === filtroTipo);
    }

    if (filtroTexto.trim()) {
      const q = filtroTexto.toLowerCase().trim();
      filtrados = filtrados.filter((c) => {
        const cli = String(c.cliente || "").toLowerCase();
        const doc = String(c.documento || "").toLowerCase();
        const cod = String(c.codigo_credito || "").toLowerCase();
        return cli.includes(q) || doc.includes(q) || cod.includes(q);
      });
    }

    return filtrados;
  }, [creditos, filtroTipo, filtroTexto]);

  // Paginación
  const totalItems = creditosFiltrados.length;
  const totalPaginas = Math.max(1, Math.ceil(totalItems / ITEMS_POR_PAGINA));
  const paginaValida = Math.min(Math.max(1, paginaActual), totalPaginas);

  const itemsPagina = useMemo(() => {
    const inicio = (paginaValida - 1) * ITEMS_POR_PAGINA;
    return creditosFiltrados.slice(inicio, inicio + ITEMS_POR_PAGINA);
  }, [creditosFiltrados, paginaValida]);

  const indiceInicio = totalItems === 0 ? 0 : (paginaValida - 1) * ITEMS_POR_PAGINA + 1;
  const indiceFin = Math.min(paginaValida * ITEMS_POR_PAGINA, totalItems);

  const cambiarPagina = (nueva: number) => {
    if (nueva >= 1 && nueva <= totalPaginas) {
      setPaginaActual(nueva);
    }
  };

  const abrirModalFiniquito = (c: CreditoPagado) => {
    setCreditoModal(c);
    setModalAbierto(true);
  };

  const manejarDescargaDirecta = async (c: CreditoPagado) => {
    setDescargandoId(c.id);
    try {
      const archivo = await descargarFiniquitoPdf(c.id, c.tipo);
      guardarComo(archivo);
      notificar(
        "exito",
        "Solvencia Descargada",
        `Certificado legal de finiquito descargado para ${c.codigo_credito}.`,
      );
    } catch (err: unknown) {
      notificarError(
        err instanceof ApiError
          ? err
          : new ApiError(0, "Error al descargar la constancia de solvencia."),
      );
    } finally {
      setDescargandoId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* ── 1. TARJETAS DE INDICADORES (KPIS DE CRÉDITOS LIQUIDADOS) ───── */}
      {cargando ? (
        <SkeletonMetricas tarjetas={4} />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* KPI 1: Total Créditos Cancelados */}
          <div className="rounded-xl border border-emerald-200 bg-gradient-to-br from-emerald-50/70 to-white p-4 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-emerald-900 uppercase tracking-wide">
                Créditos Finiquitados
              </span>
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-100 text-emerald-700">
                <IconoCheck className="h-4 w-4" />
              </span>
            </div>
            <p className="mt-2 text-2xl font-black text-emerald-950 tabular-nums">
              {resumen.total_creditos_pagados}
            </p>
            <p className="mt-1 text-[11px] text-emerald-800 font-medium">
              100% solventes y sin saldo deudor
            </p>
          </div>

          {/* KPI 2: Capital Recuperado */}
          <div className="rounded-xl border border-borde bg-white p-4 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-kaizen-900 uppercase tracking-wide">
                Capital Recuperado
              </span>
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-kaizen-100 text-kaizen-800">
                <IconoBalanza className="h-4 w-4" />
              </span>
            </div>
            <p className="mt-2 text-2xl font-black text-kaizen-900 tabular-nums">
              {formatearDinero(resumen.monto_total_prestado)}
            </p>
            <p className="mt-1 text-[11px] text-tinta-suave">
              Monto original de créditos liquidados
            </p>
          </div>

          {/* KPI 3: Intereses Percibidos */}
          <div className="rounded-xl border border-borde bg-white p-4 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-kaizen-900 uppercase tracking-wide">
                Intereses Cobrados
              </span>
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-100 text-amber-800">
                <IconoTrending className="h-4 w-4" />
              </span>
            </div>
            <p className="mt-2 text-2xl font-black text-kaizen-900 tabular-nums">
              {formatearDinero(resumen.total_intereses_cobrados)}
            </p>
            <p className="mt-1 text-[11px] text-tinta-suave">
              Rendimiento financiero percibido
            </p>
          </div>

          {/* KPI 4: Total Recaudado en Cartera */}
          <div className="rounded-xl border border-kaizen-800 bg-kaizen-900 p-4 text-white shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wide text-slate-200">
                Total Recaudado
              </span>
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-kaizen-800 text-white">
                <IconoDocumento className="h-4 w-4" />
              </span>
            </div>
            <p className="mt-2 text-2xl font-black text-white tabular-nums">
              {formatearDinero(resumen.monto_total_recaudado)}
            </p>
            <p className="mt-1 text-[11px] text-slate-300">
              Ingreso total consolidado en caja
            </p>
          </div>
        </div>
      )}

      {/* ── 2. SECCIÓN PRINCIPAL: TABLA Y FILTROS DE CRÉDITOS PAGADOS ──── */}
      <section className="rounded-xl border border-borde bg-white shadow-sm overflow-hidden">
        {/* Cabecera y Barra de Filtros */}
        <div className="border-b border-borde p-4 sm:p-5 bg-slate-50/60">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-kaizen-900">
                  Histórico de Créditos Pagados y Solvencias Emitidas
                </h3>
                <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-bold text-emerald-800">
                  {totalItems} liquidados
                </span>
              </div>
              <p className="mt-0.5 text-xs text-tinta-suave">
                Expedientes de cartera que han amortizado el 100% del capital e intereses. Puede consultar su finiquito y descargar el certificado oficial de solvencia.
              </p>
            </div>

            {/* Filtros: Tipo de Cartera, Búsqueda y Refrescar */}
            <div className="flex flex-wrap items-center gap-2.5">
              {/* Filtro por Tipo */}
              <div className="flex items-center rounded-lg border border-borde bg-white p-0.5 text-xs">
                <button
                  type="button"
                  onClick={() => {
                    setFiltroTipo("todos");
                    setPaginaActual(1);
                  }}
                  className={`px-2.5 py-1 rounded-md font-semibold transition ${
                    filtroTipo === "todos"
                      ? "bg-kaizen-900 text-white shadow-xs"
                      : "text-tinta-suave hover:text-kaizen-900"
                  }`}
                >
                  Todos
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setFiltroTipo("corp");
                    setPaginaActual(1);
                  }}
                  className={`px-2.5 py-1 rounded-md font-semibold transition ${
                    filtroTipo === "corp"
                      ? "bg-kaizen-900 text-white shadow-xs"
                      : "text-tinta-suave hover:text-kaizen-900"
                  }`}
                >
                  Corp
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setFiltroTipo("auto");
                    setPaginaActual(1);
                  }}
                  className={`px-2.5 py-1 rounded-md font-semibold transition ${
                    filtroTipo === "auto"
                      ? "bg-kaizen-900 text-white shadow-xs"
                      : "text-tinta-suave hover:text-kaizen-900"
                  }`}
                >
                  Auto
                </button>
              </div>

              {/* Buscador Rápido */}
              <div className="relative">
                <input
                  type="text"
                  value={filtroTexto}
                  onChange={(e) => {
                    setFiltroTexto(e.target.value);
                    setPaginaActual(1);
                  }}
                  placeholder="Buscar cliente, RIF o código..."
                  className="w-56 sm:w-64 rounded-lg border border-borde bg-white pl-8 pr-3 py-1.5 text-xs text-tinta placeholder:text-tinta-suave outline-none focus:border-kaizen-600 focus:ring-1 focus:ring-kaizen-600"
                />
                <IconoBuscador className="absolute left-2.5 top-2 h-3.5 w-3.5 text-tinta-suave" />
                {filtroTexto && (
                  <button
                    type="button"
                    onClick={() => {
                      setFiltroTexto("");
                      setPaginaActual(1);
                    }}
                    className="absolute right-2.5 top-1.5 text-xs text-tinta-suave hover:text-kaizen-900"
                  >
                    ✕
                  </button>
                )}
              </div>

              {/* Botón Refrescar */}
              <button
                type="button"
                onClick={() => recargar()}
                title="Refrescar listado de créditos pagados"
                className="rounded-lg border border-borde bg-white p-2 text-tinta-suave hover:text-kaizen-900 hover:bg-slate-100 transition shadow-xs"
              >
                <IconoRefrescar className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* Contenido: Tabla o Estado Vacío */}
        {cargando ? (
          <div className="p-8">
            <SkeletonTabla filas={4} columnas={7} />
          </div>
        ) : totalItems === 0 ? (
          <div className="p-12 text-center space-y-2">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 mx-auto">
              <IconoCheck className="h-6 w-6" />
            </div>
            <p className="text-sm font-bold text-kaizen-900">
              {filtroTexto ? "No se encontraron créditos pagados con ese filtro" : "Aún no hay créditos finiquitados"}
            </p>
            <p className="text-xs text-tinta-suave max-w-md mx-auto">
              {filtroTexto
                ? "Verifique el término ingresado o limpie la búsqueda para visualizar todos los créditos solventes."
                : "Una vez que los créditos activos en cartera sean cancelados en su totalidad a través de Caja Mixta, ingresarán automáticamente a esta sección con su certificación de solvencia."}
            </p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-borde bg-slate-50 text-kaizen-900 font-semibold uppercase tracking-wider text-[11px]">
                    <th className="py-3 px-4">Código / Tipo</th>
                    <th className="py-3 px-4">Cliente / Titular</th>
                    <th className="py-3 px-4">C.I. / RIF</th>
                    <th className="py-3 px-4 text-right">Monto Original</th>
                    <th className="py-3 px-4 text-right">Total Pagado</th>
                    <th className="py-3 px-4 text-right">Intereses</th>
                    <th className="py-3 px-4 text-center">Cuotas</th>
                    <th className="py-3 px-4 text-center">Liquidación</th>
                    <th className="py-3 px-4 text-center">Estado</th>
                    <th className="py-3 px-4 text-center">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-borde">
                  {itemsPagina.map((c) => (
                    <tr
                      key={`${c.tipo}-${c.id}`}
                      className="hover:bg-slate-50/70 transition"
                    >
                      {/* Código y Tipo */}
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-1.5">
                          <span className="font-bold text-kaizen-900 font-mono">
                            {c.codigo_credito}
                          </span>
                          <span
                            className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
                              c.tipo === "corp"
                                ? "bg-kaizen-100 text-kaizen-800"
                                : "bg-slate-200 text-slate-800"
                            }`}
                          >
                            {c.tipo === "corp" ? "Corp" : "Auto"}
                          </span>
                        </div>
                      </td>

                      {/* Cliente */}
                      <td className="py-3 px-4">
                        <div className="font-semibold text-kaizen-900 truncate max-w-[180px]" title={c.cliente}>
                          {c.cliente}
                        </div>
                        <div className="text-[10px] text-tinta-suave">
                          Aprobado {c.fecha_aprobacion || "Comité"}
                        </div>
                      </td>

                      {/* Documento */}
                      <td className="py-3 px-4 text-tinta font-mono text-[11px]">
                        {textoOGuion(c.documento)}
                      </td>

                      {/* Monto Original */}
                      <td className="py-3 px-4 text-right tabular-nums text-tinta">
                        {formatearDinero(c.monto_original)}
                      </td>

                      {/* Total Pagado */}
                      <td className="py-3 px-4 text-right tabular-nums font-bold text-kaizen-900">
                        {formatearDinero(c.total_pagado)}
                      </td>

                      {/* Intereses Pagados */}
                      <td className="py-3 px-4 text-right tabular-nums text-emerald-800 font-medium">
                        {formatearDinero(c.total_intereses_pagados)}
                      </td>

                      {/* Cuotas */}
                      <td className="py-3 px-4 text-center tabular-nums text-emerald-700 font-semibold">
                        {c.cuotas_pagadas}/{c.cuotas_totales}{" "}
                        <span className="text-[10px] font-bold text-emerald-800">(100%)</span>
                      </td>

                      {/* Fecha de Liquidación */}
                      <td className="py-3 px-4 text-center text-tinta-suave tabular-nums text-[11px]">
                        {formatearFecha(c.fecha_liquidacion)}
                      </td>

                      {/* Estado */}
                      <td className="py-3 px-4 text-center">
                        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-[11px] font-bold text-emerald-800 border border-emerald-300">
                          <IconoCheck className="h-3 w-3" />
                          <span>Solvente</span>
                        </span>
                      </td>

                      {/* Acciones */}
                      <td className="py-3 px-4 text-center">
                        <div className="inline-flex items-center gap-1.5">
                          {/* Botón Ver Finiquito / Certificado */}
                          <button
                            type="button"
                            onClick={() => abrirModalFiniquito(c)}
                            className="inline-flex items-center gap-1 rounded-lg border border-kaizen-800/30 bg-white px-2.5 py-1 text-[11px] font-semibold text-kaizen-900 hover:bg-kaizen-900 hover:text-white transition shadow-xs"
                            title="Ver detalle del finiquito y constancia de solvencia"
                          >
                            <IconoDocumento className="h-3.5 w-3.5" />
                            <span>Finiquito</span>
                          </button>

                          {/* Botón Descarga Rápida PDF */}
                          <button
                            type="button"
                            onClick={() => manejarDescargaDirecta(c)}
                            disabled={descargandoId === c.id}
                            className="inline-flex items-center gap-1 rounded-lg border border-emerald-600/30 bg-emerald-50 px-2 py-1 text-[11px] font-semibold text-emerald-800 hover:bg-emerald-600 hover:text-white transition shadow-xs disabled:opacity-50"
                            title="Descargar Constancia Oficial de Solvencia en PDF"
                          >
                            {descargandoId === c.id ? (
                              <Girador />
                            ) : (
                              <IconoDescargar className="h-3.5 w-3.5" />
                            )}
                            <span>PDF</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Paginador */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-t border-borde p-4 bg-slate-50/40 text-xs">
              <span className="text-tinta-suave">
                Mostrando <strong>{indiceInicio}</strong> a <strong>{indiceFin}</strong> de{" "}
                <strong>{totalItems}</strong> créditos finiquitados
              </span>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => cambiarPagina(paginaValida - 1)}
                  disabled={paginaValida <= 1}
                  className="inline-flex items-center gap-1 rounded-lg border border-borde bg-white px-2.5 py-1 font-medium text-tinta hover:bg-slate-100 disabled:opacity-40 transition"
                >
                  <IconoChevronLeft className="h-3.5 w-3.5" />
                  <span>Anterior</span>
                </button>

                <span className="font-semibold text-kaizen-900 px-1">
                  {paginaValida} / {totalPaginas}
                </span>

                <button
                  type="button"
                  onClick={() => cambiarPagina(paginaValida + 1)}
                  disabled={paginaValida >= totalPaginas}
                  className="inline-flex items-center gap-1 rounded-lg border border-borde bg-white px-2.5 py-1 font-medium text-tinta hover:bg-slate-100 disabled:opacity-40 transition"
                >
                  <span>Siguiente</span>
                  <IconoChevronRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </>
        )}
      </section>

      {/* Modal de Finiquito y Solvencia */}
      <ModalFiniquito
        abierto={modalAbierto}
        alCerrar={() => {
          setModalAbierto(false);
          setCreditoModal(null);
        }}
        credito={creditoModal}
        alVerHistorial={alVerHistorial}
      />
    </div>
  );
}
