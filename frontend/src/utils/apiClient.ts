/**
 * Cliente HTTP único contra el backend FastAPI.
 *
 * Todas las peticiones del frontend pasan por aquí, y solo por aquí, de modo que
 * la inyección del JWT y la traducción de los errores del backend ocurren en un
 * único sitio. Ninguna vista debería llamar a `fetch` directamente.
 *
 * El backend distingue tres familias de error de negocio —404 inexistente, 409
 * transición ilegítima y 422 datos inválidos— y las emite con formatos
 * distintos: `detail` es una cadena en las dos primeras y una lista de campos en
 * la tercera. `ApiError` normaliza ambas para que la interfaz pueda mostrar un
 * aviso legible sin tener que inspeccionar la forma de la respuesta.
 *
 * **Este módulo es el transporte del navegador.** No maneja el JWT ni podría:
 * el token vive en una cookie `HttpOnly` que el código de página no puede leer.
 * Toda petición sale hacia `/api/proxy/...`, el navegador adjunta la cookie por
 * ser el mismo origen y el manejador del proxy la traduce a `Authorization`. El
 * equivalente para componentes y acciones de servidor es `utils/apiServer.ts`,
 * que lee la cookie con `cookies()` y llama al backend directamente.
 */

/**
 * Prefijo del proxy autenticado.
 *
 * Una ruta del backend como `/api/v1/clientes` se pide al navegador como
 * `/api/proxy/api/v1/clientes`; el manejador reconstruye la original y le añade
 * el token. Los sitios de llamada siguen escribiendo la ruta del backend y no
 * saben nada de esto.
 */
const PREFIJO_PROXY = "/api/proxy";

/** Origen contra el que se resuelven las rutas relativas. */
function origen(): string {
  if (typeof window !== "undefined") return window.location.origin;
  return "http://127.0.0.1:3000";
}

/** Un campo señalado por la validación de Pydantic. */
export interface CampoInvalido {
  campo: string;
  mensaje: string;
}

interface DetalleValidacion {
  loc?: unknown[];
  msg?: string;
}

/** Error devuelto por el backend, ya normalizado. */
export class ApiError extends Error {
  readonly status: number;
  readonly campos: CampoInvalido[];

  constructor(status: number, mensaje: string, campos: CampoInvalido[] = []) {
    super(mensaje);
    this.name = "ApiError";
    this.status = status;
    this.campos = campos;
  }

  /** 404: el recurso no existe o fue dado de baja. */
  get esNoEncontrado(): boolean {
    return this.status === 404;
  }

  /** 409: el estado actual del expediente no admite la operación. */
  get esConflicto(): boolean {
    return this.status === 409;
  }

  /** 422: faltan datos obligatorios o no son del tipo esperado. */
  get esValidacion(): boolean {
    return this.status === 422;
  }

  /** 0: el servidor no respondió (caído, CORS o red). */
  get esDeRed(): boolean {
    return this.status === 0;
  }
}

/** Encabezado que la interfaz muestra sobre el aviso, según el tipo de fallo. */
export function titularDeError(error: ApiError): string {
  if (error.esDeRed) return "Sin conexión con el servicio";
  if (error.esNoEncontrado) return "No encontrado";
  if (error.esConflicto) return "Transición no permitida";
  if (error.esValidacion) return "Datos incompletos";
  if (error.status === 401) return "Sesión expirada";
  if (error.status === 403) return "Sin permiso";
  return "Error del servicio";
}

function extraerCampos(detalle: unknown): CampoInvalido[] {
  if (!Array.isArray(detalle)) return [];
  return detalle.map((item) => {
    const d = item as DetalleValidacion;
    const partes = Array.isArray(d.loc) ? d.loc.slice(1) : [];
    return {
      campo: partes.length > 0 ? partes.join(".") : "cuerpo",
      mensaje: typeof d.msg === "string" ? d.msg : "valor no válido",
    };
  });
}

/**
 * Construye el `ApiError` a partir del cuerpo de error ya leído.
 *
 * Lo comparten `fetch` y `XMLHttpRequest`: el segundo hace falta para conocer el
 * progreso de una subida, que `fetch` no expone, y sería un error que cada uno
 * tradujera los fallos del backend a su manera.
 */
function errorDesde(status: number, texto: string, estado = ""): ApiError {
  let cuerpo: unknown = null;
  try {
    cuerpo = JSON.parse(texto);
  } catch {
    // Algunas respuestas de error llegan vacías o en texto plano.
  }

  const detalle = (cuerpo as { detail?: unknown } | null)?.detail;

  if (typeof detalle === "string" && detalle.length > 0) {
    return new ApiError(status, detalle);
  }

  const campos = extraerCampos(detalle);
  if (campos.length > 0) {
    const resumen = campos.map((c) => `${c.campo}: ${c.mensaje}`).join("; ");
    return new ApiError(status, resumen, campos);
  }

  return new ApiError(status, `El servicio respondió ${status} ${estado}`.trim());
}

async function construirError(respuesta: Response): Promise<ApiError> {
  let texto = "";
  try {
    texto = await respuesta.text();
  } catch {
    // Cuerpo ilegible: queda el código de estado.
  }
  return errorDesde(respuesta.status, texto, respuesta.statusText);
}

/** Valores admitidos en la cadena de consulta; los nulos se omiten. */
export type Query = Record<string, string | number | boolean | null | undefined>;

const MENSAJE_SIN_BACKEND =
  "No se pudo contactar con el backend. Compruebe que el servicio FastAPI " +
  "está en marcha y que BACKEND_ORIGIN apunta a su dirección.";

interface Opciones {
  query?: Query;
  body?: unknown;
  signal?: AbortSignal;
}

function construirUrl(ruta: string, query?: Query): string {
  const camino = ruta.startsWith("/") ? ruta : `/${ruta}`;
  const url = new URL(`${origen()}${PREFIJO_PROXY}${camino}`);
  if (query) {
    for (const [clave, valor] of Object.entries(query)) {
      if (valor === null || valor === undefined || valor === "") continue;
      url.searchParams.set(clave, String(valor));
    }
  }
  return url.toString();
}

async function peticion<T>(
  metodo: "GET" | "POST" | "PUT" | "DELETE",
  ruta: string,
  opciones: Opciones = {},
): Promise<T> {
  const cabeceras: Record<string, string> = { Accept: "application/json" };

  // No se toca la autorización: el token está en una cookie que este código no
  // puede leer, y es el proxy quien la convierte en la cabecera `Authorization`.
  if (opciones.body !== undefined) {
    cabeceras["Content-Type"] = "application/json";
  }

  let respuesta: Response;
  try {
    respuesta = await fetch(construirUrl(ruta, opciones.query), {
      method: metodo,
      headers: cabeceras,
      body: opciones.body === undefined ? undefined : JSON.stringify(opciones.body),
      signal: opciones.signal,
      cache: "no-store",
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error; // La cancelación no es un fallo: la gestiona el hook.
    }
    throw new ApiError(0, MENSAJE_SIN_BACKEND);
  }

  if (respuesta.status === 401) {
    // La cookie la borra el servidor; aquí solo se informa. El middleware
    // devolverá al acceso en cuanto se navegue.
    throw new ApiError(401, "La sesión ha caducado. Vuelva a iniciar sesión.");
  }

  if (!respuesta.ok) {
    throw await construirError(respuesta);
  }

  if (respuesta.status === 204) {
    return undefined as T;
  }

  return (await respuesta.json()) as T;
}

/**
 * Envía un formulario codificado en lugar de JSON.
 *
 * Lo necesita `/token`, que sigue el contrato OAuth2 y espera
 * `application/x-www-form-urlencoded`. Pasa por aquí igual que el resto para no
 * duplicar la traducción de errores en la pantalla de acceso.
 */
async function peticionFormulario<T>(
  ruta: string,
  campos: Record<string, string>,
  signal?: AbortSignal,
): Promise<T> {
  const cuerpo = new URLSearchParams(campos);

  let respuesta: Response;
  try {
    respuesta = await fetch(construirUrl(ruta), {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: cuerpo.toString(),
      signal,
      cache: "no-store",
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    throw new ApiError(0, MENSAJE_SIN_BACKEND);
  }

  if (!respuesta.ok) {
    throw await construirError(respuesta);
  }
  return (await respuesta.json()) as T;
}

/**
 * Envía un archivo como `multipart/form-data`.
 *
 * No fija `Content-Type`: lo pone el navegador junto con el `boundary`, y
 * escribirlo a mano rompe el análisis del cuerpo en el servidor.
 */
async function peticionMultiparte<T>(
  ruta: string,
  formulario: FormData,
  signal?: AbortSignal,
): Promise<T> {
  const cabeceras: Record<string, string> = { Accept: "application/json" };
  let respuesta: Response;
  try {
    respuesta = await fetch(construirUrl(ruta), {
      method: "POST",
      headers: cabeceras,
      body: formulario,
      signal,
      cache: "no-store",
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(0, MENSAJE_SIN_BACKEND);
  }

  if (respuesta.status === 401) {
    // La cookie la borra el servidor; aquí solo se informa. El middleware
    // devolverá al acceso en cuanto se navegue.
    throw new ApiError(401, "La sesión ha caducado. Vuelva a iniciar sesión.");
  }
  if (!respuesta.ok) throw await construirError(respuesta);
  return (await respuesta.json()) as T;
}

/** Archivo binario devuelto por la API, con el nombre que propone el servidor. */
/**
 * Envía un formulario multiparte informando de cuánto lleva subido.
 *
 * Usa `XMLHttpRequest` y no `fetch` por una sola razón: `fetch` no expone el
 * progreso de subida, y una carga de varios megabytes sin señal de avance
 * parece colgada. El resto —cookie del mismo origen, prefijo del proxy,
 * traducción del error— es idéntico al de las demás peticiones.
 *
 * `alProgreso` recibe la fracción enviada, de 0 a 1. Si el servidor no informa
 * del total —`lengthComputable` falso—, no se llama: la pantalla decide
 * entonces mostrar un avance indeterminado en lugar de inventar un porcentaje.
 */
function subirConProgreso<T>(
  ruta: string,
  formulario: FormData,
  alProgreso?: (fraccion: number) => void,
): Promise<T> {
  return new Promise<T>((resolver, rechazar) => {
    const peticion = new XMLHttpRequest();
    peticion.open("POST", construirUrl(ruta));
    peticion.setRequestHeader("Accept", "application/json");
    // El `Content-Type` lo pone el navegador junto con el `boundary`.

    peticion.upload.onprogress = (evento) => {
      if (evento.lengthComputable && alProgreso) {
        alProgreso(evento.loaded / evento.total);
      }
    };

    peticion.onload = () => {
      if (peticion.status === 401) {
        rechazar(new ApiError(401, "La sesión ha caducado. Vuelva a iniciar sesión."));
        return;
      }
      if (peticion.status < 200 || peticion.status >= 300) {
        rechazar(errorDesde(peticion.status, peticion.responseText, peticion.statusText));
        return;
      }
      try {
        resolver(JSON.parse(peticion.responseText) as T);
      } catch {
        rechazar(new ApiError(peticion.status, "La respuesta del servicio no es JSON."));
      }
    };

    peticion.onerror = () => rechazar(new ApiError(0, MENSAJE_SIN_BACKEND));
    peticion.onabort = () => rechazar(new ApiError(0, "Carga cancelada."));

    peticion.send(formulario);
  });
}

export interface Descarga {
  contenido: Blob;
  nombre: string;
}

/**
 * Repara el nombre de un adjunto cuyo `Content-Disposition` viaja en UTF-8 sin
 * declararlo.
 *
 * Las cabeceras HTTP se leen como ISO-8859-1, así que un nombre con acentos
 * llega convertido en caracteres sueltos —«Cédula» se ve como «CÃ©dula»—. Si los
 * bytes de esa lectura resultan ser UTF-8 válido, es que el original lo era y se
 * recupera; si no lo son, el nombre ya era correcto y se deja intacto.
 */
function repararNombre(nombre: string): string {
  try {
    const bytes = Uint8Array.from(nombre, (caracter) => caracter.charCodeAt(0) & 0xff);
    return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch {
    return nombre;
  }
}

/**
 * Descarga un binario —un acta en PDF, un documento del repositorio—.
 *
 * No basta con apuntar un enlace a la ruta: el JWT viaja en una cabecera y una
 * navegación normal no la lleva. Se pide con `fetch`, se toma el nombre de
 * `Content-Disposition` y quien llama decide qué hacer con el blob.
 */
async function descargar(ruta: string, signal?: AbortSignal): Promise<Descarga> {
  const cabeceras: Record<string, string> = {};
  let respuesta: Response;
  try {
    respuesta = await fetch(construirUrl(ruta), {
      headers: cabeceras,
      signal,
      cache: "no-store",
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(0, MENSAJE_SIN_BACKEND);
  }

  if (respuesta.status === 401) {
    // La cookie la borra el servidor; aquí solo se informa. El middleware
    // devolverá al acceso en cuanto se navegue.
    throw new ApiError(401, "La sesión ha caducado. Vuelva a iniciar sesión.");
  }
  if (!respuesta.ok) throw await construirError(respuesta);

  const disposicion = respuesta.headers.get("Content-Disposition") ?? "";
  const coincidencia = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposicion);
  const nombre = coincidencia
    ? repararNombre(decodeURIComponent(coincidencia[1].trim()))
    : "descarga";

  return { contenido: await respuesta.blob(), nombre };
}

export const apiClient = {
  get: <T>(ruta: string, opciones?: Opciones) => peticion<T>("GET", ruta, opciones),
  post: <T>(ruta: string, body?: unknown, opciones?: Opciones) =>
    peticion<T>("POST", ruta, { ...opciones, body }),
  put: <T>(ruta: string, body?: unknown, opciones?: Opciones) =>
    peticion<T>("PUT", ruta, { ...opciones, body }),
  delete: <T>(ruta: string, opciones?: Opciones) =>
    peticion<T>("DELETE", ruta, opciones),
  postForm: peticionFormulario,
  postMultipart: peticionMultiparte,
  subirConProgreso,
  descargar,
};
