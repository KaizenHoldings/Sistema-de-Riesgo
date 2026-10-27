"use client";

/**
 * Panel de control de Configuración.
 *
 * Portada de la administración: no edita nada por sí misma, reparte hacia las
 * pantallas que sí lo hacen. Existe porque los ajustes se habían ido agrupando
 * en una sola pantalla de pestañas, y desde el menú no se veía qué había dentro.
 *
 * El rol se comprueba aquí además de en la barra lateral —que solo deja de
 * pintar el enlace— y de en el backend, que es quien realmente autoriza: llegar
 * por URL a esta ruta sin ser Superadmin no debe mostrar el panel.
 */

import Link from "next/link";

import { EncabezadoPagina } from "@/components/layout/MarcoApp";
import { useSesion } from "@/components/providers/ProveedorSesion";
import { SinResultados } from "@/components/ui/Alerta";

/** Recetas institucionales de la tarjeta, en un solo sitio. */
const TARJETA =
  "rounded-xl border border-borde bg-white shadow-sm p-6 cursor-pointer " +
  "transition hover:bg-lienzo";

interface Opcion {
  href: string;
  icono: string;
  titulo: string;
  descripcion: string;
  detalle: string;
}

const OPCIONES: Opcion[] = [
  {
    href: "/admin?seccion=usuarios",
    icono: "▣",
    titulo: "Gestión de usuarios",
    descripcion: "Altas, roles y contraseñas de las cuentas de acceso.",
    detalle: "El rol decide qué etapa del circuito puede firmar cada persona.",
  },
  {
    href: "/admin?seccion=corp",
    icono: "◈",
    titulo: "Parámetros de riesgo corporativo",
    descripcion:
      "Pesos de liquidez, solvencia y cobertura, boost Kaizen y pricing.",
    detalle: "Gobiernan el scoring de toda la cartera corporativa.",
  },
  {
    href: "/admin?seccion=auto",
    icono: "◆",
    titulo: "Parámetros de riesgo automotriz",
    descripcion:
      "Pesos de capacidad, LTV y estabilidad laboral, con su tasa base.",
    detalle: "Gobiernan el scoring de la cartera automotriz.",
  },
];

export default function ConfiguracionPage() {
  const { sesion } = useSesion();

  if (!sesion || sesion.rol !== "Superadmin") {
    return (
      <>
        <EncabezadoPagina
          icono="⚙"
          miga="Inicio / Configuración"
          titulo="Acceso denegado"
          bajada="Esta sección está reservada a la administración de la plataforma."
        />
        <SinResultados mensaje="Acceso denegado: su rol no tiene acceso al panel de configuración." />
      </>
    );
  }

  return (
    <>
      <EncabezadoPagina
        icono="⚙"
        miga="Inicio / Configuración"
        titulo="Panel de configuración"
        bajada="Cuentas de acceso y parámetros del motor de riesgo de las dos líneas de producto."
      />

      <section
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3"
        aria-label="Opciones de configuración"
      >
        {OPCIONES.map((opcion) => (
          <Link key={opcion.href} href={opcion.href} className={TARJETA}>
            <div className="flex items-start gap-3">
              <span className="text-lg text-kaizen-600" aria-hidden>
                {opcion.icono}
              </span>
              <div className="min-w-0">
                <h2 className="text-sm font-bold text-kaizen-900">
                  {opcion.titulo}
                </h2>
                <p className="mt-2 text-sm text-tinta">{opcion.descripcion}</p>
                <p className="mt-2 text-xs text-tinta-suave">{opcion.detalle}</p>
              </div>
            </div>
          </Link>
        ))}
      </section>
    </>
  );
}
