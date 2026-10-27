/**
 * Estado del formulario de acceso.
 *
 * Vive fuera de `auth.ts` porque un fichero marcado con `"use server"` solo
 * puede exportar funciones asíncronas: cualquier otro valor exportado —una
 * constante, un objeto— hace fallar el módulo en tiempo de ejecución, y la
 * compilación no lo detecta.
 */

export interface EstadoAcceso {
  error: string | null;
}

export const ESTADO_INICIAL: EstadoAcceso = { error: null };
