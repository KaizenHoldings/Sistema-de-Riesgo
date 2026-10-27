/**
 * Reglas del circuito de aprobación, en la capa de negocio.
 *
 * Aquí se decide en qué etapa está un expediente y qué acciones tiene sentido
 * ofrecer. Es una réplica de la máquina de estados de la versión anterior, y su
 * única fuente son las tres firmas y el dictamen; no consulta nada.
 *
 * Estas reglas **no autorizan** nada: el servicio de flujo del backend vuelve a
 * comprobarlas y puede rechazar cualquier transición con un 409. Lo que evitan es
 * ofrecer al usuario botones que se sabe de antemano que van a ser rechazados.
 */

import type {
  AccionFlujo,
  ApprovalWorkflow,
  EstadoPaso,
  EtapaFlujo,
  FirmasFlujo,
  PasoFlujo,
  TipoExpediente,
} from "@/business/workflows/types";

/** Expediente en crudo, tal y como llega de la capa de datos. */
export interface ExpedienteCrudo {
  id: number | null;
  cliente: string | null;
  /** Cliente del padrón al que pertenece el expediente. Puede no estar ligado. */
  cliente_id: number | null;
  monto: string | null;
  status_comp: number | null;
  status_leg: number | null;
  status_riesgo: number | null;
  dictamen: string | null;
  estado_workflow: string | null;
  aprobado_por: string | null;
  fecha_decision: string | null;
  tasa_sugerida: number | null;
  plazo_meses: number | null;
  [campo: string]: unknown;
}

const DICTAMENES_CERRADOS = ["APROBADO", "RECHAZADO"];

export function firmasDe(exp: ExpedienteCrudo): FirmasFlujo {
  return {
    cumplimiento: exp.status_comp === 1,
    legal: exp.status_leg === 1,
    riesgo: exp.status_riesgo === 1,
  };
}

export function estaCerrado(exp: ExpedienteCrudo): boolean {
  return DICTAMENES_CERRADOS.includes((exp.dictamen ?? "").toUpperCase());
}

/**
 * Etapa en la que se encuentra el expediente.
 *
 * El orden es el de la versión anterior: sin la firma de Cumplimiento no se
 * llega a ninguna otra parte, y el Comité solo entra cuando Legal y Riesgo han
 * cerrado sus evaluaciones simultáneas.
 */
export function etapaDe(exp: ExpedienteCrudo): EtapaFlujo {
  if (estaCerrado(exp)) return "cerrado";

  const firmas = firmasDe(exp);
  if (!firmas.cumplimiento) return "cumplimiento";
  if (!firmas.legal || !firmas.riesgo) return "credito_legal";
  return "comite";
}

function estadoPaso(
  paso: EtapaFlujo,
  etapa: EtapaFlujo,
  exp: ExpedienteCrudo,
): EstadoPaso {
  const rechazado = (exp.dictamen ?? "").toUpperCase() === "RECHAZADO";
  const orden: EtapaFlujo[] = ["cumplimiento", "credito_legal", "comite", "cerrado"];
  const indicePaso = orden.indexOf(paso);
  const indiceActual = orden.indexOf(etapa);

  if (paso === "cerrado") {
    if (etapa !== "cerrado") return "pendiente";
    return rechazado ? "rechazado" : "completado";
  }

  if (etapa === "cerrado") return rechazado ? "rechazado" : "completado";
  if (indicePaso < indiceActual) return "completado";
  if (indicePaso === indiceActual) return "en_curso";
  return "pendiente";
}

/** Los cuatro pasos del circuito, resueltos para el visualizador. */
export function pasosDe(exp: ExpedienteCrudo): PasoFlujo[] {
  const etapa = etapaDe(exp);
  const firmas = firmasDe(exp);

  const definicion: Array<{
    clave: EtapaFlujo;
    titulo: string;
    descripcion: string;
  }> = [
    {
      clave: "cumplimiento",
      titulo: "Cumplimiento",
      descripcion:
        "Primera revisión formal: debida diligencia AML/CFT y origen de fondos.",
    },
    {
      clave: "credito_legal",
      titulo: "Crédito y Legal",
      descripcion: firmas.cumplimiento
        ? `Evaluaciones simultáneas · Legal ${firmas.legal ? "firmada" : "pendiente"} · Riesgo ${firmas.riesgo ? "firmada" : "pendiente"}`
        : "Se abren de golpe cuando Cumplimiento certifica.",
    },
    {
      clave: "comite",
      titulo: "Comité BI",
      descripcion: "Dictamen final. Exige las tres firmas del circuito.",
    },
    {
      clave: "cerrado",
      titulo: "Cerrado",
      descripcion: "El expediente ya no admite transiciones.",
    },
  ];

  return definicion.map((paso) => ({
    ...paso,
    estado: estadoPaso(paso.clave, etapa, exp),
    firmadoPor: paso.clave === "cerrado" ? exp.aprobado_por : null,
    fecha: paso.clave === "cerrado" ? exp.fecha_decision : null,
  }));
}

/** Acciones que tiene sentido ofrecer en la etapa actual. */
export function accionesDe(exp: ExpedienteCrudo): AccionFlujo[] {
  const etapa = etapaDe(exp);

  if (etapa === "cerrado") return [];

  if (etapa === "cumplimiento") {
    return [
      "certificar_cumplimiento",
      "observar_cumplimiento",
      "rechazar_cumplimiento",
    ];
  }

  const acciones: AccionFlujo[] = ["devolver", "rechazar"];
  const firmas = firmasDe(exp);
  if (!firmas.legal) acciones.unshift("registrar_legal");
  if (!firmas.riesgo) acciones.unshift("registrar_riesgo");
  if (etapa === "comite") acciones.unshift("emitir_dictamen");

  return acciones;
}

/** Compone el estado del circuito a partir del expediente y sus tareas. */
export function construirWorkflow(
  exp: ExpedienteCrudo,
  tipo: TipoExpediente,
  tareas: ApprovalWorkflow["tareas"],
): ApprovalWorkflow {
  return {
    expedienteId: exp.id ?? 0,
    tipo,
    cliente: exp.cliente ?? "",
    clienteId: exp.cliente_id,
    monto: exp.monto,
    etapaActual: etapaDe(exp),
    estadoWorkflow: exp.estado_workflow ?? "",
    dictamen: exp.dictamen ?? "PENDIENTE",
    firmas: firmasDe(exp),
    pasos: pasosDe(exp),
    accionesPermitidas: accionesDe(exp),
    tareas,
    aprobadoPor: exp.aprobado_por,
    fechaDecision: exp.fecha_decision,
    tasaSugerida: exp.tasa_sugerida ?? 0,
    plazoMeses: exp.plazo_meses,
    expediente: exp,
  };
}
