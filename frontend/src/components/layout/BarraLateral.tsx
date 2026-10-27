"use client";

/**
 * Barra lateral persistente.
 *
 * Reproduce el degradado azul de la interfaz de Streamlit para que el salto
 * entre las dos no se note mientras conviven. Marca el módulo activo con el
 * prefijo de la ruta, no con la igualdad exacta, de modo que una ficha de
 * detalle mantenga iluminado su módulo.
 *
 * Los módulos de alta —clientes y solicitudes— se agrupan bajo «Gestión», un
 * grupo plegable que se abre solo cuando la ruta actual cae dentro de él.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useSesion } from "@/components/providers/ProveedorSesion";
import { useEvaluacionesPendientes } from "@/hooks/useEvaluacionesPendientes";
import { useSalud } from "@/hooks/useSalud";

interface Modulo {
  href: string;
  etiqueta: string;
  icono: string;
  descripcion: string;
  roles?: string[];
}

/**
 * Quien origina: el area comercial da de alta clientes y solicitudes, y
 * Superadmin conserva el acceso a todo. Los firmantes del circuito —Legal,
 * Riesgo, Cumplimiento y Comite— evaluan lo que ya esta presentado, asi que el
 * modulo de alta no les corresponde.
 */
const ROLES_GESTION = ["Comercial", "Superadmin"];

const ROLES_ORIGEN = [
  "Comercial",
  "Compliance",
  "Legal",
  "Riesgo",
  "Comité",
  "Superadmin",
];

const ENTRADAS: Modulo[] = [
  {
    href: "/dashboard",
    etiqueta: "Tablero",
    icono: "◆",
    descripcion: "Indicadores de originación y cartera",
  },
  {
    // Portada del área comercial: el menú lleva a una sola pantalla y desde
    // ella se entra a clientes, altas y solicitudes.
    href: "/gestion",
    etiqueta: "Gestión",
    icono: "▣",
    descripcion: "Clientes y originación",
    roles: ROLES_GESTION,
  },
  {
    href: "/status-creditos",
    etiqueta: "Status de créditos",
    icono: "≡",
    descripcion: "Seguimiento de todas las solicitudes",
    roles: ROLES_GESTION,
  },
  {
    href: "/evaluations",
    etiqueta: "Evaluaciones",
    icono: "◈",
    descripcion: "Circuito de crédito y comité",
    roles: ROLES_ORIGEN,
  },
  {
    href: "/portfolio",
    etiqueta: "Cartera y Cobranzas",
    icono: "▦",
    descripcion: "Caja mixta, pagos, arqueo y cartera",
    roles: ["Comité", "Cobranzas", "Superadmin"],
  },
  {
    href: "/configuracion",
    etiqueta: "Configuración",
    icono: "⚙",
    descripcion: "Motor de riesgo y usuarios",
    roles: ["Superadmin"],
  },
];

export function BarraLateral() {
  const ruta = usePathname();
  const { sesion, cerrar } = useSesion();
  const { datos: salud, error: errorSalud, cargando: comprobando } = useSalud();
  const { hayPendientes, total: totalPendientes } = useEvaluacionesPendientes();

  // El rol sale de la sesion del proveedor, la misma que resuelve el layout en
  // el servidor leyendo la cookie.
  const permitido = (roles?: string[]) =>
    !roles || Boolean(sesion && roles.includes(sesion.rol));

  // La comprobacion de rol no sustituye a la del backend, que vuelve a
  // exigirlo en cada ruta; aqui solo se deja de pintar lo que no compete.
  const entradas = ENTRADAS.filter((entrada) => permitido(entrada.roles));

  // Se ilumina el enlace más específico que contiene la ruta, para que una
  // ficha de detalle mantenga encendido su módulo.
  const activo = entradas
    .map((modulo) => modulo.href)
    .filter((href) => ruta === href || ruta.startsWith(`${href}/`))
    .sort((a, b) => b.length - a.length)[0];

  return (
    <aside className="flex w-full shrink-0 flex-col bg-gradient-to-b from-kaizen-900 via-kaizen-800 to-kaizen-600 text-white lg:h-screen lg:w-72 lg:sticky lg:top-0">
      <div className="border-b border-white/10 px-6 py-6">
        <p className="text-lg font-bold tracking-tight">KFG Risk Architect</p>
        <p className="mt-1 text-xs text-white/70">Kaizen Financial Group</p>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-5" aria-label="Módulos">
        {entradas.map((entrada) => (
          <EnlaceModulo
            key={entrada.href}
            modulo={entrada}
            activo={entrada.href === activo}
            conPuntoRojo={entrada.href === "/evaluations" && hayPendientes}
            conteo={entrada.href === "/evaluations" ? totalPendientes : undefined}
          />
        ))}
      </nav>

      <div className="space-y-3 border-t border-white/10 px-6 py-5 text-xs">
        <EstadoServicio
          comprobando={comprobando}
          version={salud?.version ?? null}
          caido={errorSalud !== null}
        />

        {sesion ? (
          <div className="space-y-2">
            <p className="truncate text-white/80" title={sesion.usuario}>
              {sesion.usuario}
            </p>
            <p className="text-white/50">{sesion.rol}</p>
            <button
              type="button"
              onClick={cerrar}
              className="w-full rounded-lg border border-white/25 px-3 py-1.5 font-medium text-white/85 transition hover:border-white/60 hover:text-white"
            >
              Cerrar sesión
            </button>
          </div>
        ) : (
          <Link
            href="/login"
            className="block rounded-lg border border-white/25 px-3 py-1.5 text-center font-medium text-white/85 transition hover:border-white/60 hover:text-white"
          >
            Iniciar sesión
          </Link>
        )}
      </div>
    </aside>
  );
}

function EnlaceModulo({
  modulo,
  activo,
  conPuntoRojo = false,
  conteo,
}: {
  modulo: Modulo;
  activo: boolean;
  conPuntoRojo?: boolean;
  conteo?: number;
}) {
  return (
    <Link
      href={modulo.href}
      aria-current={activo ? "page" : undefined}
      className={`relative flex items-start gap-3 rounded-lg px-3 py-2.5 transition ${
        activo
          ? "bg-white/15 text-white shadow-inner"
          : "text-white/75 hover:bg-white/10 hover:text-white"
      }`}
    >
      <span aria-hidden className="mt-0.5 text-sm">
        {modulo.icono}
      </span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center justify-between gap-1">
          <span className="block text-sm font-semibold">{modulo.etiqueta}</span>
          {conPuntoRojo && (
            <span
              className="inline-flex items-center gap-1.5"
              title={`${conteo ?? ""} evaluación(es) pendiente(s)`}
            >
              <span className="relative flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75"></span>
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500 ring-2 ring-kaizen-900"></span>
              </span>
              {conteo && conteo > 0 ? (
                <span className="rounded-full bg-red-500/25 px-1.5 py-0.5 text-[10px] font-bold text-red-200">
                  {conteo}
                </span>
              ) : null}
            </span>
          )}
        </span>
        <span className="block text-xs text-white/60">{modulo.descripcion}</span>
      </span>
    </Link>
  );
}

function EstadoServicio({
  comprobando,
  version,
  caido,
}: {
  comprobando: boolean;
  version: string | null;
  caido: boolean;
}) {
  if (comprobando) {
    return <p className="text-white/50">Comprobando el servicio…</p>;
  }
  if (caido) {
    return (
      <p className="flex items-center gap-2 text-white/80">
        <span className="h-2 w-2 rounded-full bg-rojo-fondo" aria-hidden />
        Backend no disponible
      </p>
    );
  }
  return (
    <p className="flex items-center gap-2 text-white/70">
      <span className="h-2 w-2 rounded-full bg-verde-fondo" aria-hidden />
      API {version ?? "activa"}
    </p>
  );
}
