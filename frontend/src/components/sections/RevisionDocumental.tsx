"use client";

/**
 * Revisión documental de la etapa de Cumplimiento.
 *
 * Es la vista de solo lectura del checklist KYC del cliente, pensada para que
 * quien certifica pueda comprobar la documentación sin salir del circuito ni
 * perder lo que lleve escrito en el formulario.
 *
 * Lo que decide si un requisito está cubierto es la existencia del archivo, no
 * la casilla marcada: el backend devuelve las dos cosas por separado y aquí se
 * distingue el requisito cubierto del marcado a mano sin adjuntar, que es el
 * caso que más veces deja pasar documentación que no está.
 *
 * La carga y el reemplazo siguen viviendo en la ficha del cliente: aquí solo se
 * revisa y se descarga, para no duplicar la gestión documental en dos sitios.
 */

import Link from "next/link";
import { useState } from "react";

import {
  SYNC_DESACTUALIZADO,
  SYNC_OK,
  descargarDocumento,
  useChecklist,
  type ItemChecklist,
} from "@/hooks/useDocumentos";
import { Alerta, SinResultados } from "@/components/ui/Alerta";
import { BOTON } from "@/components/ui/Modal";
import { Girador, SkeletonTabla } from "@/components/ui/Skeleton";
import { useAvisos } from "@/components/ui/Toast";
import { ApiError } from "@/utils/apiClient";
import { guardarComo } from "@/utils/descargas";

export function RevisionDocumental({ clienteId }: { clienteId: number | null }) {
  // El hook se declara siempre: los hooks no admiten condicionales. Queda
  // inactivo cuando el expediente no está ligado a una ficha de cliente.
  const { datos, cargando, error, recargar } = useChecklist(
    clienteId ?? 0,
    clienteId !== null,
  );
  const { notificarError } = useAvisos();
  const [descargando, setDescargando] = useState<string | null>(null);

  if (clienteId === null) {
    return (
      <SinResultados mensaje="El expediente no está ligado a una ficha del padrón, así que no tiene checklist documental asociado." />
    );
  }

  if (cargando) return <SkeletonTabla columnas={3} filas={6} />;
  if (error) return <Alerta error={error} alReintentar={recargar} />;
  if (!datos) return null;

  const descargar = async (item: ItemChecklist) => {
    if (item.documento_id === null) return;
    setDescargando(item.doc_name);
    try {
      const descarga = await descargarDocumento(clienteId, item.documento_id);
      // El checklist ya trae el nombre en UTF-8 limpio; se prefiere al de la
      // cabecera, que depende de cómo lo codifique el servidor.
      guardarComo({ ...descarga, nombre: item.file_name ?? descarga.nombre });
    } catch (fallo: unknown) {
      notificarError(
        fallo instanceof ApiError
          ? fallo
          : new ApiError(0, "No se pudo descargar el documento."),
      );
    } finally {
      setDescargando(null);
    }
  };

  const faltantes = datos.items.filter((item) => !item.tiene_archivo);
  const avance =
    datos.total === 0 ? 0 : (datos.completados / datos.total) * 100;

  return (
    <section className="rounded-xl border border-borde bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-kaizen-900">
            Revisión documental
          </h3>
          <p className="mt-1 text-xs text-tinta-suave">
            Checklist KYC exigible a un cliente{" "}
            {datos.tipo === "Natural" ? "persona natural" : "persona jurídica"}.
          </p>
        </div>
        <Link
          href={`/clients/${clienteId}`}
          className="text-sm font-semibold text-kaizen-600 transition hover:text-kaizen-900"
        >
          Gestionar en la ficha del cliente →
        </Link>
      </div>

      <div className="mt-4">
        <div className="flex items-baseline justify-between gap-3">
          <p className="text-sm text-tinta-suave tabular-nums">
            {datos.completados} de {datos.total} requisitos con documento
          </p>
          <p className="text-xs font-semibold text-tinta-suave uppercase">
            {datos.kyc_status}
          </p>
        </div>
        <div className="mt-2 h-2 overflow-hidden rounded-full bg-neutro-fondo">
          <div
            className={`h-full rounded-full transition-all ${
              faltantes.length === 0 ? "bg-verde-trazo" : "bg-kaizen-600"
            }`}
            style={{ width: `${avance}%` }}
          />
        </div>
      </div>

      {faltantes.length > 0 ? (
        <div className="mt-4 rounded-lg border border-ambar-trazo/30 bg-ambar-fondo px-4 py-3">
          <p className="text-sm font-semibold text-ambar-trazo">
            Faltan {faltantes.length} de {datos.total} requisitos obligatorios
          </p>
          <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-ambar-trazo">
            {faltantes.map((item) => (
              <li key={item.doc_name}>{item.doc_name}</li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="mt-4 rounded-lg border border-verde-trazo/30 bg-verde-fondo px-4 py-3 text-sm font-semibold text-verde-trazo">
          Documentación completa: los {datos.total} requisitos tienen archivo en
          el repositorio.
        </p>
      )}

      <ul className="mt-5 space-y-2">
        {datos.items.map((item) => (
          <Requisito
            key={item.doc_name}
            item={item}
            descargando={descargando === item.doc_name}
            alDescargar={() => void descargar(item)}
          />
        ))}
      </ul>
    </section>
  );
}

function Requisito({
  item,
  descargando,
  alDescargar,
}: {
  item: ItemChecklist;
  descargando: boolean;
  alDescargar: () => void;
}) {
  const cubierto = item.tiene_archivo;
  const marcadoSinArchivo = item.marcado && !item.tiene_archivo;

  return (
    <li
      className={`flex flex-wrap items-center justify-between gap-3 rounded-lg border px-4 py-3 ${
        cubierto ? "border-borde bg-white" : "border-ambar-trazo/30 bg-ambar-fondo/40"
      }`}
    >
      <div className="flex min-w-0 flex-1 items-start gap-3">
        <span
          className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
            cubierto
              ? "bg-verde-trazo text-white"
              : "bg-ambar-trazo/20 text-ambar-trazo"
          }`}
          aria-hidden
        >
          {cubierto ? "✓" : "!"}
        </span>
        <div className="min-w-0">
          <p className="text-sm font-medium text-tinta">{item.doc_name}</p>
          {item.file_name && (
            <p className="truncate text-xs text-tinta-suave">{item.file_name}</p>
          )}
          {marcadoSinArchivo && (
            <p className="text-xs font-semibold text-ambar-trazo">
              Marcado sin archivo en el repositorio
            </p>
          )}
          {item.aviso && (
            <p className="text-xs font-semibold text-rojo-trazo">{item.aviso}</p>
          )}
          <span className="sr-only">
            {cubierto ? "Requisito cubierto" : "Requisito pendiente"}
          </span>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        {cubierto && <InsigniaSync estado={item.sp_sync_status} />}
        {cubierto ? (
          <button
            type="button"
            className={`${BOTON.neutro} px-3 py-1.5 text-xs`}
            disabled={descargando}
            onClick={alDescargar}
          >
            {descargando && <Girador />}
            Descargar
          </button>
        ) : (
          <span className="rounded-full bg-ambar-trazo/15 px-3 py-1 text-xs font-semibold whitespace-nowrap text-ambar-trazo">
            Sin documento
          </span>
        )}
      </div>
    </li>
  );
}

function InsigniaSync({ estado }: { estado: string }) {
  const estilo =
    estado === SYNC_OK
      ? "bg-verde-fondo text-verde-trazo"
      : estado === SYNC_DESACTUALIZADO
        ? "bg-rojo-fondo text-rojo-trazo"
        : "bg-neutro-fondo text-neutro-trazo";

  return (
    <span
      className={`rounded-full px-3 py-1 text-xs font-semibold whitespace-nowrap ${estilo}`}
      title="Estado frente a SharePoint"
    >
      {estado}
    </span>
  );
}
