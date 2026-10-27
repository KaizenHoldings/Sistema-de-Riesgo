/**
 * Entrega al navegador un binario que ya está en memoria.
 *
 * Los ficheros llegan por `fetch` —el JWT viaja en una cabecera y una navegación
 * normal no la lleva—, así que la descarga se provoca con un enlace temporal
 * sobre un `blob:`. La URL se revoca en cuanto el clic ha ocurrido: cada una
 * retiene su blob en memoria hasta que se libera.
 */

import type { Descarga } from "@/utils/apiClient";

export function guardarComo({ contenido, nombre }: Descarga): void {
  const url = URL.createObjectURL(contenido);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombre;
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  URL.revokeObjectURL(url);
}
