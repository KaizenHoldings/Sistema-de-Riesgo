"use client";

/**
 * Aviso en línea para el fallo de una zona concreta de la pantalla.
 *
 * Distingue los tres errores de negocio del backend —404, 409 y 422— porque cada
 * uno pide una reacción distinta del usuario: buscar otro registro, revisar el
 * estado del expediente o completar los campos que faltan.
 */

import { ApiError, titularDeError } from "@/utils/apiClient";

const TONOS = {
  404: "border-neutro-trazo/30 bg-neutro-fondo text-neutro-trazo",
  409: "border-ambar-trazo/30 bg-ambar-fondo text-ambar-trazo",
  422: "border-ambar-trazo/30 bg-ambar-fondo text-ambar-trazo",
  otro: "border-rojo-trazo/30 bg-rojo-fondo text-rojo-trazo",
} as const;

function tonoDe(error: ApiError): string {
  if (error.esNoEncontrado) return TONOS[404];
  if (error.esConflicto) return TONOS[409];
  if (error.esValidacion) return TONOS[422];
  return TONOS.otro;
}

export function Alerta({
  error,
  alReintentar,
}: {
  error: ApiError;
  alReintentar?: () => void;
}) {
  return (
    <div className={`rounded-xl border p-5 ${tonoDe(error)}`} role="alert">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm font-semibold">{titularDeError(error)}</p>
          <p className="mt-1 text-sm opacity-90">{error.message}</p>

          {error.campos.length > 0 && (
            <ul className="mt-3 list-inside list-disc space-y-1 text-sm opacity-90">
              {error.campos.map((campo) => (
                <li key={campo.campo}>
                  <span className="font-medium">{campo.campo}</span>: {campo.mensaje}
                </li>
              ))}
            </ul>
          )}
        </div>

        {alReintentar && (
          <button
            type="button"
            onClick={alReintentar}
            className="shrink-0 rounded-lg border border-current px-3 py-1.5 text-sm font-medium transition hover:bg-white/60"
          >
            Reintentar
          </button>
        )}
      </div>
    </div>
  );
}

/** Estado vacío: la consulta funcionó, pero no devolvió filas. */
export function SinResultados({ mensaje }: { mensaje: string }) {
  return (
    <div className="rounded-xl border border-dashed border-borde bg-white px-6 py-12 text-center">
      <p className="text-sm text-tinta-suave">{mensaje}</p>
    </div>
  );
}
