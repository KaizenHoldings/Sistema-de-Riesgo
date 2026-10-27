"use client";

/**
 * Pantalla de acceso.
 *
 * El formulario envía a una acción de servidor: la credencial no pasa por el
 * código de página, y el token que devuelve el backend se guarda en una cookie
 * `HttpOnly` sin llegar nunca al navegador.
 *
 * El error de credenciales se muestra en línea, junto al formulario, y no como
 * aviso emergente: el sitio donde hay que corregirlo está a la vista.
 */

import { useRouter } from "next/navigation";
import { useActionState, useEffect } from "react";
import { useFormStatus } from "react-dom";

import { iniciarSesion } from "@/app/actions/auth";
import { ESTADO_INICIAL } from "@/app/actions/estadoAcceso";
import { useSesion } from "@/components/providers/ProveedorSesion";
import { Girador } from "@/components/ui/Skeleton";

const CAMPO =
  "w-full rounded-lg border border-borde bg-white px-3 py-2 text-sm text-tinta " +
  "outline-none transition focus:border-kaizen-600 focus:ring-2 focus:ring-kaizen-600/20";

export default function AccesoPage() {
  const router = useRouter();
  const { sesion } = useSesion();
  const [estado, enviar] = useActionState(iniciarSesion, ESTADO_INICIAL);

  // La acción revalida el layout, así que la sesión aparece por sí sola en
  // cuanto la cookie está puesta; entonces esta pantalla ya no hace falta.
  useEffect(() => {
    if (sesion) router.replace("/dashboard");
  }, [sesion, router]);

  return (
    <div className="w-full">
      <div className="rounded-xl border border-borde bg-white p-8 shadow-sm">
        {/*
          Las extensiones que anotan encabezados —inspectores de accesibilidad o
          de SEO— añaden atributos como `data-heading-tag` al DOM antes de que
          React hidrate, y React los reporta como desajuste. El título es texto
          fijo, así que aquí no hay ningún desajuste legítimo que ocultar.
        */}
        <h1
          className="text-xl font-bold text-kaizen-900"
          suppressHydrationWarning={true}
        >
          Acceso institucional
        </h1>
        <p className="mt-1.5 text-sm text-tinta-suave">
          Identifíquese con sus credenciales de KFG Risk Architect.
        </p>

        <form action={enviar} className="mt-6 space-y-4">
          <label className="block">
            <span className="text-xs font-semibold tracking-wide text-tinta-suave uppercase">
              Usuario
            </span>
            <input
              type="email"
              name="usuario"
              autoComplete="username"
              required
              className={`mt-1.5 ${CAMPO}`}
            />
          </label>

          <label className="block">
            <span className="text-xs font-semibold tracking-wide text-tinta-suave uppercase">
              Contraseña
            </span>
            <input
              type="password"
              name="contrasena"
              autoComplete="current-password"
              required
              className={`mt-1.5 ${CAMPO}`}
            />
          </label>

          {estado.error && (
            <p
              role="alert"
              className="rounded-lg border border-rojo-trazo/30 bg-rojo-fondo px-4 py-3 text-sm text-rojo-trazo"
            >
              {estado.error}
            </p>
          )}

          <BotonEntrar />
        </form>
      </div>
    </div>
  );
}

/**
 * Botón de envío.
 *
 * `useFormStatus` solo informa dentro del formulario que lo contiene, por eso va
 * en su propio componente.
 */
function BotonEntrar() {
  const { pending } = useFormStatus();

  return (
    <button
      type="submit"
      disabled={pending}
      className="flex w-full items-center justify-center gap-2 rounded-lg bg-kaizen-800 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-kaizen-900 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {pending && <Girador />}
      {pending ? "Verificando…" : "Entrar"}
    </button>
  );
}
