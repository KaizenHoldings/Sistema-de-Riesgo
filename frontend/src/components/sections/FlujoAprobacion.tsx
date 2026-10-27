"use client";

/**
 * Visualizador del Flujo de Aprobación.
 *
 * Muestra el estado del circuito para el expediente. Si el rol es Legal,
 * preserva la confidencialidad no mostrando información ni firmas de Cumplimiento
 * ni Riesgo.
 */

import { useState, useMemo } from "react";
import type { ApprovalWorkflow, EstadoPaso } from "@/business/workflows/types";
import { useSesion } from "@/components/providers/ProveedorSesion";
import { BuscadorTabla } from "@/components/ui/BuscadorTabla";

const ESTILO_PASO: Record<
  EstadoPaso,
  { circulo: string; titulo: string; linea: string; icono: string }
> = {
  completado: {
    circulo: "bg-verde-trazo text-white",
    titulo: "text-kaizen-900",
    linea: "bg-verde-trazo",
    icono: "✓",
  },
  en_curso: {
    circulo: "bg-kaizen-800 text-white ring-4 ring-kaizen-600/20",
    titulo: "text-kaizen-900",
    linea: "bg-borde",
    icono: "●",
  },
  pendiente: {
    circulo: "bg-neutro-fondo text-neutro-trazo",
    titulo: "text-tinta-suave",
    linea: "bg-borde",
    icono: "○",
  },
  rechazado: {
    circulo: "bg-rojo-trazo text-white",
    titulo: "text-rojo-trazo",
    linea: "bg-rojo-trazo",
    icono: "×",
  },
};

export function FlujoAprobacion({ flujo }: { flujo: ApprovalWorkflow }) {
  const { sesion } = useSesion();
  const esLegal = sesion?.rol === "Legal";

  // Para Legal, filtrar o adaptar la descripción de los pasos para no revelar
  // evaluaciones de Cumplimiento ni de Riesgo
  const pasos = flujo.pasos.map((paso) => {
    if (esLegal) {
      if (paso.clave === "cumplimiento") {
        return {
          ...paso,
          titulo: "Validación inicial",
          descripcion: "Revisión documental preliminar del solicitante.",
        };
      }
      if (paso.clave === "credito_legal") {
        return {
          ...paso,
          titulo: "Evaluación Legal",
          descripcion: flujo.firmas.legal
            ? "Evaluación de garantías y contratos firmada."
            : "Revisión de colaterales, redacción de contratos y anexos.",
        };
      }
    }
    return paso;
  });

  const tareas = esLegal
    ? flujo.tareas.filter((t) => {
        const et = t.etapa.toLowerCase();
        return et.includes("legal") || et.includes("comercial");
      })
    : flujo.tareas;

  const [busquedaTareas, setBusquedaTareas] = useState("");
  const tareasFiltradas = useMemo(() => {
    if (!busquedaTareas.trim()) return tareas;
    const q = busquedaTareas.toLowerCase().trim();
    return tareas.filter((t) => {
      const etapa = (t.etapa === "Legal Fase 1" ? "Legal" : t.etapa).toLowerCase();
      const estado = t.estado.toLowerCase();
      return etapa.includes(q) || estado.includes(q);
    });
  }, [tareas, busquedaTareas]);

  return (
    <section
      className="rounded-xl border border-borde bg-white p-5 shadow-sm"
      aria-label="Flujo de aprobación"
    >
      <div className="mb-6 flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="text-sm font-semibold text-kaizen-900">
          Flujo de Aprobación
        </h2>
        <p className="text-xs text-tinta-suave">{flujo.estadoWorkflow}</p>
      </div>

      <ol className="flex flex-col gap-0 md:flex-row md:gap-0">
        {pasos.map((paso, indice) => {
          const estilo = ESTILO_PASO[paso.estado];
          const ultimo = indice === pasos.length - 1;

          return (
            <li key={paso.clave} className="flex flex-1 gap-4 md:flex-col md:gap-0">
              <div className="flex flex-col items-center md:flex-row md:items-center">
                <span
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-bold ${estilo.circulo}`}
                  aria-hidden
                >
                  {estilo.icono}
                </span>
                {!ultimo && (
                  <span
                    className={`w-0.5 flex-1 md:h-0.5 md:w-full ${estilo.linea}`}
                    aria-hidden
                  />
                )}
              </div>

              <div className={ultimo ? "pb-0 md:pt-4 md:pr-4" : "pb-8 md:pt-4 md:pr-4"}>
                <p className={`text-sm font-semibold ${estilo.titulo}`}>
                  {paso.titulo}
                </p>
                <p className="mt-1 text-xs text-tinta-suave">{paso.descripcion}</p>
                {paso.firmadoPor && (
                  <p className="mt-1 text-xs text-tinta-suave">
                    {paso.firmadoPor} · {paso.fecha}
                  </p>
                )}
                <span className="sr-only">
                  Estado: {etiquetaEstado(paso.estado)}
                </span>
              </div>
            </li>
          );
        })}
      </ol>

      <div className={`mt-6 grid grid-cols-1 gap-3 border-t border-borde pt-5 ${esLegal ? "sm:grid-cols-1 max-w-xs" : "sm:grid-cols-3"}`}>
        {!esLegal && <Firma nombre="Cumplimiento" firmada={flujo.firmas.cumplimiento} />}
        <Firma nombre="Legal" firmada={flujo.firmas.legal} />
        {!esLegal && <Firma nombre="Riesgo" firmada={flujo.firmas.riesgo} />}
      </div>

      {tareas.length > 0 && (
        <div className="mt-5 border-t border-borde pt-5 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <h3 className="text-xs font-semibold tracking-wide text-tinta-suave uppercase">
              Tareas del circuito ({tareas.length})
            </h3>
            <div className="w-full sm:max-w-xs">
              <BuscadorTabla
                valor={busquedaTareas}
                alCambiar={setBusquedaTareas}
                placeholder="Buscar tarea o estado..."
                conteoFiltrado={tareasFiltradas.length}
                conteoTotal={tareas.length}
              />
            </div>
          </div>

          {tareasFiltradas.length === 0 ? (
            <div className="rounded-lg border border-dashed border-borde p-6 text-center text-xs text-tinta-suave">
              No se encontraron tareas que coincidan con &ldquo;{busquedaTareas}&rdquo;.
            </div>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-borde">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-borde text-tinta-suave uppercase font-semibold">
                  <tr>
                    <th className="p-2.5">Etapa / Tarea</th>
                    <th className="p-2.5 text-right">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {tareasFiltradas.map((tarea) => {
                    const etapaVisual =
                      tarea.etapa === "Legal Fase 1" ? "Legal" : tarea.etapa;
                    return (
                      <tr key={tarea.id ?? `${tarea.etapa}-${tarea.fecha_creacion}`} className="hover:bg-slate-50 transition">
                        <td className="p-2.5 font-medium text-kaizen-900">{etapaVisual}</td>
                        <td className="p-2.5 text-right">
                          <span
                            className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                              tarea.estado === "PENDIENTE"
                                ? "bg-ambar-fondo text-ambar-trazo"
                                : "bg-verde-fondo text-verde-trazo"
                            }`}
                          >
                            {tarea.estado}
                          </span>
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
  );
}

function Firma({ nombre, firmada }: { nombre: string; firmada: boolean }) {
  return (
    <div
      className={`flex items-center gap-3 rounded-lg border px-4 py-3 ${
        firmada
          ? "border-verde-trazo/30 bg-verde-fondo"
          : "border-borde bg-lienzo"
      }`}
    >
      <span
        className={`h-2.5 w-2.5 rounded-full ${
          firmada ? "bg-verde-trazo" : "bg-neutro-trazo/40"
        }`}
        aria-hidden
      />
      <span className="min-w-0">
        <span className="block text-sm font-semibold text-kaizen-900">{nombre}</span>
        <span
          className={`block text-xs ${
            firmada ? "text-verde-trazo" : "text-tinta-suave"
          }`}
        >
          {firmada ? "Firmada" : "Pendiente"}
        </span>
      </span>
    </div>
  );
}

function etiquetaEstado(estado: EstadoPaso): string {
  if (estado === "completado") return "completado";
  if (estado === "en_curso") return "en curso";
  if (estado === "rechazado") return "rechazado";
  return "pendiente";
}
