"use client";

/**
 * Formulario de Cumplimiento.
 *
 * Primera revisión formal del circuito. Reproduce las tres salidas de la versión
 * anterior: certificar —que firma la etapa y abre de golpe Crédito y Legal—,
 * observar —que devuelve el expediente a subsanación comercial— y rechazar.
 *
 * Cuando la etapa está certificada, se muestra en modo solo lectura.
 */

import { useState } from "react";

import {
  Bloque,
  CampoCasilla,
  CampoSeleccion,
  CampoTexto,
  CampoTextoLargo,
} from "@/components/sections/campos";
import { RevisionDocumental } from "@/components/sections/RevisionDocumental";
import { BOTON } from "@/components/ui/Modal";
import { Girador } from "@/components/ui/Skeleton";
import type {
  ComplianceForm,
  ServiceResult,
  TipoExpediente,
} from "@/business/workflows/types";

const NIVELES_AML = ["Bajo", "Medio", "Alto"] as const;

type Pestana = "formulario" | "documentos";

export function FormularioCumplimiento({
  tipo,
  clienteId,
  enviando,
  bloqueado = false,
  datosExistentes,
  onCertificar,
  onObservar,
  onRechazar,
}: {
  tipo: TipoExpediente;
  /** Cliente del padrón cuyo checklist se revisa. Nulo si no está ligado. */
  clienteId: number | null;
  enviando: boolean;
  bloqueado?: boolean;
  datosExistentes?: Record<string, unknown>;
  onCertificar: (form: ComplianceForm) => Promise<ServiceResult<unknown>>;
  onObservar: (observaciones: string) => Promise<ServiceResult<unknown>>;
  onRechazar: (motivo: string) => Promise<ServiceResult<unknown>>;
}) {
  const [form, setForm] = useState<ComplianceForm>(() => ({
    riesgo_aml: (datosExistentes?.riesgo_aml as ComplianceForm["riesgo_aml"]) || "Bajo",
    origen_fondos: String(datosExistentes?.origen_fondos ?? ""),
    check_pep: Boolean(datosExistentes?.check_pep),
    check_sanciones: Boolean(datosExistentes?.check_sanciones),
    obs: String(datosExistentes?.obs_comp ?? ""),
    ocupacion: String(datosExistentes?.ocupacion ?? ""),
    empleador: String(datosExistentes?.empleador ?? ""),
    telefono: String(datosExistentes?.telefono ?? ""),
  }));
  const [justificacion, setJustificacion] = useState("");
  const [pestana, setPestana] = useState<Pestana>("formulario");

  const set = <K extends keyof ComplianceForm>(
    clave: K,
    valor: ComplianceForm[K],
  ) => setForm((actual) => ({ ...actual, [clave]: valor }));

  const sinJustificacion = justificacion.trim().length === 0;

  return (
    <div className="rounded-xl border border-borde bg-white shadow-sm">
      <div className="border-b border-borde px-5 pt-5">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-kaizen-900">
              Evaluación de Cumplimiento
            </h3>
            <p className="mt-1 text-xs text-tinta-suave">
              Debida diligencia AML/CFT y origen de fondos.
            </p>
          </div>
          {bloqueado && (
            <span className="rounded-full bg-verde-fondo px-3 py-1 text-xs font-semibold text-verde-trazo">
              Solo lectura
            </span>
          )}
        </div>

        {bloqueado && (
          <div className="mt-3 rounded-lg border border-verde-trazo/30 bg-verde-fondo p-3 text-xs text-verde-trazo">
            ✓ Esta solicitud ya fue certificada por Cumplimiento. Formulario en modo solo lectura.
          </div>
        )}

        <div
          className="mt-4 flex gap-1"
          role="tablist"
          aria-label="Cumplimiento"
        >
          {(
            [
              ["formulario", "Formulario"],
              ["documentos", "Documentos KYC"],
            ] as Array<[Pestana, string]>
          ).map(([clave, etiqueta]) => {
            const activa = pestana === clave;
            return (
              <button
                key={clave}
                type="button"
                role="tab"
                aria-selected={activa}
                aria-controls={`panel-${clave}`}
                onClick={() => setPestana(clave)}
                className={`-mb-px rounded-t-lg border-b-2 px-4 py-2 text-sm font-semibold transition ${
                  activa
                    ? "border-kaizen-800 text-kaizen-900"
                    : "border-transparent text-tinta-suave hover:text-kaizen-600"
                }`}
              >
                {etiqueta}
              </button>
            );
          })}
        </div>
      </div>

      <form
        id="panel-formulario"
        role="tabpanel"
        hidden={pestana !== "formulario"}
        className="p-5"
        onSubmit={(evento) => {
          evento.preventDefault();
          if (!bloqueado) void onCertificar(form);
        }}
      >
        <Bloque titulo="Perfil de riesgo">
          <CampoSeleccion
            rotulo="Riesgo AML"
            valor={form.riesgo_aml}
            opciones={NIVELES_AML}
            alCambiar={(v) =>
              set("riesgo_aml", v as ComplianceForm["riesgo_aml"])
            }
            deshabilitado={bloqueado}
            ayuda="Clasificación resultante de la debida diligencia."
          />
          <CampoTexto
            rotulo="Origen de los fondos"
            valor={form.origen_fondos}
            alCambiar={(v) => set("origen_fondos", v)}
            requerido={!bloqueado}
            deshabilitado={bloqueado}
            ayuda="Actividad de la que provienen los recursos declarados."
          />
        </Bloque>

        {tipo === "auto" && (
          <Bloque
            titulo="Datos del solicitante"
            descripcion="Solo aplica a la línea automotriz, donde el sujeto de crédito es una persona natural."
            columnas={3}
          >
            <CampoTexto
              rotulo="Ocupación"
              valor={form.ocupacion ?? ""}
              alCambiar={(v) => set("ocupacion", v)}
              deshabilitado={bloqueado}
            />
            <CampoTexto
              rotulo="Empleador"
              valor={form.empleador ?? ""}
              alCambiar={(v) => set("empleador", v)}
              deshabilitado={bloqueado}
            />
            <CampoTexto
              rotulo="Teléfono"
              valor={form.telefono ?? ""}
              alCambiar={(v) => set("telefono", v)}
              deshabilitado={bloqueado}
            />
          </Bloque>
        )}

        <Bloque titulo="Verificaciones obligatorias">
          <CampoCasilla
            rotulo="Persona expuesta políticamente (PEP)"
            valor={form.check_pep}
            alCambiar={(v) => set("check_pep", v)}
            deshabilitado={bloqueado}
            ayuda="No impide certificar, pero eleva el perfil de riesgo."
          />
          <CampoCasilla
            rotulo="Figura en listas de sanciones"
            valor={form.check_sanciones}
            alCambiar={(v) => set("check_sanciones", v)}
            deshabilitado={bloqueado}
            ayuda="Impide la certificación: el expediente debe desestimarse."
          />
        </Bloque>

        <Bloque titulo="Conclusiones" columnas={1}>
          <CampoTextoLargo
            rotulo="Observaciones de Cumplimiento"
            valor={form.obs}
            alCambiar={(v) => set("obs", v)}
            deshabilitado={bloqueado}
            marcador="Resultado de la debida diligencia."
            filas={3}
          />
        </Bloque>

        {!bloqueado && (
          <>
            {form.check_sanciones && (
              <p className="mt-5 rounded-lg bg-rojo-fondo px-4 py-3 text-sm text-rojo-trazo">
                El cliente figura en listas de sanciones. La certificación queda
                bloqueada: use el rechazo indicando el motivo.
              </p>
            )}

            <div className="mt-6 flex flex-wrap gap-3 border-t border-borde pt-5">
              <button
                type="submit"
                className={BOTON.primario}
                disabled={enviando || form.check_sanciones}
              >
                {enviando && <Girador />}
                Certificar Cumplimiento
              </button>
            </div>

            <div className="mt-6 border-t border-borde pt-5">
              <h4 className="text-sm font-semibold text-kaizen-900">
                Devolver o desestimar
              </h4>
              <p className="mt-1 text-xs text-tinta-suave">
                Ambas salidas exigen justificación escrita; queda en la traza del
                expediente.
              </p>

              <div className="mt-3">
                <CampoTextoLargo
                  rotulo="Justificación"
                  valor={justificacion}
                  alCambiar={setJustificacion}
                  marcador="Qué debe subsanar el área comercial, o motivo del rechazo."
                  filas={3}
                />
              </div>

              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  className={BOTON.aviso}
                  disabled={enviando || sinJustificacion}
                  onClick={() => void onObservar(justificacion)}
                >
                  Observar y devolver a comercial
                </button>
                <button
                  type="button"
                  className={BOTON.peligro}
                  disabled={enviando || sinJustificacion}
                  onClick={() => void onRechazar(justificacion)}
                >
                  Desestimar en Cumplimiento
                </button>
              </div>
            </div>
          </>
        )}
      </form>

      <div
        id="panel-documentos"
        role="tabpanel"
        hidden={pestana !== "documentos"}
        className="p-5"
      >
        <RevisionDocumental clienteId={clienteId} />
      </div>
    </div>
  );
}
