"use client";

/**
 * Resumen del expediente.
 *
 * Se ocupa solo de presentar: identidad, importe y calificación, más la
 * descarga del acta. Las firmas, las transiciones del circuito y los cuatro
 * formularios de evaluación viven en `PanelAprobacion`, de modo que el flujo se
 * opere desde un único sitio y no desde dos que puedan discrepar.
 *
 * El área comercial no firma, así que lo que necesita de esta pantalla es el
 * estado en una frase y, si la solicitud se cerró en falso, la vía para volver
 * a presentarla: la reevaluación, que abre un expediente nuevo con los mismos
 * datos del cliente.
 */

import Link from "next/link";
import { useRouter } from "next/navigation";

import {
  CajaDocumentos,
  puedeCargarDocumentos,
  puedeVerDocumentos,
} from "@/components/evaluaciones/CajaDocumentos";
import { EncabezadoPagina } from "@/components/layout/MarcoApp";
import { Alerta } from "@/components/ui/Alerta";
import { BOTON } from "@/components/ui/Modal";
import { Insignia } from "@/components/ui/Semaforo";
import { SkeletonMetricas, SkeletonTabla } from "@/components/ui/Skeleton";
import { TarjetaMetrica } from "@/components/ui/TarjetaMetrica";
import { useAvisos } from "@/components/ui/Toast";
import { useAccion } from "@/hooks/useAccion";
import { descargarActa } from "@/hooks/useDocumentos";
import {
  solicitarReevaluacion,
  useExpedienteAutomotriz,
  useExpedienteCorporativo,
} from "@/hooks/useExpedientes";
import { useSesion } from "@/components/providers/ProveedorSesion";
import type {
  ExpedienteAutomotriz,
  ExpedienteCorporativo,
  TipoExpediente,
} from "@/types/api";
import { guardarComo } from "@/utils/descargas";
import {
  etapaActual,
  semaforoDictamen,
  semaforoRiesgoAml,
  semaforoScore,
} from "@/utils/estados";
import {
  formatearDinero,
  formatearFecha,
  formatearNumero,
  textoOGuion,
} from "@/utils/format";

export function FichaExpediente({
  tipo,
  expId,
}: {
  tipo: TipoExpediente;
  expId: number;
}) {
  const corporativo = useExpedienteCorporativo(expId, tipo === "corp");
  const automotriz = useExpedienteAutomotriz(expId, tipo === "auto");
  const consulta = tipo === "corp" ? corporativo : automotriz;

  const { sesion } = useSesion();
  const { notificarError } = useAvisos();
  const acta = useAccion(async () => {
    guardarComo(await descargarActa(tipo, expId));
    return true;
  });

  if (consulta.cargando) {
    return (
      <div className="space-y-6">
        <SkeletonMetricas />
        <SkeletonTabla />
      </div>
    );
  }

  if (consulta.error) {
    return (
      <>
        <Volver />
        <Alerta error={consulta.error} alReintentar={consulta.recargar} />
      </>
    );
  }

  const exp = consulta.datos as ExpedienteCorporativo | ExpedienteAutomotriz | null;
  if (!exp) return <Volver />;

  const cerrado = exp.dictamen === "APROBADO" || exp.dictamen === "RECHAZADO";

  const esLegal = sesion?.rol === "Legal";

  return (
    <>
      <Volver />

      <EncabezadoPagina
        icono="◈"
        miga={`Evaluaciones / ${tipo === "corp" ? "Corporativo" : "Automotriz"} / ${exp.id}`}
        titulo={textoOGuion(exp.cliente)}
        bajada={`${formatearDinero(exp.monto)} · ${textoOGuion(exp.descripcion)}`}
        acciones={
          <>
            {!esLegal && (
              <button
                type="button"
                className={BOTON.neutro}
                disabled={acta.enviando}
                onClick={async () => {
                  if ((await acta.ejecutar()) === null && acta.error) {
                    notificarError(acta.error);
                  }
                }}
              >
                {acta.enviando ? "Generando…" : "Descargar acta"}
              </button>
            )}
            <Insignia
              tono={semaforoDictamen(exp.dictamen)}
              texto={textoOGuion(exp.dictamen)}
            />
          </>
        }
      />

      <ResumenCliente tipo={tipo} exp={exp} />

      <EstadoYReevaluacion tipo={tipo} exp={exp} />

      <section className={`mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 ${esLegal ? "xl:grid-cols-2" : "xl:grid-cols-4"}`}>
        <TarjetaMetrica
          rotulo="Monto solicitado"
          valor={formatearDinero(exp.monto)}
          nota={`Solicitado el ${formatearFecha(exp.fecha)}`}
        />
        <TarjetaMetrica
          rotulo="Etapa del circuito"
          valor={etapaActual(exp)}
          nota={textoOGuion(exp.estado_workflow)}
          acento={cerrado ? "neutro" : "ambar"}
        />
        {!esLegal && (
          <>
            <TarjetaMetrica
              rotulo="Score de riesgo"
              valor={exp.score_f ? formatearNumero(exp.score_f, 2) : "Sin calificar"}
              nota={`Tasa sugerida ${formatearNumero(exp.tasa_sugerida, 2)}%`}
              acento={semaforoScore(exp.score_f)}
            />
            <TarjetaMetrica
              rotulo="Riesgo AML"
              valor={textoOGuion(exp.riesgo_aml)}
              nota="Declarado por Cumplimiento"
              acento={semaforoRiesgoAml(exp.riesgo_aml)}
            />
          </>
        )}
      </section>

      {/* Comercial reúne los documentos; Legal y Comité los inspeccionan en modo lectura */}
      {puedeVerDocumentos(sesion?.rol) && (
        <CajaDocumentos
          tipo={tipo}
          expId={expId}
          puedeCargar={puedeCargarDocumentos(sesion?.rol)}
        />
      )}
    </>
  );
}

/** Roles que trabajan con el cliente, no con el circuito. */
const ROLES_COMERCIALES = ["Comercial", "Superadmin"];

/**
 * Identidad del solicitante, con salida a su ficha.
 *
 * Solo para quien origina: el area comercial llega al expediente desde el
 * seguimiento y lo que suele necesitar es volver al cliente —su KYC, sus
 * recaudos—. Los firmantes evaluan la operacion, no el padron, y para ellos la
 * tarjeta seria un desvio: por eso no se pinta.
 */
function ResumenCliente({
  tipo,
  exp,
}: {
  tipo: TipoExpediente;
  exp: ExpedienteCorporativo | ExpedienteAutomotriz;
}) {
  const { sesion } = useSesion();
  if (!sesion || !ROLES_COMERCIALES.includes(sesion.rol)) return null;

  const documento =
    tipo === "corp"
      ? (exp as ExpedienteCorporativo).rif
      : (exp as ExpedienteAutomotriz).cedula;

  return (
    <section
      className="mb-6 rounded-xl border border-borde bg-white p-4 shadow-sm"
      aria-label="Cliente del expediente"
    >
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs font-semibold tracking-wide text-tinta-suave uppercase">
            Cliente
          </p>
          <p className="mt-1 truncate text-sm font-semibold text-tinta">
            {textoOGuion(exp.cliente)}
          </p>
          <p className="mt-1 text-xs text-tinta-suave">
            {tipo === "corp" ? "RIF" : "Cédula"} {textoOGuion(documento)} ·{" "}
            {tipo === "corp" ? "Crédito corporativo" : "Crédito automotriz"} ·
            Solicitud {exp.id ?? "—"} del {formatearFecha(exp.fecha)}
          </p>
        </div>

        {exp.cliente_id ? (
          <Link
            href={`/clients/${exp.cliente_id}`}
            className="text-sm font-semibold text-kaizen-900 hover:underline"
          >
            Ver ficha del cliente
          </Link>
        ) : (
          <p className="text-xs text-tinta-suave">
            La solicitud no está enlazada a una ficha del padrón.
          </p>
        )}
      </div>
    </section>
  );
}

/** Roles que pueden volver a presentar una solicitud cerrada en falso. */
const ROLES_REEVALUACION = ["Comercial", "Superadmin"];

interface EstadoSolicitud {
  etiqueta: string;
  detalle: string;
  tono: "verde" | "rojo" | "ambar" | "neutro";
  reevaluable: boolean;
}

/**
 * Traduce el dictamen al lenguaje del área comercial.
 *
 * Las devoluciones viajan como «REVISIÓN-<etapa>», que dice a qué etapa volvió
 * el expediente; para quien lo presentó, lo relevante es que está frenado y en
 * qué punto.
 */
function estadoSolicitud(dictamen: string | null): EstadoSolicitud {
  const valor = (dictamen ?? "").toUpperCase();

  if (valor === "APROBADO") {
    return {
      etiqueta: "Aprobado",
      detalle: "El Comité aprobó la solicitud y se generó el plan de pagos.",
      tono: "verde",
      reevaluable: false,
    };
  }
  if (valor === "RECHAZADO") {
    return {
      etiqueta: "Denegado",
      detalle: "La solicitud fue rechazada y el expediente está cerrado.",
      tono: "rojo",
      reevaluable: true,
    };
  }
  if (valor.startsWith("REVISIÓN") || valor.startsWith("REVISION")) {
    const etapa = (dictamen ?? "").split("-").slice(1).join("-").trim();
    return {
      etiqueta: "Frenado",
      detalle: etapa
        ? `Devuelto a ${etapa} para subsanación.`
        : "Devuelto para subsanación.",
      tono: "ambar",
      reevaluable: true,
    };
  }
  return {
    etiqueta: "En evaluación",
    detalle: "La solicitud sigue su curso por el circuito.",
    tono: "neutro",
    reevaluable: false,
  };
}

const TONO_ESTADO: Record<EstadoSolicitud["tono"], string> = {
  verde: "border-verde-trazo/30 bg-verde-fondo text-verde-trazo",
  rojo: "border-rojo-trazo/30 bg-rojo-fondo text-rojo-trazo",
  ambar: "border-ambar-trazo/30 bg-ambar-fondo text-ambar-trazo",
  neutro: "border-borde bg-lienzo text-tinta-suave",
};

/**
 * Estado de la solicitud y salida para volver a presentarla.
 *
 * El botón solo aparece cuando hay algo que reabrir y quien mira puede hacerlo;
 * el backend vuelve a comprobar ambas cosas y responde 409 o 403 si no.
 */
function EstadoYReevaluacion({
  tipo,
  exp,
}: {
  tipo: TipoExpediente;
  exp: ExpedienteCorporativo | ExpedienteAutomotriz;
}) {
  const router = useRouter();
  const { sesion } = useSesion();
  const { notificarError } = useAvisos();

  const estado = estadoSolicitud(exp.dictamen);
  const puedeReevaluar =
    Boolean(sesion && ROLES_REEVALUACION.includes(sesion.rol)) &&
    estado.reevaluable;

  const reevaluacion = useAccion(() => solicitarReevaluacion(tipo, exp.id ?? 0));
  console.log("exp", exp);
  return (
    <section
      className={`mb-6 flex flex-wrap items-center justify-between gap-4 rounded-xl border px-5 py-4 ${TONO_ESTADO[estado.tono]}`}
      aria-label="Estado de la solicitud"
    >
      <div className="min-w-0">
        <p className="text-sm font-bold">{estado.etiqueta}</p>
        <p className="mt-1 text-sm">{estado.detalle}</p>
        {/* El motivo es lo que explica la parada: sin él, el área comercial no
            sabe qué subsanar antes de volver a presentar la solicitud. */}
        {estado.reevaluable && exp.obs_decision && (
          <p className="mt-2 rounded-lg bg-white/70 px-3 py-2 text-sm text-tinta">
            <span className="font-semibold">Motivo: </span>
            {exp.obs_decision}
          </p>
        )}
        {estado.reevaluable && exp.aprobado_por && (
          <p className="mt-1 text-xs">
            Registrado por {exp.aprobado_por}
            {exp.fecha_decision ? ` · ${exp.fecha_decision}` : ""}
          </p>
        )}
        {exp.parent_expediente_id && (
          <p className="mt-1 text-xs">
            Reevaluación del expediente {exp.parent_expediente_id}.
          </p>  
        )}
      </div>

      {puedeReevaluar && (
        <button
          type="button"
          className={BOTON.primario}
          disabled={reevaluacion.enviando}
          onClick={async () => {
            const nuevo = await reevaluacion.ejecutar();
            if (nuevo) {
              // El expediente viejo deja de estar en la bandeja en cuanto nace
              // el hijo, asi que las listas ya cacheadas por el enrutador
              // quedarian mostrandolo. `refresh` las descarta antes de navegar;
              // las consultas a la API se relanzan solas al montar la vista.
              //router.refresh();
              router.push(`/evaluations`);
            
            } else if (reevaluacion.error) {
              notificarError(reevaluacion.error);
            }
          }}
        >
          {reevaluacion.enviando ? "Abriendo…" : "Solicitar reevaluación"}
        </button>
      )}
    </section>
  );
}

function Volver() {
  return (
    <Link
      href="/evaluations"
      className="mb-4 inline-flex items-center gap-2 text-sm font-semibold text-kaizen-600 transition hover:text-kaizen-900"
    >
      <span aria-hidden>←</span> Volver a la bandeja
    </Link>
  );
}

