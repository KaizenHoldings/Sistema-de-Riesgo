"use client";

/**
 * Ficha del cliente.
 *
 * Recupera la vista `client_profile` de Streamlit: los datos de identificación,
 * el estado de la debida diligencia con su aprobación, y el checklist documental
 * en su propia pestaña.
 */

import Link from "next/link";
import { useState, type ReactNode } from "react";

import { ChecklistDocumental } from "@/components/clientes/ChecklistDocumental";
import { HistorialExpedientes } from "@/components/clientes/HistorialExpedientes";
import { EncabezadoPagina } from "@/components/layout/MarcoApp";
import { Alerta } from "@/components/ui/Alerta";
import { BOTON, CAMPO, Modal } from "@/components/ui/Modal";
import { Insignia } from "@/components/ui/Semaforo";
import { Girador, SkeletonMetricas, SkeletonTabla } from "@/components/ui/Skeleton";
import { TarjetaMetrica } from "@/components/ui/TarjetaMetrica";
import { useAvisos } from "@/components/ui/Toast";
import { useAccion } from "@/hooks/useAccion";
import { useChecklist, aprobarKyc } from "@/hooks/useDocumentos";
import { useCliente } from "@/hooks/useClientes";
import { semaforoKyc } from "@/utils/estados";
import { formatearFecha, textoOGuion } from "@/utils/format";

type Pestana = "datos" | "documentos" | "expedientes";

export function FichaCliente({ cliId }: { cliId: number }) {
  const cliente = useCliente(cliId);
  const checklist = useChecklist(cliId);
  const [pestana, setPestana] = useState<Pestana>("datos");
  const [aprobando, setAprobando] = useState(false);

  if (cliente.cargando) {
    return (
      <div className="space-y-6">
        <SkeletonMetricas />
        <SkeletonTabla />
      </div>
    );
  }

  if (cliente.error) {
    return (
      <>
        <Volver />
        <Alerta error={cliente.error} alReintentar={cliente.recargar} />
      </>
    );
  }

  const c = cliente.datos;
  if (!c) return <Volver />;

  const estado = c.kyc_status ?? "";
  const puedeAprobar = estado === "Prospecto" || estado === "KYC Pendiente";

  return (
    <>
      <Volver />

      <EncabezadoPagina
        icono="▣"
        miga={`Clientes / ${c.id}`}
        titulo={textoOGuion(c.nombre)}
        bajada={`${textoOGuion(c.tipo)} · ${textoOGuion(c.cedula_rif)}`}
        acciones={<Insignia tono={semaforoKyc(estado)} texto={textoOGuion(estado)} />}
      />

      <section className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <TarjetaMetrica
          rotulo="Estado KYC"
          valor={textoOGuion(estado)}
          nota={
            c.kyc_aprobado_por
              ? `Aprobado por ${c.kyc_aprobado_por} el ${formatearFecha(c.kyc_fecha)}`
              : "Pendiente de certificación"
          }
          acento={semaforoKyc(estado)}
        />
        <TarjetaMetrica
          rotulo="Documentos cubiertos"
          valor={
            checklist.datos
              ? `${checklist.datos.completados} / ${checklist.datos.total}`
              : "—"
          }
          nota="Requisitos con archivo en el repositorio"
          acento={
            checklist.datos && checklist.datos.completados === checklist.datos.total
              ? "verde"
              : "ambar"
          }
        />
        <TarjetaMetrica
          rotulo="Alta en el padrón"
          valor={formatearFecha(c.fecha_registro)}
          nota={textoOGuion(c.nacionalidad)}
        />
        <TarjetaMetrica
          rotulo="Actividad económica"
          valor={textoOGuion(c.actividad_economica)}
          nota={textoOGuion(c.tipo)}
        />
      </section>

      <div
        className="mb-6 inline-flex rounded-lg border border-borde bg-white p-1"
        role="tablist"
      >
        {(
          [
            ["datos", "Detalles del cliente"],
            ["documentos", "Checklist y documentos"],
            ["expedientes", "Historial de expedientes"],
          ] as Array<[Pestana, string]>
        ).map(([valor, etiqueta]) => (
          <button
            key={valor}
            type="button"
            role="tab"
            aria-selected={pestana === valor}
            onClick={() => setPestana(valor)}
            className={`rounded-md px-4 py-2 text-sm font-semibold transition ${
              pestana === valor
                ? "bg-kaizen-800 text-white"
                : "text-tinta-suave hover:text-kaizen-900"
            }`}
          >
            {etiqueta}
          </button>
        ))}
      </div>

      {pestana === "datos" ? (
        <section className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="rounded-xl border border-borde bg-white p-5 shadow-sm lg:col-span-2">
            <h2 className="mb-4 text-sm font-semibold text-kaizen-900">
              Identificación y contacto
            </h2>
            <Dato rotulo="Documento" valor={textoOGuion(c.cedula_rif)} />
            <Dato rotulo="Teléfono" valor={textoOGuion(c.telefono)} />
            <Dato rotulo="Correo" valor={textoOGuion(c.email)} />
            <Dato rotulo="Dirección" valor={textoOGuion(c.direccion)} />
            <Dato rotulo="Nacimiento" valor={formatearFecha(c.fecha_nacimiento)} />
            {c.tipo !== "Natural" && (
              <>
                <Dato rotulo="Representante legal" valor={textoOGuion(c.nombre_rep)} />
                <Dato rotulo="Documento del representante" valor={textoOGuion(c.cedula_rep)} />
                <Dato rotulo="Cargo" valor={textoOGuion(c.cargo_rep)} />
              </>
            )}
          </div>

          <div className="rounded-xl border border-borde bg-white p-5 shadow-sm">
            <h2 className="mb-4 text-sm font-semibold text-kaizen-900">
              Debida diligencia
            </h2>
            <p className="text-sm text-tinta-suave">
              {textoOGuion(c.obs_kyc) === "—"
                ? "Sin observaciones registradas."
                : c.obs_kyc}
            </p>

            <div className="mt-5">
              {puedeAprobar ? (
                <button
                  type="button"
                  className={`${BOTON.primario} w-full`}
                  onClick={() => setAprobando(true)}
                >
                  Aprobar KYC
                </button>
              ) : (
                <p className="rounded-lg bg-verde-fondo px-4 py-3 text-sm text-verde-trazo">
                  Expediente en {estado}: no admite una nueva aprobación.
                </p>
              )}
            </div>
          </div>
        </section>
      ) : pestana === "documentos" ? (
        <ChecklistDocumental
          cliId={cliId}
          checklist={checklist.datos}
          error={checklist.error}
          alRecargar={() => {
            checklist.recargar();
            cliente.recargar();
          }}
        />
      ) : (
        <HistorialExpedientes cliente={c.nombre ?? ""} />
      )}

      <ModalAprobarKyc
        abierto={aprobando}
        cliId={cliId}
        pendientes={
          checklist.datos ? checklist.datos.total - checklist.datos.completados : 0
        }
        alCerrar={() => setAprobando(false)}
        alAprobar={() => {
          cliente.recargar();
          checklist.recargar();
        }}
      />
    </>
  );
}

/**
 * Aprobación del KYC.
 *
 * Advierte de los requisitos sin documento pero no bloquea: en la operación hay
 * expedientes que se cierran con documentación aportada por otra vía, y quien
 * aprueba es Cumplimiento. El backend sí rechaza aprobar dos veces.
 */
function ModalAprobarKyc({
  abierto,
  cliId,
  pendientes,
  alCerrar,
  alAprobar,
}: {
  abierto: boolean;
  cliId: number;
  pendientes: number;
  alCerrar: () => void;
  alAprobar: () => void;
}) {
  const [observaciones, setObservaciones] = useState("");
  const { notificar } = useAvisos();
  const accion = useAccion(() => aprobarKyc(cliId, observaciones));

  const cerrar = () => {
    accion.limpiarError();
    setObservaciones("");
    alCerrar();
  };

  const confirmar = async () => {
    if (await accion.ejecutar()) {
      notificar("exito", "KYC aprobado", "El expediente quedó certificado.");
      alAprobar();
      cerrar();
    }
  };

  return (
    <Modal
      abierto={abierto}
      titulo="Aprobar el expediente KYC"
      descripcion="La aprobación queda firmada con su usuario y la fecha de hoy."
      alCerrar={cerrar}
      pie={
        <>
          <button type="button" className={BOTON.neutro} onClick={cerrar}>
            Cancelar
          </button>
          <button
            type="button"
            className={BOTON.primario}
            disabled={accion.enviando}
            onClick={confirmar}
          >
            {accion.enviando && <Girador />}
            Aprobar KYC
          </button>
        </>
      }
    >
      <div className="space-y-4">
        {pendientes > 0 && (
          <p className="rounded-lg bg-ambar-fondo px-4 py-3 text-sm text-ambar-trazo">
            Quedan {pendientes} requisitos sin documento en el repositorio.
            Compruebe que dispone de ellos por otra vía antes de certificar.
          </p>
        )}

        <label className="block">
          <span className="text-xs font-semibold tracking-wide text-tinta-suave uppercase">
            Observaciones
          </span>
          <textarea
            rows={4}
            value={observaciones}
            onChange={(evento) => setObservaciones(evento.target.value)}
            placeholder="Conclusiones de la debida diligencia."
            className={`mt-1.5 resize-y ${CAMPO}`}
          />
        </label>

        {accion.error && <Alerta error={accion.error} />}
      </div>
    </Modal>
  );
}

function Volver() {
  return (
    <Link
      href="/clients"
      className="mb-4 inline-flex items-center gap-2 text-sm font-semibold text-kaizen-600 transition hover:text-kaizen-900"
    >
      <span aria-hidden>←</span> Volver al padrón
    </Link>
  );
}

function Dato({ rotulo, valor }: { rotulo: string; valor: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-borde py-2 last:border-0">
      <span className="text-sm text-tinta-suave">{rotulo}</span>
      <span className="text-right text-sm font-semibold text-kaizen-900">{valor}</span>
    </div>
  );
}
