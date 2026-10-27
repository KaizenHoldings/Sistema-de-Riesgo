"use client";

/**
 * Columnas comunes de las bandejas de expedientes.
 *
 * Las dos líneas de producto viven en tablas distintas, pero en una bandeja se
 * leen igual: quién pide, cuánto, en qué etapa está y con qué dictamen. Al
 * compartir columnas, el filtro de categoría puede mostrar ambas mezcladas sin
 * que la tabla cambie de forma.
 *
 * Lo propio de cada línea —el RIF de una empresa, el vehículo de un crédito
 * automotriz— se resuelve en la columna «Referencia», que mira la línea de la
 * fila en lugar de duplicar la tabla.
 */

import Link from "next/link";

import type { Columna } from "@/components/ui/Tabla";
import { Firmas, Insignia } from "@/components/ui/Semaforo";
import type { ExpedienteAutomotriz } from "@/types/api";
import { etapaActual, semaforoDictamen, semaforoScore } from "@/utils/estados";
import {
  formatearDinero,
  formatearFecha,
  formatearNumero,
  textoOGuion,
} from "@/utils/format";

import type { FilaExpediente } from "./FiltrosExpedientes";

function referencia(fila: FilaExpediente): string {
  if (fila.linea === "corp") {
    return textoOGuion("rif" in fila ? fila.rif : null);
  }
  const auto = fila as ExpedienteAutomotriz;
  return [auto.marca, auto.modelo, auto.anio].filter(Boolean).join(" ") || "—";
}

/**
 * @param accion Enlace final de cada fila: «Evaluar» abre el circuito, «Ver
 * ficha» solo consulta. El seguimiento comercial no ofrece acciones de circuito.
 */
export function columnasExpedientes(
  accion: "evaluar" | "ficha",
  rol?: string,
): Array<Columna<FilaExpediente>> {
  const esLegal = rol === "Legal";

  const cols: Array<Columna<FilaExpediente>> = [
    {
      clave: "accion",
      encabezado: "",
      celda: (exp) =>
        accion === "evaluar" ? (
          <Link
            href={`/evaluations/${exp.linea}/${exp.id}`}
            className="inline-flex rounded-lg bg-kaizen-800 px-3 py-1.5 text-xs font-semibold whitespace-nowrap text-white transition hover:bg-kaizen-900"
          >
            {exp.dictamen === "PENDIENTE" ? "Evaluar" : "Ver ficha"}
          </Link>
        ) : (
          <Link
            href={`/evaluations/${exp.linea}/${exp.id}`}
            className="inline-flex rounded-lg border border-borde px-3 py-1.5 text-xs font-semibold whitespace-nowrap text-tinta transition hover:border-kaizen-600 hover:text-kaizen-600"
          >
            Ver ficha
          </Link>
        ),
    },
    {
      clave: "id",
      encabezado: "Nº",
      alineacion: "derecha",
      celda: (exp) => (
        <span className="font-mono text-xs text-tinta-suave tabular-nums">
          {exp.id ?? "—"}
        </span>
      ),
    },
    {
      clave: "cliente",
      encabezado: "Cliente",
      anchoMinimo: "15rem",
      celda: (exp) => (
        <div className="min-w-0">
          <p className="truncate font-semibold text-kaizen-900">
            {textoOGuion(exp.cliente)}
          </p>
          <p className="truncate text-xs text-tinta-suave">
            {textoOGuion(exp.descripcion)}
          </p>
        </div>
      ),
    },
    {
      clave: "categoria",
      encabezado: "Categoría",
      celda: (exp) => (
        <span className="text-sm whitespace-nowrap text-tinta">
          {exp.linea === "corp" ? "Corporativo" : "Automotriz"}
        </span>
      ),
    },
    {
      clave: "referencia",
      encabezado: "Referencia",
      anchoMinimo: "10rem",
      celda: (exp) => (
        <span className="text-xs whitespace-nowrap text-tinta-suave">
          {referencia(exp)}
        </span>
      ),
    },
    {
      clave: "fecha",
      encabezado: "Presentada",
      celda: (exp) => (
        <span className="text-sm whitespace-nowrap text-tinta-suave">
          {formatearFecha(exp.fecha)}
        </span>
      ),
    },
    {
      clave: "monto",
      encabezado: "Monto",
      alineacion: "derecha",
      celda: (exp) => (
        <span className="font-semibold whitespace-nowrap tabular-nums">
          {formatearDinero(exp.monto)}
        </span>
      ),
    },
    {
      clave: "etapa",
      encabezado: "Etapa",
      celda: (exp) => (
        <span className="text-sm whitespace-nowrap text-tinta-suave">
          {esLegal && etapaActual(exp) === "Crédito y Legal"
            ? "Legal"
            : etapaActual(exp)}
        </span>
      ),
    },
    {
      clave: "firmas",
      encabezado: esLegal ? "Legal" : "Firmas",
      alineacion: "centro",
      celda: (exp) =>
        esLegal ? (
          <span
            title={`Firma Legal: ${exp.status_leg === 1 ? "firmado" : "pendiente"}`}
            className={`inline-block h-2.5 w-2.5 rounded-full ${
              exp.status_leg === 1
                ? "bg-verde-trazo"
                : "bg-neutro-fondo ring-1 ring-neutro-trazo/30"
            }`}
          />
        ) : (
          <Firmas
            comp={exp.status_comp}
            legal={exp.status_leg}
            riesgo={exp.status_riesgo}
          />
        ),
    },
  ];

  if (!esLegal) {
    cols.push({
      clave: "score",
      encabezado: "Score",
      alineacion: "derecha",
      celda: (exp) => (
        <Insignia
          tono={semaforoScore(exp.score_f)}
          texto={exp.score_f ? formatearNumero(exp.score_f, 1) : "s/c"}
        />
      ),
    });
  }

  cols.push({
    clave: "dictamen",
    encabezado: accion === "ficha" ? "Status" : "Dictamen",
    anchoMinimo: "11rem",
    celda: (exp) => (
      <div className="min-w-0">
        <Insignia
          tono={semaforoDictamen(exp.dictamen)}
          texto={textoOGuion(exp.dictamen)}
        />
        {exp.devuelto_a && (
          <p className="mt-1 truncate text-xs text-tinta-suave">
            Devuelto a {exp.devuelto_a}
          </p>
        )}
      </div>
    ),
  });

  return cols;
}
