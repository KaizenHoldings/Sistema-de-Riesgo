/**
 * Lectura de la sesión en el servidor.
 *
 * El JWT vive en una cookie `HttpOnly`, así que el navegador no puede leerlo:
 * solo el servidor de Next y el backend. Este módulo es el único punto donde se
 * abre esa cookie, y no se importa nunca desde un componente de cliente.
 *
 * Las claims se leen sin verificar la firma. La verificación es del backend, que
 * la repite en cada petición; aquí solo sirven para rotular la interfaz, de modo
 * que una lectura fallida no es un problema de seguridad sino un rótulo vacío.
 */

import { cookies } from "next/headers";

export const COOKIE_SESION = "kfg_auth";

export interface SesionServidor {
  usuario: string;
  rol: string;
}

interface Claims {
  user?: unknown;
  role?: unknown;
  exp?: unknown;
}

function decodificarClaims(token: string): Claims | null {
  const partes = token.split(".");
  if (partes.length !== 3) return null;
  try {
    const base64 = partes[1].replace(/-/g, "+").replace(/_/g, "/");
    const relleno = base64.padEnd(
      base64.length + ((4 - (base64.length % 4)) % 4),
      "=",
    );
    return JSON.parse(
      Buffer.from(relleno, "base64").toString("utf8"),
    ) as Claims;
  } catch {
    return null;
  }
}

/** Token en crudo, para inyectarlo como `Authorization: Bearer`. */
export async function leerTokenServidor(): Promise<string | null> {
  const almacen = await cookies();
  return almacen.get(COOKIE_SESION)?.value ?? null;
}

/**
 * Identidad de la sesión vigente, o `null` si no hay ninguna.
 *
 * Un token caducado se trata como ausencia de sesión: mostrar el nombre de quien
 * ya no puede operar solo confundiría, y la siguiente petición al backend
 * devolvería un 401 de todos modos.
 */
export async function leerSesionServidor(): Promise<SesionServidor | null> {
  const token = await leerTokenServidor();
  if (!token) return null;

  const claims = decodificarClaims(token);
  if (!claims) return null;

  if (typeof claims.exp === "number" && claims.exp * 1000 <= Date.now()) {
    return null;
  }

  return {
    usuario: typeof claims.user === "string" ? claims.user : "",
    rol: typeof claims.role === "string" ? claims.role : "",
  };
}
