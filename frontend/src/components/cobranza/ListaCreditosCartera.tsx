"use client";

import { useState, useMemo } from "react";
import { useCreditosCartera, type CreditoEncontrado } from "@/hooks/useCobranzas";
import { formatearDinero, textoOGuion } from "@/utils/format";
import {
  IconoBuscador,
  IconoTarjeta,
  IconoChevronLeft,
  IconoChevronRight,
  IconoRefrescar,
  IconoCheck,
} from "@/components/ui/Iconos";
import { Girador } from "@/components/ui/Skeleton";

interface Props {
  alSeleccionarCredito: (credito: CreditoEncontrado) => void;
  creditoSeleccionadoId?: number | null;
  filtroExterno?: string;
  alIrAPagados?: () => void;
}

const ITEMS_POR_PAGINA = 5;

export function ListaCreditosCartera({
  alSeleccionarCredito,
  creditoSeleccionadoId,
  filtroExterno = "",
  alIrAPagados,
}: Props) {
  const [filtroInterno, setFiltroInterno] = useState("");
  const [filtroEstado, setFiltroEstado] = useState<"activos" | "pagados" | "todos">("activos");
  const [paginaActual, setPaginaActual] = useState(1);

  // Usamos el hook de cartera que obtiene los créditos aprobados por el comité
  const { creditos, cargando, recargar } = useCreditosCartera(filtroExterno);

  // Conteo de activos vs pagados
  const { countActivos, countPagados } = useMemo(() => {
    let act = 0;
    let pag = 0;
    creditos.forEach((c) => {
      if (c.estado_cobranza === "Pagado" || c.saldo_capital <= 0.01) {
        pag++;
      } else {
        act++;
      }
    });
    return { countActivos: act, countPagados: pag };
  }, [creditos]);

  // Filtrado local en memoria
  const creditosFiltrados = useMemo(() => {
    let list = creditos;
    if (filtroEstado === "activos") {
      list = list.filter((c) => c.estado_cobranza !== "Pagado" && c.saldo_capital > 0.01);
    } else if (filtroEstado === "pagados") {
      list = list.filter((c) => c.estado_cobranza === "Pagado" || c.saldo_capital <= 0.01);
    }

    const q = filtroInterno.trim().toLowerCase();
    if (!q) return list;
    return list.filter((c) => {
      const matchCliente = c.cliente?.toLowerCase().includes(q);
      const matchDoc = c.documento?.toLowerCase().includes(q);
      const matchCodigo = c.codigo_credito?.toLowerCase().includes(q);
      return matchCliente || matchDoc || matchCodigo;
    });
  }, [creditos, filtroEstado, filtroInterno]);

  // Cálculo de Paginación exacta en bloques de 5
  const totalItems = creditosFiltrados.length;
  const totalPaginas = Math.max(1, Math.ceil(totalItems / ITEMS_POR_PAGINA));
  const paginaValida = Math.min(Math.max(1, paginaActual), totalPaginas);

  const itemsPagina = useMemo(() => {
    const inicio = (paginaValida - 1) * ITEMS_POR_PAGINA;
    return creditosFiltrados.slice(inicio, inicio + ITEMS_POR_PAGINA);
  }, [creditosFiltrados, paginaValida]);

  const indiceInicio = totalItems === 0 ? 0 : (paginaValida - 1) * ITEMS_POR_PAGINA + 1;
  const indiceFin = Math.min(paginaValida * ITEMS_POR_PAGINA, totalItems);

  const cambiarPagina = (nuevaPagina: number) => {
    if (nuevaPagina >= 1 && nuevaPagina <= totalPaginas) {
      setPaginaActual(nuevaPagina);
    }
  };

  const manejarCambioFiltro = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFiltroInterno(e.target.value);
    setPaginaActual(1);
  };

  return (
    <section className="rounded-xl border border-borde bg-white shadow-sm overflow-hidden">
      {/* Cabecera del Panel de Créditos de Cartera */}
      <div className="border-b border-borde p-4 sm:p-5 bg-slate-50/50">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-kaizen-900">
                Créditos Aprobados por Comité Disponibles para Cobro
              </h3>
              <span className="rounded-full bg-kaizen-100 px-2.5 py-0.5 text-xs font-semibold text-kaizen-800">
                {totalItems} en cartera
              </span>
            </div>
            <p className="mt-0.5 text-xs text-tinta-suave">
              Mostrando exclusivamente expedientes aprobados por el Comité de Crédito. Seleccione uno para procesar caja mixta.
            </p>

            {/* Selector de Estado: Activos con saldo vs Pagados */}
            <div className="mt-2.5 flex flex-wrap items-center gap-2">
              <div className="inline-flex items-center rounded-lg border border-borde bg-white p-0.5 text-[11px]">
                <button
                  type="button"
                  onClick={() => {
                    setFiltroEstado("activos");
                    setPaginaActual(1);
                  }}
                  className={`px-2.5 py-1 rounded-md font-semibold transition ${
                    filtroEstado === "activos"
                      ? "bg-kaizen-900 text-white shadow-xs"
                      : "text-tinta-suave hover:text-kaizen-900"
                  }`}
                >
                  Con Saldo Activo ({countActivos})
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setFiltroEstado("pagados");
                    setPaginaActual(1);
                  }}
                  className={`px-2.5 py-1 rounded-md font-semibold transition ${
                    filtroEstado === "pagados"
                      ? "bg-emerald-800 text-white shadow-xs"
                      : "text-tinta-suave hover:text-emerald-800"
                  }`}
                >
                  Pagados / Solventes ({countPagados})
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setFiltroEstado("todos");
                    setPaginaActual(1);
                  }}
                  className={`px-2.5 py-1 rounded-md font-semibold transition ${
                    filtroEstado === "todos"
                      ? "bg-kaizen-900 text-white shadow-xs"
                      : "text-tinta-suave hover:text-kaizen-900"
                  }`}
                >
                  Todos ({creditos.length})
                </button>
              </div>

              {alIrAPagados && countPagados > 0 && (
                <button
                  type="button"
                  onClick={alIrAPagados}
                  className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-800 hover:text-emerald-950 underline underline-offset-2"
                >
                  <span>Ir a la sección de Créditos Pagados →</span>
                </button>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto">
            {/* Buscador Rápido Local */}
            <div className="relative">
              <input
                type="text"
                value={filtroInterno}
                onChange={manejarCambioFiltro}
                placeholder="Filtrar por nombre, RIF o código..."
                className="w-56 sm:w-64 rounded-lg border border-borde bg-white pl-8 pr-3 py-1.5 text-xs text-tinta placeholder:text-tinta-suave outline-none focus:border-kaizen-600 focus:ring-1 focus:ring-kaizen-600"
              />
              <IconoBuscador className="absolute left-2.5 top-2 h-3.5 w-3.5 text-tinta-suave" />
              {filtroInterno && (
                <button
                  type="button"
                  onClick={() => {
                    setFiltroInterno("");
                    setPaginaActual(1);
                  }}
                  className="absolute right-2.5 top-1.5 text-xs text-tinta-suave hover:text-kaizen-900"
                >
                  ✕
                </button>
              )}
            </div>

            <button
              type="button"
              onClick={() => recargar()}
              title="Refrescar créditos de cartera"
              className="rounded-lg border border-borde bg-white p-2 text-tinta-suave hover:text-kaizen-900 hover:bg-slate-100 transition shadow-xs"
            >
              <IconoRefrescar className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Contenido: Tabla o Estados de Carga/Vacío */}
      {cargando ? (
        <div className="p-8 text-center space-y-3">
          <Girador />
          <p className="text-xs text-tinta-suave">Cargando créditos aprobados por el comité...</p>
        </div>
      ) : totalItems === 0 ? (
        <div className="p-10 text-center space-y-2">
          <IconoBuscador className="h-7 w-7 text-tinta-suave mx-auto" />
          <p className="text-sm font-semibold text-kaizen-900">
            {filtroInterno ? "No se encontraron créditos con ese filtro" : "No hay créditos aprobados en cartera"}
          </p>
          <p className="text-xs text-tinta-suave max-w-md mx-auto">
            {filtroInterno
              ? "Verifique el término ingresado o limpie la búsqueda para ver todos los créditos de la cartera."
              : "Los créditos ingresarán automáticamente a esta sección una vez que hayan recibido dictamen APROBADO por el Comité de Crédito."}
          </p>
        </div>
      ) : (
        <>
          {/* Tabla de Créditos Aprobados */}
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-borde bg-slate-50 text-kaizen-900 font-semibold uppercase tracking-wider text-[11px]">
                  <th className="py-3 px-4">Código / Tipo</th>
                  <th className="py-3 px-4">Cliente / Titular</th>
                  <th className="py-3 px-4">C.I. / RIF</th>
                  <th className="py-3 px-4 text-right">Monto Aprobado</th>
                  <th className="py-3 px-4 text-right">Saldo Capital</th>
                  <th className="py-3 px-4 text-center">Cuotas</th>
                  <th className="py-3 px-4 text-center">Estado</th>
                  <th className="py-3 px-4 text-center">Acción</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-borde">
                {itemsPagina.map((c) => {
                  const estaSeleccionado = creditoSeleccionadoId === c.id;
                  const esPagado = c.estado_cobranza === "Pagado" || c.saldo_capital <= 0.01;
                  const esAlDia = c.estado_cobranza === "Al día" || esPagado;

                  return (
                    <tr
                      key={`${c.tipo}-${c.id}`}
                      className={`transition ${
                        estaSeleccionado
                          ? "bg-kaizen-50/80 font-medium"
                          : esPagado
                          ? "bg-emerald-50/30 hover:bg-emerald-50/60"
                          : "hover:bg-slate-50/70"
                      }`}
                    >
                      {/* Código y Tipo */}
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-kaizen-900 font-mono">{c.codigo_credito}</span>
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
                          Aprobado {c.fecha ? c.fecha.slice(0, 10) : "Comité"}
                        </div>
                      </td>

                      {/* Documento */}
                      <td className="py-3 px-4 text-tinta font-mono text-[11px]">
                        {textoOGuion(c.documento)}
                      </td>

                      {/* Monto Aprobado */}
                      <td className="py-3 px-4 text-right tabular-nums text-tinta">
                        {formatearDinero(c.monto)}
                      </td>

                      {/* Saldo Capital */}
                      <td className="py-3 px-4 text-right tabular-nums font-bold text-kaizen-900">
                        {esPagado ? (
                          <span className="text-emerald-700 font-bold">$ 0.00</span>
                        ) : (
                          formatearDinero(c.saldo_capital)
                        )}
                      </td>

                      {/* Cuotas */}
                      <td className="py-3 px-4 text-center tabular-nums text-tinta-suave">
                        {esPagado ? (
                          <span className="font-bold text-emerald-700">
                            {c.plazo_meses}/{c.plazo_meses}
                          </span>
                        ) : (
                          <>
                            <span className="font-semibold text-tinta">{c.cuotas_pendientes}</span>
                            <span className="text-[10px]">/{c.plazo_meses}</span>
                          </>
                        )}
                      </td>

                      {/* Estado */}
                      <td className="py-3 px-4 text-center">
                        <span
                          className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                            esPagado
                              ? "bg-emerald-100 text-emerald-800 border border-emerald-300 font-bold"
                              : esAlDia
                              ? "bg-verde-fondo text-verde-trazo border border-verde-trazo/20"
                              : "bg-rojo-fondo text-rojo-trazo border border-rojo-trazo/20"
                          }`}
                        >
                          {esPagado ? "✓ Pagado" : c.estado_cobranza || "Al día"}
                        </span>
                      </td>

                      {/* Botón de Selección / Cobro */}
                      <td className="py-3 px-4 text-center">
                        {esPagado ? (
                          alIrAPagados ? (
                            <button
                              type="button"
                              onClick={alIrAPagados}
                              className="inline-flex items-center gap-1 rounded-lg border border-emerald-300 bg-emerald-50 px-2.5 py-1.5 text-xs font-semibold text-emerald-800 hover:bg-emerald-600 hover:text-white transition shadow-xs"
                              title="Ver constancia de finiquito y solvencia"
                            >
                              <IconoCheck className="h-3.5 w-3.5" />
                              <span>Ver Solvencia</span>
                            </button>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-800">
                              <IconoCheck className="h-3.5 w-3.5" />
                              <span>Solvente</span>
                            </span>
                          )
                        ) : (
                          <button
                            type="button"
                            onClick={() => alSeleccionarCredito(c)}
                            className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                              estaSeleccionado
                                ? "bg-kaizen-900 text-white shadow-sm ring-2 ring-kaizen-700/20"
                                : "border border-kaizen-800/30 bg-white text-kaizen-900 hover:bg-kaizen-800 hover:text-white"
                            }`}
                          >
                            {estaSeleccionado ? (
                              <>
                                <IconoCheck className="h-3.5 w-3.5" />
                                <span>En Caja</span>
                              </>
                            ) : (
                              <>
                                <IconoTarjeta className="h-3.5 w-3.5" />
                                <span>Cobrar</span>
                              </>
                            )}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Barra de Paginación de 5 en 5 */}
          <div className="border-t border-borde px-4 py-3 bg-slate-50/50 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-xs text-tinta-suave">
            <div>
              Mostrando <span className="font-semibold text-kaizen-900">{indiceInicio}</span> a{" "}
              <span className="font-semibold text-kaizen-900">{indiceFin}</span> de{" "}
              <span className="font-semibold text-kaizen-900">{totalItems}</span> créditos (5 por página)
            </div>

            <div className="flex items-center gap-1 self-end sm:self-auto">
              <button
                type="button"
                onClick={() => cambiarPagina(paginaValida - 1)}
                disabled={paginaValida <= 1}
                className="inline-flex items-center gap-1 rounded border border-borde bg-white px-2.5 py-1 text-xs font-semibold text-tinta hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed transition"
              >
                <IconoChevronLeft className="h-3.5 w-3.5" />
                <span>Anterior</span>
              </button>

              {/* Botones numéricos de página */}
              <div className="flex items-center gap-1 px-1">
                {Array.from({ length: totalPaginas }, (_, i) => i + 1).map((num) => (
                  <button
                    key={num}
                    type="button"
                    onClick={() => cambiarPagina(num)}
                    className={`min-w-[26px] h-[26px] rounded text-xs font-semibold transition ${
                      num === paginaValida
                        ? "bg-kaizen-800 text-white"
                        : "border border-borde bg-white text-tinta hover:bg-slate-100"
                    }`}
                  >
                    {num}
                  </button>
                ))}
              </div>

              <button
                type="button"
                onClick={() => cambiarPagina(paginaValida + 1)}
                disabled={paginaValida >= totalPaginas}
                className="inline-flex items-center gap-1 rounded border border-borde bg-white px-2.5 py-1 text-xs font-semibold text-tinta hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed transition"
              >
                <span>Siguiente</span>
                <IconoChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
