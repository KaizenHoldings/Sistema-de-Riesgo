/**
 * Dirección interna del backend FastAPI.
 *
 * Es una variable de servidor, sin el prefijo `NEXT_PUBLIC_`: la dirección del
 * backend no viaja al navegador. Solo la usan las acciones de servidor y el
 * proxy, que son las únicas piezas que hablan directamente con él.
 */
export const BACKEND_ORIGIN = (
  process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000"
).replace(/\/+$/, "");
