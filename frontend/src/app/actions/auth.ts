"use server";

/**
 * Acciones de servidor para el acceso a la plataforma.
 *
 * El JWT no llega nunca al navegador: la credencial viaja al servidor de Next,
 * este la canjea contra `/token` del backend y guarda el token resultante en una
 * cookie `HttpOnly`. Un script inyectado en la página no puede leerla, que es
 * exactamente lo que no ocurría cuando el token vivía en el almacenamiento del
 * navegador.
 *
 * Estas acciones son el único sitio donde se escribe o se borra esa cookie.
 *
 * De este módulo solo pueden salir funciones asíncronas: es la regla de los
 * ficheros `"use server"`, y el tipo y el estado inicial del formulario viven
 * por eso en `estadoAcceso.ts`.
 */

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import type { EstadoAcceso } from "@/app/actions/estadoAcceso";
import { BACKEND_ORIGIN } from "@/utils/backend";
import { COOKIE_SESION } from "@/utils/sesionServidor";

/** Ocho horas, la misma vigencia que el backend firma en el token. */
const DURACION_SEGUNDOS = 60 * 60 * 8;

interface RespuestaToken {
  access_token?: unknown;
}

/**
 * Canjea usuario y contraseña por un token y abre la sesión.
 *
 * Devuelve el error en lugar de lanzarlo: la pantalla de acceso lo muestra junto
 * al formulario, con lo escrito intacto.
 */
export async function iniciarSesion(
  _estadoPrevio: EstadoAcceso,
  datos: FormData,
): Promise<EstadoAcceso> {
  const usuario = String(datos.get("usuario") ?? "").trim();
  const contrasena = String(datos.get("contrasena") ?? "");

  if (!usuario || !contrasena) {
    return { error: "Indique su usuario y su contraseña." };
  }

  let respuesta: Response;
  try {
    respuesta = await fetch(`${BACKEND_ORIGIN}/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ username: usuario, password: contrasena }),
      cache: "no-store",
    });
  } catch {
    return {
      error:
        "No se pudo contactar con el servicio de autenticación. Compruebe que " +
        "el backend está en marcha.",
    };
  }

  if (!respuesta.ok) {
    if (respuesta.status === 401) {
      return { error: "Usuario o contraseña incorrectos." };
    }
    return {
      error: `El servicio de autenticación respondió ${respuesta.status}.`,
    };
  }

  const cuerpo = (await respuesta.json()) as RespuestaToken;
  const token = cuerpo.access_token;
  if (typeof token !== "string" || token.length === 0) {
    return { error: "El servicio no devolvió ningún token de acceso." };
  }

  const almacen = await cookies();
  almacen.set(COOKIE_SESION, token, {
    httpOnly: true,
    // En despliegues HTTP (como IP directa sin certificado SSL), `secure: true`
    // hace que el navegador descarte la cookie. Se activa si COOKIE_SECURE="true".
    secure: process.env.COOKIE_SECURE === "true",
    sameSite: "lax",
    path: "/",
    maxAge: DURACION_SEGUNDOS,
  });

  // El marco se pinta en el servidor y muestra el usuario: hay que rehacerlo.
  revalidatePath("/", "layout");
  redirect("/dashboard");
}

/** Cierra la sesión borrando la cookie. */
export async function cerrarSesion(): Promise<void> {
  const almacen = await cookies();
  almacen.delete(COOKIE_SESION);
  revalidatePath("/", "layout");
}
