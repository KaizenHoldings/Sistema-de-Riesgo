"use client";

/**
 * Campos compartidos por los cuatro formularios de evaluación.
 *
 * Todos rotulan con `<label>` envolvente —el texto queda asociado al control sin
 * depender de identificadores— y heredan el color de texto oscuro que fija
 * `globals.css`, que es lo que evita el texto blanco sobre fondo blanco en el
 * autorrelleno del navegador.
 */

import type { ReactNode } from "react";

export const CONTROL =
  "w-full rounded-lg border border-borde bg-white px-3 py-2 text-sm text-tinta " +
  "outline-none transition focus:border-kaizen-600 focus:ring-2 focus:ring-kaizen-600/20 " +
  "disabled:cursor-not-allowed disabled:bg-lienzo disabled:text-tinta-suave";

export function Rotulo({ children }: { children: ReactNode }) {
  return (
    <span className="text-xs font-semibold tracking-wide text-tinta-suave uppercase">
      {children}
    </span>
  );
}

export function CampoTexto({
  rotulo,
  valor,
  alCambiar,
  ayuda,
  tipo = "text",
  requerido = false,
  deshabilitado = false,
}: {
  rotulo: string;
  valor: string;
  alCambiar: (valor: string) => void;
  ayuda?: string;
  tipo?: "text" | "date";
  requerido?: boolean;
  deshabilitado?: boolean;
}) {
  return (
    <label className="block">
      <Rotulo>
        {rotulo}
        {requerido && <span className="text-rojo-trazo"> *</span>}
      </Rotulo>
      <input
        type={tipo}
        value={valor}
        required={requerido}
        disabled={deshabilitado}
        onChange={(evento) => alCambiar(evento.target.value)}
        className={`mt-1.5 ${CONTROL}`}
      />
      {ayuda && <span className="mt-1 block text-xs text-tinta-suave">{ayuda}</span>}
    </label>
  );
}

export function CampoNumero({
  rotulo,
  valor,
  alCambiar,
  paso = "0.01",
  minimo,
  maximo,
  ayuda,
  deshabilitado = false,
}: {
  rotulo: string;
  valor: string;
  alCambiar: (valor: string) => void;
  paso?: string;
  minimo?: number;
  maximo?: number;
  ayuda?: string;
  deshabilitado?: boolean;
}) {
  return (
    <label className="block">
      <Rotulo>{rotulo}</Rotulo>
      <input
        type="number"
        inputMode="decimal"
        step={paso}
        min={minimo}
        max={maximo}
        value={valor}
        disabled={deshabilitado}
        onChange={(evento) => alCambiar(evento.target.value)}
        className={`mt-1.5 ${CONTROL} tabular-nums`}
      />
      {ayuda && <span className="mt-1 block text-xs text-tinta-suave">{ayuda}</span>}
    </label>
  );
}

export function CampoSeleccion({
  rotulo,
  valor,
  opciones,
  alCambiar,
  ayuda,
  deshabilitado = false,
}: {
  rotulo: string;
  valor: string;
  opciones: readonly string[];
  alCambiar: (valor: string) => void;
  ayuda?: string;
  deshabilitado?: boolean;
}) {
  return (
    <label className="block">
      <Rotulo>{rotulo}</Rotulo>
      <select
        value={valor}
        disabled={deshabilitado}
        onChange={(evento) => alCambiar(evento.target.value)}
        className={`mt-1.5 ${CONTROL}`}
      >
        {opciones.map((opcion) => (
          <option key={opcion} value={opcion}>
            {opcion}
          </option>
        ))}
      </select>
      {ayuda && <span className="mt-1 block text-xs text-tinta-suave">{ayuda}</span>}
    </label>
  );
}

export function CampoTextoLargo({
  rotulo,
  valor,
  alCambiar,
  marcador,
  requerido = false,
  filas = 3,
  deshabilitado = false,
}: {
  rotulo: string;
  valor: string;
  alCambiar: (valor: string) => void;
  marcador?: string;
  requerido?: boolean;
  filas?: number;
  deshabilitado?: boolean;
}) {
  return (
    <label className="block">
      <Rotulo>
        {rotulo}
        {requerido && <span className="text-rojo-trazo"> *</span>}
      </Rotulo>
      <textarea
        rows={filas}
        value={valor}
        placeholder={marcador}
        required={requerido}
        disabled={deshabilitado}
        onChange={(evento) => alCambiar(evento.target.value)}
        className={`mt-1.5 resize-y ${CONTROL}`}
      />
    </label>
  );
}

export function CampoCasilla({
  rotulo,
  valor,
  alCambiar,
  ayuda,
  deshabilitado = false,
}: {
  rotulo: string;
  valor: boolean;
  alCambiar: (valor: boolean) => void;
  ayuda?: string;
  deshabilitado?: boolean;
}) {
  return (
    <label className={`flex items-start gap-3 rounded-lg border border-borde px-4 py-3 ${deshabilitado ? "bg-lienzo opacity-70 cursor-not-allowed" : "bg-white"}`}>
      <input
        type="checkbox"
        checked={valor}
        disabled={deshabilitado}
        onChange={(evento) => alCambiar(evento.target.checked)}
        className="mt-0.5 h-4 w-4 shrink-0 accent-kaizen-800 disabled:cursor-not-allowed"
      />
      <span className="min-w-0">
        <span className="block text-sm font-medium text-tinta">{rotulo}</span>
        {ayuda && <span className="block text-xs text-tinta-suave">{ayuda}</span>}
      </span>
    </label>
  );
}

/** Agrupación con título, para separar bloques dentro de un formulario largo. */
export function Bloque({
  titulo,
  descripcion,
  children,
  columnas = 2,
}: {
  titulo: string;
  descripcion?: string;
  children: ReactNode;
  columnas?: 1 | 2 | 3;
}) {
  const rejilla =
    columnas === 1
      ? "grid-cols-1"
      : columnas === 3
        ? "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
        : "grid-cols-1 sm:grid-cols-2";

  return (
    <fieldset className="mt-6 first:mt-0">
      <legend className="text-sm font-semibold text-kaizen-900">{titulo}</legend>
      {descripcion && (
        <p className="mt-1 mb-3 text-xs text-tinta-suave">{descripcion}</p>
      )}
      <div className={`mt-3 grid gap-4 ${rejilla}`}>{children}</div>
    </fieldset>
  );
}

/**
 * Convierte el texto de un campo numérico a número.
 *
 * Conserva el signo: `-5000` es menos cinco mil, no cinco mil. Importa porque
 * los estados financieros admiten importes negativos con significado propio —una
 * recuperación de impuesto, una liberación de capital de trabajo—, y convertirlos
 * en positivos cambiaría el resultado sin que nadie lo notara.
 *
 * Tolera los estados intermedios de la escritura: mientras el campo está vacío o
 * contiene solo el signo, el valor es cero y el usuario puede seguir tecleando
 * sin que la pantalla salte a `NaN`.
 */
export function aNumero(valor: string): number {
  const texto = String(valor ?? "").trim();
  if (texto === "" || texto === "-" || texto === "+" || texto === ".") return 0;

  // Se admiten los espacios de agrupación que dejan algunos teclados numéricos.
  const n = Number(texto.replace(/\s/g, ""));
  return Number.isFinite(n) ? n : 0;
}
