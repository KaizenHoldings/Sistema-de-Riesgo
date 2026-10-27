import { NextResponse, type NextRequest } from "next/server";

import { COOKIE_SESION } from "@/utils/sesionServidor";

/**
 * Guarda de acceso y validación de rutas con parámetros.
 *
 * Dos trabajos, ambos anteriores a que se monte nada:
 *
 * 1. **Sesión.** Sin la cookie de acceso, cualquier ruta privada devuelve al
 *    acceso. Hacerlo aquí y no en un componente evita el destello de pantalla
 *    protegida que se ve cuando la comprobación ocurre ya montado el árbol.
 *    Sigue sin ser la autorización real —esa la hace el backend verificando el
 *    JWT en cada petición—, pero sí impide pintar una pantalla que no va a
 *    poder cargar datos.
 *
 * 2. **Parámetros.** `notFound()` dentro de la página pinta la pantalla correcta
 *    pero responde 200: para entonces el árbol ya se está transmitiendo y las
 *    cabeceras están enviadas. Comprobar aquí los parámetros es lo que permite
 *    devolver un 404 de verdad.
 */

/** Lo único que se sirve sin sesión. */
const RUTAS_PUBLICAS = ["/login", "/no-encontrado"];

const FICHA_EVALUACION = /^\/evaluations\/([^/]+)\/([^/]+)\/?$/;

function esPublica(ruta: string): boolean {
  return RUTAS_PUBLICAS.some(
    (publica) => ruta === publica || ruta.startsWith(`${publica}/`),
  );
}

export function middleware(peticion: NextRequest) {
  const { pathname } = peticion.nextUrl;
  const autenticado = Boolean(peticion.cookies.get(COOKIE_SESION)?.value);

  // El proxy resuelve por su cuenta la falta de sesión con un 401, que es lo que
  // una petición de datos espera; redirigirla a una página HTML la rompería.
  if (pathname.startsWith("/api/")) {
    return NextResponse.next();
  }

  if (!autenticado && !esPublica(pathname)) {
    const destino = peticion.nextUrl.clone();
    destino.pathname = "/login";
    destino.search = "";
    return NextResponse.redirect(destino);
  }

  // Con sesión iniciada, la pantalla de acceso no tiene nada que ofrecer.
  if (autenticado && pathname === "/login") {
    const destino = peticion.nextUrl.clone();
    destino.pathname = "/dashboard";
    destino.search = "";
    return NextResponse.redirect(destino);
  }

  const coincidencia = FICHA_EVALUACION.exec(pathname);
  if (coincidencia) {
    const [, tipo, id] = coincidencia;
    const expId = Number(id);
    const valida =
      (tipo === "corp" || tipo === "auto") &&
      Number.isInteger(expId) &&
      expId > 0;

    if (!valida) {
      // Se reescribe a la pantalla de no encontrado para conservar el marco de
      // la aplicación, pero con el estado que corresponde.
      return NextResponse.rewrite(new URL("/no-encontrado", peticion.url), {
        status: 404,
      });
    }
  }

  return NextResponse.next();
}

export const config = {
  /**
   * Todo salvo los recursos internos de Next y los estáticos: la guarda debe
   * cubrir cualquier página, no una lista de rutas que habría que ampliar cada
   * vez que se añade un módulo.
   */
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
};
