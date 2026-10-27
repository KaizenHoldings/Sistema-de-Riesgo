"use client";

/**
 * Elige el marco según la ruta.
 *
 * El acceso se sirve sin barra lateral: un menú de módulos junto al formulario
 * ofrece navegación que todavía no existe —no hay sesión— y deja a la vista la
 * estructura interna de la aplicación a quien aún no se ha identificado.
 *
 * Vive aparte del layout raíz porque decidirlo exige conocer la ruta en el
 * cliente, y el layout resuelve la sesión en el servidor. Los hijos siguen
 * llegando ya renderizados: este componente solo decide qué los envuelve.
 */

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { MarcoApp } from "@/components/layout/MarcoApp";

/** Rutas que se pintan solas, sin barra lateral ni encabezado de módulo. */
const RUTAS_SIN_MARCO = ["/login"];

export function Marco({ children }: { children: ReactNode }) {
  const ruta = usePathname();
  const sinMarco = RUTAS_SIN_MARCO.some(
    (publica) => ruta === publica || ruta.startsWith(`${publica}/`),
  );

  if (sinMarco) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-lienzo px-5 py-8">
        <div className="w-full max-w-md">{children}</div>
      </main>
    );
  }

  return <MarcoApp>{children}</MarcoApp>;
}
