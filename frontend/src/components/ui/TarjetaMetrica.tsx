/**
 * Tarjeta de métrica del encabezado.
 *
 * El valor domina visualmente porque es lo que se lee de un vistazo; el rótulo y
 * la nota de apoyo quedan por debajo en peso y en tamaño.
 */

import type { ReactNode } from "react";

import type { Semaforo } from "@/utils/estados";

const ACENTOS: Record<Semaforo, string> = {
  verde: "border-t-verde-trazo",
  ambar: "border-t-ambar-trazo",
  rojo: "border-t-rojo-trazo",
  neutro: "border-t-kaizen-600",
};

export function TarjetaMetrica({
  rotulo,
  valor,
  nota,
  acento = "neutro",
  icono,
}: {
  rotulo: string;
  valor: string;
  nota?: string;
  acento?: Semaforo;
  icono?: ReactNode;
}) {
  return (
    <div
      className={`rounded-xl border border-borde border-t-4 bg-white p-5 shadow-sm transition hover:shadow-md ${ACENTOS[acento]}`}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-semibold tracking-wide text-tinta-suave uppercase">
          {rotulo}
        </p>
        {icono && <span className="text-kaizen-600">{icono}</span>}
      </div>
      <p className="mt-3 text-2xl font-bold text-kaizen-900 tabular-nums">{valor}</p>
      {nota && <p className="mt-2 text-xs text-tinta-suave">{nota}</p>}
    </div>
  );
}
