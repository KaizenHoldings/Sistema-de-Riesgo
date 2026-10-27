/**
 * Transporte del servidor contra el backend FastAPI.
 *
 * Gemelo de `apiClient.ts` para componentes y acciones de servidor. La
 * diferencia está en de dónde sale el token: aquí se lee la cookie `HttpOnly`
 * con `cookies()` y se inyecta como `Authorization`, sin pasar por el proxy —que
 * existe solo porque el navegador no puede hacer esto—.
 *
 * Importar este módulo desde un componente de cliente rompe la compilación, y es
 * lo correcto: `next/headers` no existe en el navegador.
 */

import { ApiError, type Query } from "@/utils/apiClient";
import { BACKEND_ORIGIN } from "@/utils/backend";
import { leerTokenServidor } from "@/utils/sesionServidor";

function construirUrl(ruta: string, query?: Query): string {
  const camino = ruta.startsWith("/") ? ruta : `/${ruta}`;
  const url = new URL(`${BACKEND_ORIGIN}${camino}`);
  if (query) {
    for (const [clave, valor] of Object.entries(query)) {
      if (valor === null || valor === undefined || valor === "") continue;
      url.searchParams.set(clave, String(valor));
    }
  }
  return url.toString();
}

/**
 * Lectura autenticada desde el servidor.
 *
 * Sin sesión no se intenta la llamada: se lanza el mismo `ApiError` 401 que
 * produciría el backend, para que quien llame no tenga que distinguir los casos.
 */
export async function obtenerDelServidor<T>(
  ruta: string,
  query?: Query,
): Promise<T> {
  const token = await leerTokenServidor();
  if (!token) {
    throw new ApiError(401, "No hay sesión iniciada.");
  }

  let respuesta: Response;
  try {
    respuesta = await fetch(construirUrl(ruta, query), {
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      0,
      "No se pudo contactar con el backend desde el servidor de Next.",
    );
  }

  if (!respuesta.ok) {
    let detalle: unknown = null;
    try {
      detalle = ((await respuesta.json()) as { detail?: unknown }).detail;
    } catch {
      // Respuesta de error sin cuerpo JSON: basta con el código.
    }
    throw new ApiError(
      respuesta.status,
      typeof detalle === "string"
        ? detalle
        : `El servicio respondió ${respuesta.status}.`,
    );
  }

  if (respuesta.status === 204) return undefined as T;
  return (await respuesta.json()) as T;
}
