"use client";

/**
 * Hook para las operaciones que escriben.
 *
 * La contrapartida de `useApiQuery`: allí el disparo es el cambio de filtros,
 * aquí es un clic. Guarda el estado de envío y el error ya normalizado para que
 * el formulario pueda deshabilitar su botón y mostrar el aviso sin repetir el
 * mismo `try` en cada modal.
 *
 * El error se devuelve además de guardarse, para que quien llama decida si lo
 * muestra en línea —lo habitual en un modal— o lo lanza como aviso emergente.
 */

import { useCallback, useState } from "react";

import { ApiError } from "@/utils/apiClient";

export interface EstadoAccion<A extends unknown[], R> {
  ejecutar: (...args: A) => Promise<R | null>;
  enviando: boolean;
  error: ApiError | null;
  limpiarError: () => void;
}

export function useAccion<A extends unknown[], R>(
  accion: (...args: A) => Promise<R>,
): EstadoAccion<A, R> {
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const ejecutar = useCallback(
    async (...args: A): Promise<R | null> => {
      setEnviando(true);
      setError(null);
      try {
        return await accion(...args);
      } catch (fallo: unknown) {
        setError(
          fallo instanceof ApiError
            ? fallo
            : new ApiError(0, "No se pudo completar la operación."),
        );
        return null;
      } finally {
        setEnviando(false);
      }
    },
    [accion],
  );

  const limpiarError = useCallback(() => setError(null), []);

  return { ejecutar, enviando, error, limpiarError };
}
