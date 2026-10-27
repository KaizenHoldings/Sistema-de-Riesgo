/**
 * Formateo para la presentación institucional.
 *
 * Los importes llegan del backend como cadena —`Dinero` se serializa así para
 * conservar la cuantización a céntimos— y se convierten a número solo aquí, en
 * el último paso antes de pintarlos.
 */

const MONEDA = new Intl.NumberFormat("es-VE", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const ENTERO = new Intl.NumberFormat("es-VE", { maximumFractionDigits: 0 });

export function formatearDinero(valor: string | number | null | undefined): string {
  if (valor === null || valor === undefined || valor === "") return "—";
  const numero = typeof valor === "number" ? valor : Number(valor);
  if (!Number.isFinite(numero)) return "—";
  return MONEDA.format(numero);
}

export function formatearNumero(valor: number | null | undefined, decimales = 2): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) return "—";
  return valor.toFixed(decimales);
}

export function formatearEntero(valor: number | null | undefined): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) return "0";
  return ENTERO.format(valor);
}

/** Las fechas se guardan como texto ISO; se muestran en formato local corto. */
export function formatearFecha(valor: string | null | undefined): string {
  if (!valor) return "—";
  const fecha = new Date(valor.slice(0, 10));
  if (Number.isNaN(fecha.getTime())) return valor;
  return fecha.toLocaleDateString("es-VE", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function textoOGuion(valor: string | null | undefined): string {
  const limpio = (valor ?? "").trim();
  return limpio.length > 0 ? limpio : "—";
}
