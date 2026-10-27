"use client";

/**
 * Hook base de lectura contra la API.
 *
 * Resuelve de una vez lo que si no se repetiría en cada vista: el estado de
 * carga, el error ya normalizado, la cancelación de la petición cuando cambian
 * los filtros —para que una respuesta lenta no pise a otra más reciente— y una
 * recarga manual.
 *
 * El resultado se guarda etiquetado con la clave de los filtros que lo
 * produjeron. Así «cargando» no es un estado que haya que encender a mano al
 * entrar en el efecto —lo que provocaría renders en cascada—, sino simplemente
 * no tener todavía una respuesta para los filtros vigentes.
 */

import { useCallback, useEffect, useState } from "react";

import { ApiError } from "@/utils/apiClient";

export interface EstadoConsulta<T> {
  datos: T | null;
  cargando: boolean;
  error: ApiError | null;
  recargar: () => void;
}

interface Resultado<T> {
  clave: string;
  datos: T | null;
  error: ApiError | null;
}

export function useApiQuery<T>(
  obtener: (signal: AbortSignal) => Promise<T>,
  dependencias: readonly unknown[],
  /**
   * Permite declarar el hook sin llegar a consultar. Los hooks no admiten
   * condicionales, así que una vista que elige entre dos fuentes los declara
   * ambos y deja inactiva la que no toca, en lugar de pedir un identificador
   * que sabe que no existe.
   */
  habilitado = true,
): EstadoConsulta<T> {
  const [intento, setIntento] = useState(0);
  const [resultado, setResultado] = useState<Resultado<T> | null>(null);

  const clave = `${JSON.stringify(dependencias)}#${intento}`;

  useEffect(() => {
    if (!habilitado) return;

    const controlador = new AbortController();

    obtener(controlador.signal)
      .then((datos) => {
        if (controlador.signal.aborted) return;
        setResultado({ clave, datos, error: null });
      })
      .catch((fallo: unknown) => {
        if (controlador.signal.aborted) return;
        setResultado({
          clave,
          datos: null,
          error:
            fallo instanceof ApiError
              ? fallo
              : new ApiError(0, "Error inesperado al consultar el servicio."),
        });
      });

    return () => controlador.abort();
  }, [clave, obtener, habilitado]);

  const recargar = useCallback(() => setIntento((n) => n + 1), []);

  // Un resultado de una clave anterior pertenece a unos filtros que ya no están
  // en pantalla: se ignora y la vista vuelve a mostrarse cargando.
  const vigente = resultado !== null && resultado.clave === clave ? resultado : null;

  return {
    datos: vigente?.datos ?? null,
    cargando: habilitado && vigente === null,
    error: vigente?.error ?? null,
    recargar,
  };
}
