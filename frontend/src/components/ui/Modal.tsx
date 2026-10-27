"use client";

/**
 * Ventana modal.
 *
 * Sustituye a los `st.dialog` de la interfaz anterior. Cierra con Escape y con
 * clic en el velo, devuelve el foco al abrirse y bloquea el desplazamiento del
 * fondo mientras está abierta, que son las tres cosas que un diálogo hecho a
 * mano suele olvidar.
 */

import { useEffect, useRef, type ReactNode } from "react";

export function Modal({
  abierto,
  titulo,
  descripcion,
  alCerrar,
  children,
  pie,
}: {
  abierto: boolean;
  titulo: string;
  descripcion?: string;
  alCerrar: () => void;
  children: ReactNode;
  pie?: ReactNode;
}) {
  const caja = useRef<HTMLDivElement>(null);

  // `alCerrar` suele ser una funcion nueva en cada render del formulario que usa
  // el modal. Guardarla en una referencia mantiene el efecto de apertura atado
  // solo a `abierto`: si dependiera de ella, cada pulsacion de tecla volveria a
  // ejecutarlo y `caja.focus()` robaria el foco al campo que se esta rellenando.
  const alCerrarRef = useRef(alCerrar);
  useEffect(() => {
    alCerrarRef.current = alCerrar;
  });

  useEffect(() => {
    if (!abierto) return;

    const cerrarConEscape = (evento: KeyboardEvent) => {
      if (evento.key === "Escape") alCerrarRef.current();
    };

    document.addEventListener("keydown", cerrarConEscape);
    const desbordeOriginal = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    // El foco entra al dialogo una sola vez, al abrirse.
    caja.current?.focus();

    return () => {
      document.removeEventListener("keydown", cerrarConEscape);
      document.body.style.overflow = desbordeOriginal;
    };
  }, [abierto]);

  if (!abierto) return null;

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-kaizen-900/50 p-4 backdrop-blur-[2px]"
      onClick={alCerrar}
    >
      <div
        ref={caja}
        role="dialog"
        aria-modal="true"
        aria-label={titulo}
        tabIndex={-1}
        onClick={(evento) => evento.stopPropagation()}
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl border border-borde bg-white shadow-2xl outline-none"
      >
        <div className="flex items-start justify-between gap-4 border-b border-borde px-6 py-4">
          <div className="min-w-0">
            <h2 className="text-base font-bold text-kaizen-900">{titulo}</h2>
            {descripcion && (
              <p className="mt-1 text-sm text-tinta-suave">{descripcion}</p>
            )}
          </div>
          <button
            type="button"
            onClick={alCerrar}
            aria-label="Cerrar"
            className="shrink-0 text-lg leading-none text-tinta-suave transition hover:text-kaizen-900"
          >
            ×
          </button>
        </div>

        <div className="px-6 py-5">{children}</div>

        {pie && (
          <div className="flex flex-wrap justify-end gap-3 border-t border-borde px-6 py-4">
            {pie}
          </div>
        )}
      </div>
    </div>
  );
}

const BASE_BOTON =
  "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm " +
  "font-semibold transition disabled:cursor-not-allowed disabled:opacity-60";

export const BOTON = {
  primario: `${BASE_BOTON} bg-kaizen-800 text-white hover:bg-kaizen-900`,
  peligro: `${BASE_BOTON} bg-rojo-trazo text-white hover:brightness-90`,
  aviso: `${BASE_BOTON} bg-ambar-trazo text-white hover:brightness-90`,
  neutro: `${BASE_BOTON} border border-borde bg-white text-tinta hover:border-kaizen-600 hover:text-kaizen-600`,
} as const;

export const CAMPO =
  "w-full rounded-lg border border-borde bg-white px-3 py-2 text-sm text-tinta " +
  "outline-none transition focus:border-kaizen-600 focus:ring-2 focus:ring-kaizen-600/20";
