/**
 * Proxy autenticado entre el navegador y el backend FastAPI.
 *
 * Los componentes de cliente no pueden leer el JWT —vive en una cookie
 * `HttpOnly`— ni deberían: su trabajo es pedir datos, no custodiar credenciales.
 * Piden a `/api/proxy/...`, el navegador adjunta la cookie por ser el mismo
 * origen, y este manejador la convierte en la cabecera `Authorization` que el
 * backend espera.
 *
 * De paso desaparece el reenvío abierto que había en `next.config.ts`: antes
 * cualquiera podía atravesar el servidor de Next hacia el backend sin pasar por
 * ninguna comprobación; ahora sin cookie se responde 401 sin tocar la red.
 */

import { NextResponse, type NextRequest } from "next/server";

import { BACKEND_ORIGIN } from "@/utils/backend";
import { COOKIE_SESION } from "@/utils/sesionServidor";

/** Cabeceras que no deben copiarse: las fija el propio transporte. */
const CABECERAS_OMITIDAS = new Set([
  "host",
  "connection",
  "content-length",
  "transfer-encoding",
  "accept-encoding",
  "cookie",
]);

async function reenviar(
  peticion: NextRequest,
  contexto: { params: Promise<{ ruta: string[] }> },
): Promise<Response> {
  const { ruta } = await contexto.params;

  const token = peticion.cookies.get(COOKIE_SESION)?.value;
  if (!token) {
    return NextResponse.json(
      { detail: "La sesión ha caducado. Vuelva a iniciar sesión." },
      { status: 401 },
    );
  }

  const destino = new URL(`${BACKEND_ORIGIN}/${ruta.join("/")}`);
  destino.search = peticion.nextUrl.search;

  const cabeceras = new Headers();
  peticion.headers.forEach((valor, nombre) => {
    if (!CABECERAS_OMITIDAS.has(nombre.toLowerCase())) {
      cabeceras.set(nombre, valor);
    }
  });
  cabeceras.set("Authorization", `Bearer ${token}`);

  // El cuerpo se lee entero en lugar de transmitirse: evita el modo dúplex del
  // `fetch` de Node y basta para lo que sube esta aplicación —documentos del
  // expediente—, que son archivos de unos pocos megabytes.
  const cuerpo =
    peticion.method === "GET" || peticion.method === "HEAD"
      ? undefined
      : await peticion.arrayBuffer();

  let respuesta: Response;
  try {
    respuesta = await fetch(destino, {
      method: peticion.method,
      headers: cabeceras,
      body: cuerpo,
      cache: "no-store",
      redirect: "manual",
    });
  } catch {
    return NextResponse.json(
      {
        detail:
          "No se pudo contactar con el backend. Compruebe que el servicio " +
          "FastAPI está en marcha.",
      },
      { status: 502 },
    );
  }

  // La respuesta se devuelve tal cual —incluidos los binarios de las descargas—
  // conservando el tipo de contenido y el nombre del adjunto.
  const salida = new Headers();
  for (const nombre of ["content-type", "content-disposition", "content-length"]) {
    const valor = respuesta.headers.get(nombre);
    if (valor) salida.set(nombre, valor);
  }

  return new Response(respuesta.body, {
    status: respuesta.status,
    statusText: respuesta.statusText,
    headers: salida,
  });
}

export const GET = reenviar;
export const POST = reenviar;
export const PUT = reenviar;
export const PATCH = reenviar;
export const DELETE = reenviar;
