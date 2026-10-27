import type { Metadata } from "next";

import { Marco } from "@/components/layout/Marco";
import { ProveedorSesion } from "@/components/providers/ProveedorSesion";
import { ProveedorAvisos } from "@/components/ui/Toast";
import { leerSesionServidor } from "@/utils/sesionServidor";

import "./globals.css";

export const metadata: Metadata = {
  title: "KFG Risk Architect",
  description:
    "Plataforma de originación y riesgo de crédito de Kaizen Financial Group.",
};

/**
 * Layout raíz.
 *
 * Resuelve la identidad en el servidor —leyendo la cookie `HttpOnly`— y la pasa
 * al proveedor ya hecha: el navegador nunca ve el token, y no hay un primer
 * render «sin sesión» que corregir después, que era el precio de guardarla en el
 * almacenamiento del navegador.
 *
 * Los proveedores y el marco se montan por encima del enrutador: al navegar
 * entre módulos no se vuelven a montar, así que los avisos en curso sobreviven
 * al cambio de página.
 *
 * `Marco` decide si la pantalla lleva barra lateral: el acceso se sirve solo con
 * su formulario, porque no hay sesión con la que navegar a ningún módulo.
 */
export default async function RootLayout({ children }: LayoutProps<"/">) {
  const sesion = await leerSesionServidor();

  return (
    <html lang="es" className="h-full antialiased">
      <body className="min-h-full">
        <ProveedorSesion sesion={sesion}>
          <ProveedorAvisos>
            <Marco>{children}</Marco>
          </ProveedorAvisos>
        </ProveedorSesion>
      </body>
    </html>
  );
}
