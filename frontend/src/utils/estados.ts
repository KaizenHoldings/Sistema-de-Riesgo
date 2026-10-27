/**
 * Traducción de los estados del dominio al semáforo institucional.
 *
 * Los criterios son los mismos que aplica la interfaz de Streamlit, de modo que
 * un expediente se ve del mismo color en las dos interfaces mientras conviven.
 */

export type Semaforo = "verde" | "ambar" | "rojo" | "neutro";

/** Dictamen del Comité. */
export function semaforoDictamen(dictamen: string | null | undefined): Semaforo {
  const d = (dictamen ?? "").toUpperCase();
  if (d === "APROBADO") return "verde";
  if (d === "RECHAZADO") return "rojo";
  if (d.startsWith("REVISIÓN") || d.startsWith("REVISION")) return "ambar";
  return "neutro";
}

/** Estado del expediente KYC de un cliente. */
export function semaforoKyc(estado: string | null | undefined): Semaforo {
  const e = (estado ?? "").toLowerCase();
  if (e.includes("aprobado")) return "verde";
  if (e.includes("rechazado")) return "rojo";
  if (e.includes("pendiente") || e.includes("revisión") || e.includes("revision")) {
    return "ambar";
  }
  return "neutro";
}

/** Nivel de riesgo AML declarado por Cumplimiento. */
export function semaforoRiesgoAml(nivel: string | null | undefined): Semaforo {
  const n = (nivel ?? "").toLowerCase();
  if (n === "bajo") return "verde";
  if (n === "medio") return "ambar";
  if (n === "alto") return "rojo";
  return "neutro";
}

/**
 * Score final de 0 a 10. El corte en 7 y 5 es el mismo que usa la vista de
 * riesgo para clasificar la calidad crediticia.
 */
export function semaforoScore(score: number | null | undefined): Semaforo {
  if (score === null || score === undefined || !Number.isFinite(score) || score === 0) {
    return "neutro";
  }
  if (score >= 7) return "verde";
  if (score >= 5) return "ambar";
  return "rojo";
}

/** Etapa del circuito en la que se encuentra el expediente. */
export function etapaActual(exp: {
  status_comp: number | null;
  status_leg: number | null;
  status_riesgo: number | null;
  dictamen: string | null;
}): string {
  const d = (exp.dictamen ?? "").toUpperCase();
  if (d === "APROBADO" || d === "RECHAZADO") return "Cerrado";
  if (exp.status_comp !== 1) return "Cumplimiento";
  if (exp.status_leg !== 1 || exp.status_riesgo !== 1) return "Crédito y Legal";
  return "Comité";
}

/** Firmas registradas sobre las tres del circuito. */
export function firmasRegistradas(exp: {
  status_comp: number | null;
  status_leg: number | null;
  status_riesgo: number | null;
}): number {
  return [exp.status_comp, exp.status_leg, exp.status_riesgo].filter((f) => f === 1)
    .length;
}

/**
 * Semáforo que emite el motor de riesgo para indicadores y Altman.
 *
 * El backend responde «Verde», «Amarillo» o «Rojo» cuando hay umbral, y
 * «Referencial» o nulo cuando el indicador no tiene umbral o no se pudo
 * calcular; esos dos últimos casos se muestran en neutro.
 */
export function semaforoMotor(valor: string | null | undefined): Semaforo {
  if (valor === "Verde") return "verde";
  if (valor === "Amarillo") return "ambar";
  if (valor === "Rojo") return "rojo";
  return "neutro";
}

/**
 * Clases de tarjeta completa para cada estado del semáforo.
 *
 * Fondo, borde y texto salen de las parejas `*-fondo` / `*-trazo` definidas en
 * el bloque `@theme` de `globals.css`. Se escriben como cadenas literales
 * completas porque Tailwind solo genera las clases que encuentra enteras en el
 * código: componerlas por interpolación dejaría la tarjeta sin color.
 */
export const TARJETA_SEMAFORO: Record<Semaforo, string> = {
  verde: "bg-verde-fondo border-verde-trazo text-verde-trazo",
  ambar: "bg-ambar-fondo border-ambar-trazo text-ambar-trazo",
  rojo: "bg-rojo-fondo border-rojo-trazo text-rojo-trazo",
  neutro: "bg-neutro-fondo border-neutro-trazo text-neutro-trazo",
};
