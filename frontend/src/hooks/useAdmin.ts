"use client";

/**
 * Configuración del motor y cuentas de acceso.
 *
 * Ambos recursos están reservados a Superadmin en el backend: una respuesta 403
 * aquí no es un fallo, es la respuesta correcta para el resto de roles, y la
 * vista la presenta como tal.
 */

import { useCallback } from "react";

import { useApiQuery, type EstadoConsulta } from "@/hooks/useApiQuery";
import { apiClient } from "@/utils/apiClient";
import type { ConfigParametro, UsuarioCuenta } from "@/types/api";

export function useParametros(): EstadoConsulta<ConfigParametro[]> {
  const obtener = useCallback(
    (signal: AbortSignal) =>
      apiClient.get<ConfigParametro[]>("/api/v1/config/parametros", { signal }),
    [],
  );
  return useApiQuery(obtener, []);
}

export function guardarParametros(
  cambios: Array<{ clave: string; valor: number }>,
): Promise<ConfigParametro[]> {
  return apiClient.put<ConfigParametro[]>("/api/v1/config/parametros", cambios);
}

export function useUsuarios(): EstadoConsulta<UsuarioCuenta[]> {
  const obtener = useCallback(
    (signal: AbortSignal) =>
      apiClient.get<UsuarioCuenta[]>("/api/v1/usuarios", { signal }),
    [],
  );
  return useApiQuery(obtener, []);
}

export function guardarUsuario(
  usuario: string,
  contrasena: string,
  rol: string,
): Promise<UsuarioCuenta> {
  return apiClient.post<UsuarioCuenta>("/api/v1/usuarios", {
    usuario,
    contrasena,
    rol,
  });
}

/**
 * Restablece la contraseña. Devuelve la cuenta afectada en lugar de nada: el
 * endpoint responde 204, y sin un valor de vuelta quien llama no puede
 * distinguir el éxito del fallo sin esperar a que el estado se repinte.
 */
export async function cambiarContrasena(
  usuario: string,
  contrasena: string,
): Promise<string> {
  await apiClient.put<void>(
    `/api/v1/usuarios/${encodeURIComponent(usuario)}/contrasena`,
    { contrasena },
  );
  return usuario;
}
