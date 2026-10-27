"use client";

/**
 * Portada de Gestión.
 *
 * Reparte hacia las tres pantallas con las que trabaja el área comercial. Antes
 * eran un desplegable del menú; como pantalla caben la descripción de cada una
 * y el orden en que se usan —dar de alta al cliente, y solo después presentar su
 * solicitud—, que un menú plegable no puede explicar.
 *
 * El rol se comprueba aquí además de en la barra lateral, que solo deja de
 * pintar el enlace; quien autoriza de verdad es el backend en cada ruta.
 */

import Link from "next/link";

import { EncabezadoPagina } from "@/components/layout/MarcoApp";
import { useSesion } from "@/components/providers/ProveedorSesion";
import { SinResultados } from "@/components/ui/Alerta";

const ROLES_GESTION = ["Comercial", "Superadmin"];

/** Receta institucional de la tarjeta, en un solo sitio. */
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
    href: "/clients",
    icono: "▣",
    titulo: "Clientes",
    descripcion: "Padrón de clientes con su estado KYC y su documentación.",
    detalle: "Consulta, ficha del cliente y carga de recaudos.",
  },
  {
    href: "/clients/new",
    icono: "+",
    titulo: "Registrar cliente",
    descripcion: "Alta de una persona natural o jurídica en el padrón.",
    detalle: "Nace como Prospecto; Cumplimiento aprueba su KYC.",
  },
  {
    href: "/applications/new",
    icono: "+",
    titulo: "Nueva solicitud",
    descripcion: "Originación de un crédito corporativo o automotriz.",
    detalle: "El expediente entra al circuito por Cumplimiento.",
  },
  {
    href: "/status-creditos",
    icono: "≡",
    titulo: "Status de créditos",
    descripcion: "Seguimiento de todas las solicitudes presentadas.",
    detalle: "Etapa y dictamen de cada una, sin acciones de circuito.",
  },
];

export default function GestionPage() {
  const { sesion } = useSesion();

  if (!sesion || !ROLES_GESTION.includes(sesion.rol)) {
    return (
      <>
        <EncabezadoPagina
          icono="▣"
          miga="Inicio / Gestión"
          titulo="Acceso denegado"
          bajada="Esta sección corresponde al área comercial."
        />
        <SinResultados mensaje="Acceso denegado: su rol no tiene acceso al módulo de gestión." />
      </>
    );
  }

  return (
    <>
      <EncabezadoPagina
        icono="▣"
        miga="Inicio / Gestión"
        titulo="Gestión comercial"
        bajada="Padrón de clientes y originación de solicitudes de crédito."
      />

      <section
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3"
        aria-label="Opciones de gestión"
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
