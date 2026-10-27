"use client";

/**
 * Filtros de las bandejas de expedientes.
 *
 * Los comparten la bandeja de evaluaciones y el status de créditos, que listan
 * lo mismo con distinto alcance. Filtran sobre lo ya recibido: son un recorte de
 * lectura, no una consulta nueva —el alcance lo fija `view_mode` en el backend—.
 *
 * El dictamen se agrupa por lo que significa para el negocio: en la base, un
 * expediente frenado se guarda como «REVISIÓN-<etapa>» y uno denegado como
 * «RECHAZADO», pero quien mira la bandeja piensa en «frenado» y «denegado».
 */

import type { ExpedienteAutomotriz, ExpedienteCorporativo } from "@/types/api";
import { etapaActual } from "@/utils/estados";
import { formatearFecha } from "@/utils/format";

export type Categoria = "todos" | "corp" | "auto";
export type EtapaFiltro = "todas" | "Cumplimiento" | "Crédito y Legal" | "Comité" | "Cerrado";
export type DictamenFiltro = "todos" | "PENDIENTE" | "APROBADO" | "DENEGADO" | "FRENADO";

/** Expediente de cualquiera de las dos líneas, etiquetado con la suya. */
export type FilaExpediente = (ExpedienteCorporativo | ExpedienteAutomotriz) & {
  linea: "corp" | "auto";
};

const CATEGORIAS: Array<[Categoria, string]> = [
  ["todos", "Todos"],
  ["corp", "Corporativo"],
  ["auto", "Automotriz"],
];

const ETAPAS: Array<[EtapaFiltro, string]> = [
  ["todas", "Todas"],
  ["Cumplimiento", "Cumplimiento"],
  ["Crédito y Legal", "Crédito y Legal"],
  ["Comité", "Comité"],
  ["Cerrado", "Cerrado"],
];

const DICTAMENES: Array<[DictamenFiltro, string]> = [
  ["todos", "Todos"],
  ["PENDIENTE", "Pendiente"],
  ["APROBADO", "Aprobado"],
  ["DENEGADO", "Denegado"],
  ["FRENADO", "Frenado"],
];

const SELECTOR =
  "rounded-md border border-borde bg-white px-3 py-2 text-sm text-tinta shadow-sm " +
  "focus:border-kaizen-900 focus:outline-none focus:ring-1 focus:ring-kaizen-900";

const BUSCADOR =
  "w-full max-w-sm rounded-md border border-borde bg-white px-3 py-2 text-sm " +
  "text-tinta shadow-sm placeholder:text-tinta-suave focus:border-kaizen-900 " +
  "focus:outline-none focus:ring-1 focus:ring-kaizen-900";

/** La etapa se deduce de las firmas, igual que la muestra la tabla. */
export function coincideEtapa(fila: FilaExpediente, filtro: EtapaFiltro): boolean {
  return filtro === "todas" || etapaActual(fila) === filtro;
}

export function coincideDictamen(
  fila: FilaExpediente,
  filtro: DictamenFiltro,
): boolean {
  if (filtro === "todos") return true;
  const valor = (fila.dictamen ?? "PENDIENTE").toUpperCase();

  if (filtro === "DENEGADO") {
    return valor === "RECHAZADO" || valor === "DENEGADO";
  }
  if (filtro === "FRENADO") {
    return (
      valor.startsWith("REVISIÓN") ||
      valor.startsWith("REVISION") ||
      valor === "FRENADO" ||
      valor === "DEVUELTO"
    );
  }
  return valor === filtro;
}

/**
 * Texto sobre el que busca la barra.
 *
 * Se arma con lo que la fila muestra —identificador, cliente, referencia,
 * fecha, importe, etapa y dictamen—, no con la fila entera: buscar dentro de
 * campos que no estan en pantalla devolveria coincidencias que nadie ve.
 */
function textoBuscable(fila: FilaExpediente): string {
  const auto = fila as ExpedienteAutomotriz;
  const corp = fila as ExpedienteCorporativo;
  return [
    fila.id,
    fila.cliente,
    fila.descripcion,
    fila.linea === "corp" ? "Corporativo" : "Automotriz",
    fila.linea === "corp" ? corp.rif : auto.cedula,
    auto.marca,
    auto.modelo,
    auto.anio,
    formatearFecha(fila.fecha),
    fila.monto,
    etapaActual(fila),
    fila.dictamen,
    fila.devuelto_a,
  ]
    .filter((valor) => valor !== null && valor !== undefined && valor !== "")
    .join(" ")
    .toLowerCase();
}

/** Coincidencia sin distinguir mayusculas; el termino ya viene normalizado. */
export function coincideTexto(fila: FilaExpediente, termino: string): boolean {
  return !termino || textoBuscable(fila).includes(termino);
}

function Campo({
  etiqueta,
  valor,
  opciones,
  alCambiar,
}: {
  etiqueta: string;
  valor: string;
  opciones: Array<[string, string]>;
  alCambiar: (valor: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-semibold tracking-wide text-tinta-suave uppercase">
        {etiqueta}
      </span>
      <select
        value={valor}
        onChange={(evento) => alCambiar(evento.target.value)}
        className={SELECTOR}
      >
        {opciones.map(([clave, texto]) => (
          <option key={clave} value={clave}>
            {texto}
          </option>
        ))}
      </select>
    </label>
  );
}

export function FiltrosExpedientes({
  categoria,
  etapa,
  dictamen,
  busqueda,
  alCambiarCategoria,
  alCambiarEtapa,
  alCambiarDictamen,
  alCambiarBusqueda,
  acciones,
}: {
  categoria: Categoria;
  etapa: EtapaFiltro;
  dictamen: DictamenFiltro;
  busqueda: string;
  alCambiarCategoria: (valor: Categoria) => void;
  alCambiarEtapa: (valor: EtapaFiltro) => void;
  alCambiarDictamen: (valor: DictamenFiltro) => void;
  alCambiarBusqueda: (valor: string) => void;
  /** Botones propios de la pantalla, alineados al final de la barra. */
  acciones?: React.ReactNode;
}) {
  return (
    <section
      className="mb-5 flex flex-wrap items-end gap-4"
      aria-label="Filtros de la bandeja"
    >
      <Campo
        etiqueta="Categoría"
        valor={categoria}
        opciones={CATEGORIAS}
        alCambiar={(v) => alCambiarCategoria(v as Categoria)}
      />
      <Campo
        etiqueta="Etapa"
        valor={etapa}
        opciones={ETAPAS}
        alCambiar={(v) => alCambiarEtapa(v as EtapaFiltro)}
      />
      <Campo
        etiqueta="Dictamen"
        valor={dictamen}
        opciones={DICTAMENES}
        alCambiar={(v) => alCambiarDictamen(v as DictamenFiltro)}
      />
      <label className="flex flex-col gap-1.5">
        <span className="text-xs font-semibold tracking-wide text-tinta-suave uppercase">
          Buscar
        </span>
        <input
          type="search"
          value={busqueda}
          onChange={(evento) => alCambiarBusqueda(evento.target.value)}
          placeholder="Cliente, RIF, vehículo…"
          className={BUSCADOR}
        />
      </label>
      {acciones && <div className="ml-auto flex items-center gap-3">{acciones}</div>}
    </section>
  );
}
