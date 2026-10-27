"use client";

import { IconoBuscador } from "@/components/ui/Iconos";

interface BuscadorTablaProps {
  valor: string;
  alCambiar: (valor: string) => void;
  placeholder?: string;
  className?: string;
  conteoFiltrado?: number;
  conteoTotal?: number;
}

export function BuscadorTabla({
  valor,
  alCambiar,
  placeholder = "Buscar en la tabla...",
  className = "",
  conteoFiltrado,
  conteoTotal,
}: BuscadorTablaProps) {
  return (
    <div className={`relative flex items-center ${className}`}>
      <IconoBuscador className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-tinta-suave" />
      <input
        type="text"
        value={valor}
        onChange={(e) => alCambiar(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-lg border border-borde bg-white pl-8 pr-7 py-1.5 text-xs text-kaizen-900 placeholder:text-tinta-suave outline-none transition focus:border-kaizen-600 focus:ring-1 focus:ring-kaizen-600/20"
      />
      {valor && (
        <button
          type="button"
          onClick={() => alCambiar("")}
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full p-0.5 text-xs text-tinta-suave hover:bg-slate-100 hover:text-kaizen-900"
          title="Limpiar búsqueda"
        >
          <span className="sr-only">Limpiar</span>
          ✕
        </button>
      )}
      {conteoTotal !== undefined && conteoFiltrado !== undefined && valor.trim() !== "" && (
        <span className="ml-2 text-[11px] text-tinta-suave whitespace-nowrap hidden sm:inline">
          ({conteoFiltrado} de {conteoTotal})
        </span>
      )}
    </div>
  );
}
