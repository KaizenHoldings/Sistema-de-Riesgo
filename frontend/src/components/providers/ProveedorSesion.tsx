"use client";

/**
 * Sesión autenticada, disponible en todo el árbol.
 *
 * Ya no hay almacén en el navegador: la identidad la resuelve el servidor
 * leyendo la cookie `HttpOnly` y la entrega como propiedad al montar el layout.
 * Aquí solo se transporta hacia abajo, de modo que no hay estado que hidratar ni
 * ventana en la que el cliente muestre algo distinto de lo que el servidor sabe.
 *
 * El cierre de sesión tampoco toca nada local: invoca la acción de servidor, que
 * es la única que puede borrar la cookie.
 */

import { useRouter } from "next/navigation";
import { createContext, useContext, useMemo, useTransition, type ReactNode } from "react";

import { cerrarSesion } from "@/app/actions/auth";

export interface Sesion {
  usuario: string;
  rol: string;
}

interface ContextoSesion {
  sesion: Sesion | null;
  /** Cierto mientras la acción de cierre está en curso. */
  cerrando: boolean;
  cerrar: () => void;
}

const Contexto = createContext<ContextoSesion | null>(null);

export function ProveedorSesion({
  sesion,
  children,
}: {
  sesion: Sesion | null;
  children: ReactNode;
}) {
  const router = useRouter();
  const [cerrando, iniciarTransicion] = useTransition();

  const valor = useMemo<ContextoSesion>(
    () => ({
      sesion,
      cerrando,
      cerrar: () =>
        iniciarTransicion(async () => {
          await cerrarSesion();
          router.replace("/login");
        }),
    }),
    [sesion, cerrando, router],
  );

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

export function useSesion(): ContextoSesion {
  const contexto = useContext(Contexto);
  if (!contexto) {
    throw new Error("useSesion debe usarse dentro de ProveedorSesion.");
  }
  return contexto;
}
