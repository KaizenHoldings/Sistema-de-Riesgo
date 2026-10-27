"use client";

/**
 * Paginación.
 *
 * El backend pagina en el motor y no devuelve el total de páginas, así que el
 * control avanza mientras la página venga llena y se detiene en cuanto llega
 * incompleta: es la última.
 */

export function Paginador({
  pagina,
  porPagina,
  recibidas,
  alCambiar,
}: {
  pagina: number;
  porPagina: number;
  recibidas: number;
  alCambiar: (pagina: number) => void;
}) {
  const hayAnterior = pagina > 1;
  const haySiguiente = recibidas === porPagina;
  const desde = recibidas === 0 ? 0 : (pagina - 1) * porPagina + 1;
  const hasta = (pagina - 1) * porPagina + recibidas;

  const clase =
    "rounded-lg border border-borde px-3 py-1.5 text-sm font-medium transition " +
    "enabled:hover:border-kaizen-600 enabled:hover:text-kaizen-600 " +
    "disabled:cursor-not-allowed disabled:opacity-40";

  return (
    <>
      <p className="text-sm text-tinta-suave tabular-nums">
        Registros {desde} a {hasta}
      </p>
      <div className="flex items-center gap-2">
        <button
          type="button"
          className={clase}
          disabled={!hayAnterior}
          onClick={() => alCambiar(pagina - 1)}
        >
          Anterior
        </button>
        <span className="px-2 text-sm font-semibold text-kaizen-900 tabular-nums">
          {pagina}
        </span>
        <button
          type="button"
          className={clase}
          disabled={!haySiguiente}
          onClick={() => alCambiar(pagina + 1)}
        >
          Siguiente
        </button>
      </div>
    </>
  );
}
