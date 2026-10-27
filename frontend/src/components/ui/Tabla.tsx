"use client";

/**
 * Tabla de datos genérica.
 *
 * Cada columna declara cómo se pinta su celda, de modo que la vista no repite el
 * andamiaje de `thead`/`tbody` ni las clases de alineación. La tabla desplaza en
 * horizontal dentro de su propia caja: la página nunca lo hace.
 *
 * No filtra ni ordena: recibe las filas ya recortadas. Cada pantalla reúne sus
 * filtros —texto y desplegables— en una sola barra, y tenerlos ahí es lo que
 * permite combinarlos; un buscador propio de la tabla competiria con ellos.
 */

import type { ReactNode } from "react";

export interface Columna<T> {
  clave: string;
  encabezado: string;
  celda: (fila: T) => ReactNode;
  /** Los importes y los conteos se alinean a la derecha. */
  alineacion?: "izquierda" | "derecha" | "centro";
  anchoMinimo?: string;
}

const ALINEACION = {
  izquierda: "text-left",
  derecha: "text-right",
  centro: "text-center",
} as const;

export function Tabla<T>({
  columnas,
  filas,
  claveFila,
  titulo,
  pie,
}: {
  columnas: Array<Columna<T>>;
  filas: T[];
  claveFila: (fila: T, indice: number) => string | number;
  titulo?: string;
  pie?: ReactNode;
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-borde bg-white shadow-sm">
      {titulo && (
        <div className="border-b border-borde px-5 py-3">
          <h3 className="text-sm font-semibold text-kaizen-900">{titulo}</h3>
        </div>
      )}

      <div className="scroll-fino overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-kaizen-900 text-white">
              {columnas.map((columna) => (
                <th
                  key={columna.clave}
                  scope="col"
                  style={{ minWidth: columna.anchoMinimo }}
                  className={`px-5 py-3 text-xs font-semibold tracking-wide uppercase whitespace-nowrap ${
                    ALINEACION[columna.alineacion ?? "izquierda"]
                  }`}
                >
                  {columna.encabezado}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-borde">
            {filas.map((fila, indice) => (
              <tr
                key={claveFila(fila, indice)}
                className="transition hover:bg-kaizen-100/40"
              >
                {columnas.map((columna) => (
                  <td
                    key={columna.clave}
                    className={`px-5 py-3.5 align-middle ${
                      ALINEACION[columna.alineacion ?? "izquierda"]
                    }`}
                  >
                    {columna.celda(fila)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {pie && (
        <div className="flex items-center justify-between gap-4 border-t border-borde px-5 py-3">
          {pie}
        </div>
      )}
    </div>
  );
}
