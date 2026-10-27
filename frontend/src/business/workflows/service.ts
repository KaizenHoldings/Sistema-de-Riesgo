/**
 * Servicio del circuito de aprobación.
 *
 * Frontera entre la interfaz y los datos: la capa visual no conoce rutas, ni
 * códigos HTTP, ni el `ApiError`. Todo método devuelve `ServiceResult`, de modo
 * que un fallo de negocio —una guarda del backend que rechaza la transición— se
 * trata igual que cualquier otro resultado y no interrumpe el render.
 *
 * Las validaciones que se hacen aquí son las mismas que exige el backend, no
 * unas propias: adelantan el aviso al usuario sin sustituir la comprobación real,
 * que sigue estando del lado del servidor.
 */

import {
  construirWorkflow,
  type ExpedienteCrudo,
} from "@/business/workflows/approvalWorkflow";
import type {
  ApprovalWorkflow,
  BICommitteeForm,
  ComplianceForm,
  EtapaDevolucion,
  EvaluacionGuardada,
  EvaluacionRiesgo,
  LegalForm,
  ResultadoScoring,
  ResultadoTransicion,
  RiskForm,
  ServiceResult,
  TipoExpediente,
} from "@/business/workflows/types";
import {
  workflowRepository,
  type WorkflowRepository,
} from "@/data/workflowRepository";
import { ApiError } from "@/utils/apiClient";

/** Traduce el fallo de transporte a un código de dominio estable. */
function comoError(fallo: unknown): ServiceResult<never> {
  if (fallo instanceof ApiError) {
    const code = fallo.esNoEncontrado
      ? "NO_ENCONTRADO"
      : fallo.esConflicto
        ? "TRANSICION_INVALIDA"
        : fallo.esValidacion
          ? "DATOS_INSUFICIENTES"
          : fallo.esDeRed
            ? "SIN_CONEXION"
            : fallo.status === 403
              ? "SIN_PERMISO"
              : "ERROR_SERVICIO";
    return { success: false, error: { code, message: fallo.message } };
  }
  return {
    success: false,
    error: {
      code: "ERROR_INESPERADO",
      message: "No se pudo completar la operación.",
    },
  };
}

function ok<T>(data: T): ServiceResult<T> {
  return { success: true, data };
}

function invalido(message: string): ServiceResult<never> {
  return { success: false, error: { code: "DATOS_INSUFICIENTES", message } };
}

export function crearApprovalWorkflowService(
  repositorio: WorkflowRepository = workflowRepository,
) {
  return {
    /** Estado completo del circuito, listo para el visualizador. */
    async obtenerFlujo(
      tipo: TipoExpediente,
      expId: number,
      signal?: AbortSignal,
    ): Promise<ServiceResult<ApprovalWorkflow>> {
      try {
        const expediente: ExpedienteCrudo = await repositorio.obtenerExpediente(
          tipo,
          expId,
          signal,
        );

        // Las tareas son informativas: si su consulta falla, el circuito debe
        // poder seguir operándose igualmente.
        let tareas: ApprovalWorkflow["tareas"] = [];
        try {
          const crudas = await repositorio.obtenerTareas(tipo, expId, signal);
          tareas = crudas.map((t) => ({
            id: t.id,
            etapa: t.etapa,
            estado: t.estado,
            origen: t.origen,
            observaciones: t.observaciones,
            fecha_creacion: t.fecha_creacion,
          }));
        } catch {
          tareas = [];
        }

        return ok(construirWorkflow(expediente, tipo, tareas));
      } catch (fallo) {
        return comoError(fallo);
      }
    },

    /**
     * Certifica Cumplimiento.
     *
     * Los datos AML/CFT viajan en la misma llamada que la firma: el backend los
     * persiste dentro de la transacción que cierra la etapa, de modo que no
     * puede quedar una etapa firmada sin su debida diligencia registrada.
     */
    async certificarCumplimiento(
      tipo: TipoExpediente,
      expId: number,
      usuario: string,
      formulario: ComplianceForm,
    ): Promise<ServiceResult<ResultadoTransicion>> {
      if (!formulario.origen_fondos.trim()) {
        return invalido("Debe declarar el origen de los fondos.");
      }
      if (formulario.check_sanciones) {
        return invalido(
          "El cliente figura en listas de sanciones: el expediente no puede " +
            "certificarse, debe rechazarse en Cumplimiento.",
        );
      }

      const datos: Record<string, unknown> = {
        riesgo_aml: formulario.riesgo_aml,
        origen_fondos: formulario.origen_fondos.trim(),
        check_pep: formulario.check_pep ? 1 : 0,
        check_sanciones: formulario.check_sanciones ? 1 : 0,
        obs: formulario.obs.trim(),
      };

      // La línea automotriz añade los datos laborales del solicitante.
      if (tipo === "auto") {
        datos.ocupacion = formulario.ocupacion ?? "";
        datos.empleador = formulario.empleador ?? "";
        datos.telefono = formulario.telefono ?? "";
      }

      try {
        return ok(
          await repositorio.certificarCumplimiento(tipo, expId, usuario, datos),
        );
      } catch (fallo) {
        return comoError(fallo);
      }
    },

    /** Devuelve el expediente al área comercial para subsanación. */
    async observarCumplimiento(
      tipo: TipoExpediente,
      expId: number,
      usuario: string,
      observaciones: string,
    ): Promise<ServiceResult<ResultadoTransicion>> {
      const texto = observaciones.trim();
      if (!texto) return invalido("Debe indicar las observaciones de la devolución.");
      try {
        return ok(
          await repositorio.observarCumplimiento(tipo, expId, usuario, texto),
        );
      } catch (fallo) {
        return comoError(fallo);
      }
    },

    /** Desestima el expediente en Cumplimiento. */
    async rechazarCumplimiento(
      tipo: TipoExpediente,
      expId: number,
      usuario: string,
      motivo: string,
    ): Promise<ServiceResult<ResultadoTransicion>> {
      const texto = motivo.trim();
      if (!texto) return invalido("Debe indicar el motivo del rechazo.");
      try {
        return ok(
          await repositorio.rechazarCumplimiento(tipo, expId, usuario, texto),
        );
      } catch (fallo) {
        return comoError(fallo);
      }
    },

    /** Firma de Legal. Exige la certificación previa de Cumplimiento. */
    async registrarLegal(
      tipo: TipoExpediente,
      expId: number,
      formulario: LegalForm,
    ): Promise<ServiceResult<ResultadoTransicion>> {
      try {
        return ok(await repositorio.registrarLegal(tipo, expId, formulario));
      } catch (fallo) {
        return comoError(fallo);
      }
    },

    /** Firma de Riesgo. Exige la certificación previa de Cumplimiento. */
    async registrarRiesgo(
      tipo: TipoExpediente,
      expId: number,
      formulario: RiskForm,
    ): Promise<ServiceResult<ResultadoTransicion>> {
      try {
        return ok(await repositorio.registrarRiesgo(tipo, expId, formulario));
      } catch (fallo) {
        return comoError(fallo);
      }
    },

    /**
     * Calcula el scoring sin registrar nada.
     *
     * Es el paso previo de la evaluación de Riesgo, igual que en la versión
     * anterior: primero se calcula y se revisa el resultado, y solo después se
     * firma la etapa con las cifras obtenidas.
     */
    async calcularScoring(
      tipo: TipoExpediente,
      entradas: Record<string, unknown>,
    ): Promise<ServiceResult<ResultadoScoring>> {
      try {
        return ok(await repositorio.calcularScoring(tipo, entradas));
      } catch (fallo) {
        return comoError(fallo);
      }
    },

    /**
     * Hoja de trabajo de Riesgo guardada en la base, o `null` si no hay.
     *
     * No firma ni avanza nada: es lo que el analista dejó escrito, para retomarlo
     * desde cualquier equipo.
     */
    async obtenerEvaluacionRiesgo<T extends EvaluacionRiesgo>(
      tipo: TipoExpediente,
      expId: number,
      signal?: AbortSignal,
    ): Promise<ServiceResult<EvaluacionGuardada<T> | null>> {
      try {
        return ok(await repositorio.obtenerEvaluacionRiesgo<T>(tipo, expId, signal));
      } catch (fallo) {
        return comoError(fallo);
      }
    },

    /** Guarda o reemplaza la hoja de trabajo. Solo el rol Riesgo puede escribirla. */
    async guardarEvaluacionRiesgo<T extends EvaluacionRiesgo>(
      tipo: TipoExpediente,
      expId: number,
      datos: T,
    ): Promise<ServiceResult<EvaluacionGuardada<T>>> {
      try {
        return ok(await repositorio.guardarEvaluacionRiesgo<T>(tipo, expId, datos));
      } catch (fallo) {
        return comoError(fallo);
      }
    },

    /** Dictamen del Comité. Aprobar exige las tres firmas del circuito. */
    async emitirDictamen(
      tipo: TipoExpediente,
      expId: number,
      usuario: string,
      formulario: BICommitteeForm,
    ): Promise<ServiceResult<ResultadoTransicion>> {
      if (formulario.dictamen === "APROBADO") {
        if (formulario.plazo <= 0) {
          return invalido("El plazo aprobado debe ser mayor que cero.");
        }
        if (formulario.tasa < 0) {
          return invalido("La tasa aprobada no puede ser negativa.");
        }
      }
      try {
        return ok(
          await repositorio.emitirDictamen(tipo, expId, usuario, formulario),
        );
      } catch (fallo) {
        return comoError(fallo);
      }
    },

    /** Devuelve el expediente a una etapa previa con justificación obligatoria. */
    async devolver(
      tipo: TipoExpediente,
      expId: number,
      usuario: string,
      etapaDestino: EtapaDevolucion,
      observaciones: string,
    ): Promise<ServiceResult<ResultadoTransicion>> {
      const texto = observaciones.trim();
      if (!texto) return invalido("Debe indicar la justificación de la devolución.");
      try {
        return ok(
          await repositorio.devolver(tipo, expId, usuario, etapaDestino, texto),
        );
      } catch (fallo) {
        return comoError(fallo);
      }
    },

    /** Rechazo administrativo, posterior a Cumplimiento. */
    async rechazar(
      tipo: TipoExpediente,
      expId: number,
      usuario: string,
      motivo: string,
    ): Promise<ServiceResult<ResultadoTransicion>> {
      const texto = motivo.trim();
      if (!texto) return invalido("Debe indicar el motivo del rechazo.");
      try {
        return ok(await repositorio.rechazar(tipo, expId, usuario, texto));
      } catch (fallo) {
        return comoError(fallo);
      }
    },
  };
}

export type ApprovalWorkflowService = ReturnType<
  typeof crearApprovalWorkflowService
>;

/** Instancia por omisión, sobre el repositorio real. */
export const approvalWorkflowService = crearApprovalWorkflowService();
