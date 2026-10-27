"use client";

/**
 * Panel del circuito de aprobación.
 *
 * Frontera cliente de la funcionalidad: administra el estado de las evaluaciones,
 * el envío de transiciones y la visualización de los formularios según el rol.
 *
 * Cada rol ve exclusivamente lo que le compete. Al aprobar una etapa, su formulario
 * se presenta en modo solo lectura para conservar la trazabilidad de lo evaluado.
 */

import { useCallback, useEffect, useMemo, useState } from "react";

import { approvalWorkflowService } from "@/business/workflows/service";
import type {
  ApprovalWorkflow,
  BICommitteeForm,
  ComplianceForm,
  EtapaDevolucion,
  EvaluacionRiesgo,
  LegalForm,
  ResultadoScoring,
  RiskForm,
  ServiceResult,
  TipoExpediente,
} from "@/business/workflows/types";
import { FlujoAprobacion } from "@/components/sections/FlujoAprobacion";
import { FormularioComiteBI } from "@/components/sections/FormularioComiteBI";
import { FormularioCumplimiento } from "@/components/sections/FormularioCumplimiento";
import { FormularioLegal } from "@/components/sections/FormularioLegal";
import {
  FormularioRiesgo,
  type PersistenciaRiesgo,
} from "@/components/sections/FormularioRiesgo";
import { useSesion } from "@/components/providers/ProveedorSesion";
import { SinResultados } from "@/components/ui/Alerta";
import { BOTON, Modal } from "@/components/ui/Modal";
import { SkeletonMetricas, SkeletonTabla } from "@/components/ui/Skeleton";
import { useAvisos } from "@/components/ui/Toast";

type Pestana = "cumplimiento" | "legal" | "riesgo" | "comite";

/**
 * Roles que solo hacen seguimiento y no firman etapas.
 */
const ROLES_SIN_FIRMA = ["Comercial", "Cobranzas"];

const PESTANAS: Array<{ clave: Pestana; etiqueta: string; roles: string[] }> = [
  { clave: "cumplimiento", etiqueta: "Cumplimiento", roles: ["Compliance", "Superadmin"] },
  { clave: "legal", etiqueta: "Legal", roles: ["Legal", "Superadmin"] },
  { clave: "riesgo", etiqueta: "Riesgo", roles: ["Riesgo", "Superadmin"] },
  { clave: "comite", etiqueta: "Comité BI", roles: ["Comité", "Superadmin"] },
];

/** Etapas cuya firma exige confirmación explícita. */
type EtapaFirma = "Cumplimiento" | "Legal" | "Riesgo";

interface FirmaPendiente {
  etapa: EtapaFirma;
  titulo: string;
  operacion: () => Promise<ServiceResult<unknown>>;
  resolver: (resultado: ServiceResult<unknown>) => void;
}

const FIRMA_CANCELADA: ServiceResult<never> = {
  success: false,
  error: { code: "CANCELADO", message: "La firma no se registró." },
};

export function PanelAprobacion({
  tipo,
  expId,
}: {
  tipo: TipoExpediente;
  expId: number;
}) {
  const { sesion } = useSesion();
  const { notificar } = useAvisos();
  const usuario = sesion?.usuario ?? "";

  const [flujo, setFlujo] = useState<ApprovalWorkflow | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  const [enviando, setEnviando] = useState(false);
  const [pestanaElegida, setPestana] = useState<Pestana>("cumplimiento");
  const [firmaPendiente, setFirmaPendiente] = useState<FirmaPendiente | null>(null);

  const soloLectura = Boolean(sesion && ROLES_SIN_FIRMA.includes(sesion.rol));
  const pestanasVisibles = useMemo(
    () =>
      soloLectura
        ? []
        : PESTANAS.filter((item) => sesion && item.roles.includes(sesion.rol)),
    [sesion, soloLectura],
  );

  const pestana: Pestana = pestanasVisibles.some(
    (item) => item.clave === pestanaElegida,
  )
    ? pestanaElegida
    : (pestanasVisibles[0]?.clave ?? "cumplimiento");

  const [recarga, setRecarga] = useState(0);
  const refrescar = useCallback(() => setRecarga((n) => n + 1), []);

  useEffect(() => {
    const controlador = new AbortController();

    approvalWorkflowService
      .obtenerFlujo(tipo, expId, controlador.signal)
      .then((resultado) => {
        if (controlador.signal.aborted) return;
        if (resultado.success) {
          setFlujo(resultado.data);
          setFallo(null);
          // Si el usuario es Superadmin o tiene varias pestañas, acompañar la etapa activa si no ha elegido otra
          if (sesion?.rol === "Superadmin") {
            setPestana((actual) =>
              actual === "cumplimiento" && resultado.data.firmas.cumplimiento
                ? resultado.data.etapaActual === "comite"
                  ? "comite"
                  : "riesgo"
                : actual,
            );
          }
        } else {
          setFallo(resultado.error.message);
        }
        setCargando(false);
      });

    return () => controlador.abort();
  }, [tipo, expId, recarga, sesion?.rol]);

  const ejecutar = async <T,>(
    titulo: string,
    operacion: () => Promise<ServiceResult<T>>,
  ): Promise<ServiceResult<T>> => {
    setEnviando(true);
    const resultado = await operacion();
    setEnviando(false);

    if (resultado.success) {
      notificar("exito", titulo, "El circuito quedó actualizado.");
      refrescar();
    } else {
      notificar("error", titulo, resultado.error.message);
    }
    return resultado;
  };

  const conConfirmacion = (
    etapa: EtapaFirma,
    titulo: string,
    operacion: () => Promise<ServiceResult<unknown>>,
  ): Promise<ServiceResult<unknown>> =>
    new Promise((resolver) => {
      setFirmaPendiente({ etapa, titulo, operacion, resolver });
    });

  const cancelarFirma = () => {
    firmaPendiente?.resolver(FIRMA_CANCELADA);
    setFirmaPendiente(null);
  };

  const confirmarFirma = async () => {
    if (!firmaPendiente) return;
    const { titulo, operacion, resolver } = firmaPendiente;
    setFirmaPendiente(null);
    resolver(await ejecutar(titulo, operacion));
  };

  const dictamen = (flujo?.dictamen ?? "PENDIENTE").toUpperCase();
  const finalizado = dictamen !== "PENDIENTE";

  // Estados de aprobación por etapa:
  // Cuando un rol ya aprobó, su formulario se muestra en modo solo lectura.
  const cumplimientoFirmado = Boolean(flujo?.firmas.cumplimiento);
  const legalFirmado = Boolean(flujo?.firmas.legal);
  const riesgoFirmado = Boolean(flujo?.firmas.riesgo);

  const cumplimientoBloqueado = cumplimientoFirmado || finalizado;
  const legalBloqueado = legalFirmado || finalizado;
  const riesgoBloqueado = riesgoFirmado || finalizado;
  const comiteBloqueado = finalizado;

  const persistenciaRiesgo: PersistenciaRiesgo = {
    puedeGuardar:
      (sesion?.rol === "Riesgo" || sesion?.rol === "Superadmin") &&
      !riesgoBloqueado &&
      cumplimientoFirmado,
    cargar: (signal) =>
      approvalWorkflowService.obtenerEvaluacionRiesgo(tipo, expId, signal),
    guardar: async (datos: EvaluacionRiesgo, opciones) => {
      const resultado = await approvalWorkflowService.guardarEvaluacionRiesgo(
        tipo,
        expId,
        datos,
      );
      if (resultado.success) {
        if (opciones.modo === "automatico") {
          notificar("exito", "Evaluación de Riesgo", "Avances guardados automáticamente");
        } else if (opciones.modo === "manual") {
          notificar("exito", "Evaluación de Riesgo", "Evaluación guardada.");
        }
      } else if (opciones.avisarError) {
        notificar("error", "Evaluación de Riesgo", resultado.error.message);
      }
      return resultado;
    },
  };

  if (cargando) {
    return (
      <div className="space-y-6">
        <SkeletonMetricas tarjetas={2} />
        <SkeletonTabla filas={4} />
      </div>
    );
  }

  if (fallo || !flujo) {
    return <SinResultados mensaje={fallo ?? "No se pudo cargar el circuito."} />;
  }

  if (soloLectura) {
    return (
      <div className="space-y-6">
        <FlujoAprobacion flujo={flujo} />
        <SinResultados mensaje="Su rol sigue el expediente pero no interviene en el circuito: las firmas corresponden a Cumplimiento, Legal, Riesgo y el Comité." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <FlujoAprobacion flujo={flujo} />

      {finalizado && (
        <div className="rounded-xl border border-borde bg-white p-4 shadow-sm text-sm text-tinta">
          <p className="font-semibold text-kaizen-900">
            Expediente {flujo.dictamen.toLowerCase()}
          </p>
          <p className="mt-1 text-xs text-tinta-suave">
            El circuito de aprobación se encuentra finalizado y no admite nuevas transiciones. Las evaluaciones se muestran en modo solo lectura.
          </p>
        </div>
      )}

      {/* Selector de pestañas: solo visible si el usuario tiene acceso a más de una */}
      {pestanasVisibles.length > 1 && (
        <div
          className="inline-flex flex-wrap rounded-lg border border-borde bg-white p-1"
          role="tablist"
          aria-label="Evaluaciones del circuito"
        >
          {pestanasVisibles.map(({ clave, etiqueta }) => {
            const activa = pestana === clave;
            return (
              <button
                key={clave}
                type="button"
                role="tab"
                aria-selected={activa}
                onClick={() => setPestana(clave)}
                className={`rounded-md px-4 py-2 text-sm font-semibold transition ${
                  activa
                    ? "bg-kaizen-800 text-white"
                    : "text-tinta-suave hover:text-kaizen-900"
                }`}
              >
                {etiqueta}
              </button>
            );
          })}
        </div>
      )}

      {pestana === "cumplimiento" && (
        <FormularioCumplimiento
          tipo={tipo}
          clienteId={flujo.clienteId}
          enviando={enviando}
          bloqueado={cumplimientoBloqueado}
          datosExistentes={flujo.expediente}
          onCertificar={(form: ComplianceForm) =>
            conConfirmacion("Cumplimiento", "Cumplimiento", () =>
              approvalWorkflowService.certificarCumplimiento(
                tipo,
                expId,
                usuario,
                form,
              ),
            )
          }
          onObservar={(obs) =>
            ejecutar("Subsanación comercial", () =>
              approvalWorkflowService.observarCumplimiento(
                tipo,
                expId,
                usuario,
                obs,
              ),
            )
          }
          onRechazar={(motivo) =>
            ejecutar("Rechazo en Cumplimiento", () =>
              approvalWorkflowService.rechazarCumplimiento(
                tipo,
                expId,
                usuario,
                motivo,
              ),
            )
          }
        />
      )}

      {pestana === "legal" && (
        <>
          {!cumplimientoFirmado && !legalFirmado && !finalizado && (
            <div className="rounded-xl border border-ambar-trazo/30 bg-ambar-fondo p-4 text-xs text-ambar-trazo">
              El expediente se encuentra en la etapa inicial de Cumplimiento. La evaluación Legal se habilitará para firma una vez que dicha etapa sea certificada. Mientras tanto, puede inspeccionar documentos y descargar el contrato.
            </div>
          )}
          <FormularioLegal
            tipo={tipo}
            expId={expId}
            montoCredito={Number(flujo.monto ?? 0)}
            enviando={enviando}
            bloqueado={legalBloqueado || !cumplimientoFirmado}
            datosExistentes={flujo.expediente}
            onRegistrar={(form: LegalForm) =>
              conConfirmacion("Legal", "Firma de Legal", () =>
                approvalWorkflowService.registrarLegal(tipo, expId, form),
              )
            }
            onDevolver={(etapa: EtapaDevolucion, obs) =>
              ejecutar("Devolución desde Legal", () =>
                approvalWorkflowService.devolver(
                  tipo,
                  expId,
                  usuario,
                  etapa,
                  obs,
                ),
              )
            }
            onRechazar={(motivo) =>
              ejecutar("Denegación desde Legal", () =>
                approvalWorkflowService.rechazar(tipo, expId, usuario, motivo),
              )
            }
          />
        </>
      )}

      {pestana === "riesgo" && (
        <>
          {!cumplimientoFirmado && !riesgoFirmado && !finalizado && (
            <div className="rounded-xl border border-ambar-trazo/30 bg-ambar-fondo p-4 text-xs text-ambar-trazo">
              El expediente se encuentra en la etapa inicial de Cumplimiento. La evaluación de Riesgo se habilitará una vez que dicha etapa sea certificada.
            </div>
          )}
          <FormularioRiesgo
            tipo={tipo}
            expId={expId}
            enviando={enviando}
            bloqueado={riesgoBloqueado || !cumplimientoFirmado}
            persistencia={persistenciaRiesgo}
            onCalcular={(
              entradas,
            ): Promise<ServiceResult<ResultadoScoring>> =>
              approvalWorkflowService.calcularScoring(tipo, entradas)
            }
            onRegistrar={(form: RiskForm) =>
              conConfirmacion("Riesgo", "Firma de Riesgo", () =>
                approvalWorkflowService.registrarRiesgo(tipo, expId, form),
              )
            }
          />
        </>
      )}

      {pestana === "comite" && (
        <FormularioComiteBI
          tipo={tipo}
          expId={expId}
          clienteId={flujo.clienteId}
          nombreCliente={flujo.cliente}
          firmas={flujo.firmas}
          tasaSugerida={flujo.tasaSugerida}
          plazoSugerido={flujo.plazoMeses ?? 36}
          enviando={enviando}
          bloqueado={comiteBloqueado}
          dictamen={flujo.dictamen}
          tasaAprobada={
            flujo.expediente?.tasa_aprobada !== undefined
              ? Number(flujo.expediente.tasa_aprobada)
              : undefined
          }
          plazoAprobado={
            flujo.expediente?.plazo_meses !== undefined
              ? Number(flujo.expediente.plazo_meses)
              : undefined
          }
          onDictamen={(form: BICommitteeForm) =>
            ejecutar("Dictamen del Comité", () =>
              approvalWorkflowService.emitirDictamen(
                tipo,
                expId,
                usuario,
                form,
              ),
            )
          }
          onDevolver={(etapa: EtapaDevolucion, obs) =>
            ejecutar("Devolución", () =>
              approvalWorkflowService.devolver(
                tipo,
                expId,
                usuario,
                etapa,
                obs,
              ),
            )
          }
          onRechazar={(motivo) =>
            ejecutar("Rechazo", () =>
              approvalWorkflowService.rechazar(tipo, expId, usuario, motivo),
            )
          }
        />
      )}

      <Modal
        abierto={firmaPendiente !== null}
        titulo="Confirmar firma"
        alCerrar={cancelarFirma}
        pie={
          <>
            <button type="button" className={BOTON.neutro} onClick={cancelarFirma}>
              Cancelar
            </button>
            <button
              type="button"
              className={BOTON.primario}
              disabled={enviando}
              onClick={() => void confirmarFirma()}
            >
              Confirmar
            </button>
          </>
        }
      >
        <p className="text-sm text-tinta">
          ¿Está seguro de dar aprobación de {firmaPendiente?.etapa} a esta
          solicitud?
        </p>
      </Modal>
    </div>
  );
}
