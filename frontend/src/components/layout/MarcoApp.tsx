/**
 * Marco de la aplicación: barra lateral fija y área de contenido desplazable.
 *
 * En pantallas estrechas la barra pasa a ocupar el ancho completo por encima del
 * contenido, en lugar de esconderse tras un menú: son solo dos módulos.
 */

import type { ReactNode } from "react";

import { BarraLateral } from "@/components/layout/BarraLateral";

export function MarcoApp({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      <BarraLateral />
      <main className="min-w-0 flex-1 bg-lienzo px-5 py-8 sm:px-8 lg:px-10">
        <div className="mx-auto w-full max-w-7xl">{children}</div>
      </main>
    </div>
  );
}

/** Encabezado de página, con su miga y su bajada. */
export function EncabezadoPagina({
  icono,
  titulo,
  bajada,
  miga,
  acciones,
}: {
  icono: string;
  titulo: string;
  bajada: string;
  miga: string;
  acciones?: ReactNode;
}) {
  return (
    <header className="mb-8">
      <p className="text-xs font-semibold tracking-wider text-kaizen-600 uppercase">
        {miga}
      </p>
      <div className="mt-2 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-3 text-2xl font-bold text-kaizen-900">
            <span aria-hidden>{icono}</span>
            {titulo}
          </h1>
          <p className="mt-1.5 text-sm text-tinta-suave">{bajada}</p>
        </div>
        {acciones && <div className="flex items-center gap-2">{acciones}</div>}
      </div>
      <div className="mt-5 h-px bg-borde" />
    </header>
  );
}
