/**
 * Semáforo institucional.
 *
 * Lleva punto de color y además texto: el color por sí solo no es accesible para
 * quien no lo distingue, y en un expediente de crédito la diferencia entre ámbar
 * y rojo cambia la decisión.
 */

import type { Semaforo as Tono } from "@/utils/estados";

const ESTILOS: Record<Tono, { caja: string; punto: string }> = {
  verde: { caja: "bg-verde-fondo text-verde-trazo", punto: "bg-verde-trazo" },
  ambar: { caja: "bg-ambar-fondo text-ambar-trazo", punto: "bg-ambar-trazo" },
  rojo: { caja: "bg-rojo-fondo text-rojo-trazo", punto: "bg-rojo-trazo" },
  neutro: { caja: "bg-neutro-fondo text-neutro-trazo", punto: "bg-neutro-trazo" },
};

export function Insignia({
  tono,
  texto,
}: {
  tono: Tono;
  texto: string;
}) {
  const estilo = ESTILOS[tono];
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold whitespace-nowrap ${estilo.caja}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${estilo.punto}`} aria-hidden />
      {texto}
    </span>
  );
}

/** Firmas del circuito: tres puntos, uno por etapa, con su rótulo accesible. */
export function Firmas({
  comp,
  legal,
  riesgo,
}: {
  comp: number | null;
  legal: number | null;
  riesgo: number | null;
}) {
  const etapas: Array<[string, number | null]> = [
    ["Cumplimiento", comp],
    ["Legal", legal],
    ["Riesgo", riesgo],
  ];

  return (
    <span className="inline-flex items-center gap-1.5">
      {etapas.map(([nombre, firmada]) => (
        <span
          key={nombre}
          title={`${nombre}: ${firmada === 1 ? "firmado" : "pendiente"}`}
          className={`h-2.5 w-2.5 rounded-full ${
            firmada === 1 ? "bg-verde-trazo" : "bg-neutro-fondo ring-1 ring-neutro-trazo/30"
          }`}
        >
          <span className="sr-only">
            {nombre}: {firmada === 1 ? "firmado" : "pendiente"}
          </span>
        </span>
      ))}
    </span>
  );
}
