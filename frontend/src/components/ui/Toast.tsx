"use client";

/**
 * Avisos emergentes.
 *
 * Existen para los fallos que no pertenecen a ninguna zona concreta de la
 * pantalla —una recarga que no responde, una transición rechazada por el
 * backend—. Cuando el fallo sí tiene un sitio natural, como una tabla que no ha
 * podido cargarse, se usa `Alerta` en línea y no un aviso emergente.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { ApiError, titularDeError } from "@/utils/apiClient";

export type TonoAviso = "error" | "aviso" | "exito";

interface Aviso {
  id: number;
  tono: TonoAviso;
  titulo: string;
  mensaje: string;
}

interface ContextoAvisos {
  notificar: (tono: TonoAviso, titulo: string, mensaje: string) => void;
  /** Traduce un `ApiError` a un aviso con el titular que le corresponde. */
  notificarError: (error: ApiError) => void;
}

const Contexto = createContext<ContextoAvisos | null>(null);

const DURACION_MS = 6000;

const ESTILOS: Record<TonoAviso, string> = {
  error: "border-l-rojo-trazo bg-white",
  aviso: "border-l-ambar-trazo bg-white",
  exito: "border-l-verde-trazo bg-white",
};

const ICONOS: Record<TonoAviso, string> = {
  error: "●",
  aviso: "▲",
  exito: "✓",
};

const COLOR_ICONO: Record<TonoAviso, string> = {
  error: "text-rojo-trazo",
  aviso: "text-ambar-trazo",
  exito: "text-verde-trazo",
};

export function ProveedorAvisos({ children }: { children: ReactNode }) {
  const [avisos, setAvisos] = useState<Aviso[]>([]);
  const siguienteId = useRef(1);

  const descartar = useCallback((id: number) => {
    setAvisos((actuales) => actuales.filter((a) => a.id !== id));
  }, []);

  const notificar = useCallback(
    (tono: TonoAviso, titulo: string, mensaje: string) => {
      const id = siguienteId.current;
      siguienteId.current += 1;
      setAvisos((actuales) => [...actuales, { id, tono, titulo, mensaje }]);
    },
    [],
  );

  const notificarError = useCallback(
    (error: ApiError) => {
      notificar("error", titularDeError(error), error.message);
    },
    [notificar],
  );

  const valor = useMemo(
    () => ({ notificar, notificarError }),
    [notificar, notificarError],
  );

  return (
    <Contexto.Provider value={valor}>
      {children}
      <div
        className="pointer-events-none fixed bottom-6 right-6 z-50 flex w-full max-w-sm flex-col gap-3"
        role="status"
        aria-live="polite"
      >
        {avisos.map((aviso) => (
          <TarjetaAviso key={aviso.id} aviso={aviso} alCerrar={descartar} />
        ))}
      </div>
    </Contexto.Provider>
  );
}

function TarjetaAviso({
  aviso,
  alCerrar,
}: {
  aviso: Aviso;
  alCerrar: (id: number) => void;
}) {
  // La cuenta atrás solo corre con la pestaña a la vista. Un aviso emitido en
  // segundo plano —el autoguardado sigue funcionando con la pestaña oculta—
  // se retiraría sin que nadie llegara a verlo; así espera a que el usuario
  // vuelva y entonces cuenta sus segundos.
  useEffect(() => {
    let temporizador: number | undefined;

    const programar = () => {
      if (document.visibilityState !== "visible" || temporizador !== undefined) {
        return;
      }
      temporizador = window.setTimeout(() => alCerrar(aviso.id), DURACION_MS);
    };

    programar();
    document.addEventListener("visibilitychange", programar);
    return () => {
      document.removeEventListener("visibilitychange", programar);
      window.clearTimeout(temporizador);
    };
  }, [aviso.id, alCerrar]);

  return (
    <div
      className={`pointer-events-auto flex gap-3 rounded-lg border border-borde border-l-4 p-4 shadow-lg ${ESTILOS[aviso.tono]}`}
    >
      <span className={`text-sm leading-5 ${COLOR_ICONO[aviso.tono]}`} aria-hidden>
        {ICONOS[aviso.tono]}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-kaizen-900">{aviso.titulo}</p>
        <p className="mt-1 text-sm break-words text-tinta-suave">{aviso.mensaje}</p>
      </div>
      <button
        type="button"
        onClick={() => alCerrar(aviso.id)}
        className="self-start text-tinta-suave transition hover:text-kaizen-900"
        aria-label="Cerrar aviso"
      >
        ×
      </button>
    </div>
  );
}

export function useAvisos(): ContextoAvisos {
  const contexto = useContext(Contexto);
  if (!contexto) {
    throw new Error("useAvisos debe usarse dentro de ProveedorAvisos.");
  }
  return contexto;
}
