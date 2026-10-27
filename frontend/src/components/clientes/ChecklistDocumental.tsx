"use client";

/**
 * Checklist KYC con su gestión documental.
 *
 * Reproduce la progresión de la vista de Streamlit, fila a fila:
 *
 * 1. Requisito sin archivo → se ofrece el cargador.
 * 2. Requisito marcado pero sin archivo en el repositorio → se avisa de esa
 *    incoherencia y se sigue pidiendo el adjunto; la marca sola no basta.
 * 3. Requisito cubierto → descarga, reemplazo y, si procede, sincronización.
 * 4. Reemplazo → el archivo entra como `Desactualizado`, porque el que está en
 *    SharePoint ha dejado de ser la versión vigente.
 */

import { useRef, useState } from "react";

import { Alerta } from "@/components/ui/Alerta";
import { BOTON } from "@/components/ui/Modal";
import { Insignia } from "@/components/ui/Semaforo";
import { Girador } from "@/components/ui/Skeleton";
import { useAvisos } from "@/components/ui/Toast";
import {
  SYNC_DESACTUALIZADO,
  SYNC_OK,
  actualizarMarcas,
  cargarDocumento,
  descargarDocumento,
  sincronizarDocumento,
  type Checklist,
  type ItemChecklist,
} from "@/hooks/useDocumentos";
import { ApiError } from "@/utils/apiClient";
import { guardarComo } from "@/utils/descargas";
import type { Semaforo } from "@/utils/estados";

function tonoSync(estado: string): Semaforo {
  if (estado === SYNC_OK) return "verde";
  if (estado === SYNC_DESACTUALIZADO) return "rojo";
  return "ambar";
}

export function ChecklistDocumental({
  cliId,
  checklist,
  error,
  alRecargar,
}: {
  cliId: number;
  checklist: Checklist | null;
  error: ApiError | null;
  alRecargar: () => void;
}) {
  const { notificar, notificarError } = useAvisos();
  const [ocupado, setOcupado] = useState<string | null>(null);
  const [enReemplazo, setEnReemplazo] = useState<Set<string>>(new Set());

  if (error) return <Alerta error={error} alReintentar={alRecargar} />;
  if (!checklist) return null;

  const alternarReemplazo = (docName: string, activo: boolean) => {
    setEnReemplazo((actuales) => {
      const copia = new Set(actuales);
      if (activo) copia.add(docName);
      else copia.delete(docName);
      return copia;
    });
  };

  const conAviso = async (
    docName: string,
    operacion: () => Promise<void>,
  ): Promise<void> => {
    setOcupado(docName);
    try {
      await operacion();
    } catch (fallo: unknown) {
      notificarError(
        fallo instanceof ApiError
          ? fallo
          : new ApiError(0, "No se pudo completar la operación."),
      );
    } finally {
      setOcupado(null);
    }
  };

  const subir = (item: ItemChecklist, archivo: File) =>
    conAviso(item.doc_name, async () => {
      const reemplazo = item.tiene_archivo;
      const resultado = await cargarDocumento(cliId, item.doc_name, archivo);
      alternarReemplazo(item.doc_name, false);
      notificar(
        "exito",
        reemplazo ? "Documento reemplazado" : "Documento cargado",
        `${resultado.archivo} en ${resultado.carpeta}.`,
      );
      alRecargar();
    });

  const descargar = (item: ItemChecklist) =>
    conAviso(item.doc_name, async () => {
      if (item.documento_id === null) return;
      guardarComo(await descargarDocumento(cliId, item.documento_id));
    });

  const sincronizar = (item: ItemChecklist) =>
    conAviso(item.doc_name, async () => {
      if (item.documento_id === null) return;
      await sincronizarDocumento(cliId, item.documento_id);
      notificar("exito", "Sincronizado", `${item.file_name} viajó a SharePoint.`);
      alRecargar();
    });

  const marcar = (item: ItemChecklist, valor: boolean) =>
    conAviso(item.doc_name, async () => {
      await actualizarMarcas(cliId, { [item.doc_name]: valor });
      alRecargar();
    });

  const avance = checklist.total === 0 ? 0 : (checklist.completados / checklist.total) * 100;

  return (
    <section>
      <div className="mb-5 rounded-xl border border-borde bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h2 className="text-sm font-semibold text-kaizen-900">
            Checklist de documentos KYC
          </h2>
          <p className="text-sm text-tinta-suave tabular-nums">
            {checklist.completados} de {checklist.total} requisitos con documento
          </p>
        </div>
        <div className="mt-3 h-2 overflow-hidden rounded-full bg-neutro-fondo">
          <div
            className="h-full rounded-full bg-kaizen-600 transition-all"
            style={{ width: `${avance}%` }}
          />
        </div>
        <p className="mt-2 text-xs text-tinta-suave">
          Los requisitos exigibles dependen del tipo de cliente:{" "}
          {checklist.tipo === "Natural" ? "persona natural" : "persona jurídica"}.
        </p>
      </div>

      <ul className="space-y-3">
        {checklist.items.map((item) => (
          <FilaRequisito
            key={item.doc_name}
            item={item}
            ocupado={ocupado === item.doc_name}
            reemplazando={enReemplazo.has(item.doc_name)}
            alReemplazar={(activo) => alternarReemplazo(item.doc_name, activo)}
            alSubir={(archivo) => subir(item, archivo)}
            alDescargar={() => descargar(item)}
            alSincronizar={() => sincronizar(item)}
            alMarcar={(valor) => marcar(item, valor)}
          />
        ))}
      </ul>
    </section>
  );
}

function FilaRequisito({
  item,
  ocupado,
  reemplazando,
  alReemplazar,
  alSubir,
  alDescargar,
  alSincronizar,
  alMarcar,
}: {
  item: ItemChecklist;
  ocupado: boolean;
  reemplazando: boolean;
  alReemplazar: (activo: boolean) => void;
  alSubir: (archivo: File) => void;
  alDescargar: () => void;
  alSincronizar: () => void;
  alMarcar: (valor: boolean) => void;
}) {
  const entrada = useRef<HTMLInputElement>(null);
  const cubierto = item.tiene_archivo && !reemplazando;

  return (
    <li className="rounded-xl border border-borde bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <label className="flex min-w-0 flex-1 items-start gap-3">
          <input
            type="checkbox"
            checked={item.marcado}
            disabled={ocupado}
            onChange={(evento) => alMarcar(evento.target.checked)}
            className="mt-0.5 h-4 w-4 shrink-0 accent-kaizen-800"
          />
          <span className="min-w-0">
            <span className="block text-sm font-medium text-tinta">
              {item.doc_name}
            </span>
            {item.file_name && (
              <span className="block truncate text-xs text-tinta-suave">
                {item.file_name}
              </span>
            )}
          </span>
        </label>

        <div className="flex shrink-0 items-center gap-2">
          {ocupado && <Girador />}
          {item.tiene_archivo && (
            <Insignia tono={tonoSync(item.sp_sync_status)} texto={item.sp_sync_status} />
          )}
        </div>
      </div>

      {item.aviso && (
        <p className="mt-3 rounded-lg bg-rojo-fondo px-3 py-2 text-xs text-rojo-trazo">
          {item.aviso}
        </p>
      )}

      {item.marcado && !item.tiene_archivo && (
        <p className="mt-3 rounded-lg bg-ambar-fondo px-3 py-2 text-xs text-ambar-trazo">
          Marcado sin archivo: adjunte el documento para dar el requisito por
          cubierto.
        </p>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        {cubierto ? (
          <>
            <button
              type="button"
              className={BOTON.primario}
              disabled={ocupado}
              onClick={alDescargar}
            >
              Ver documento
            </button>
            <button
              type="button"
              className={BOTON.neutro}
              disabled={ocupado}
              onClick={() => alReemplazar(true)}
            >
              Reemplazar
            </button>
            {item.sp_sync_status !== SYNC_OK && (
              <button
                type="button"
                className={BOTON.aviso}
                disabled={ocupado}
                onClick={alSincronizar}
              >
                Sincronizar
              </button>
            )}
          </>
        ) : (
          <>
            <input
              ref={entrada}
              type="file"
              className="hidden"
              onChange={(evento) => {
                const archivo = evento.target.files?.[0];
                if (archivo) alSubir(archivo);
                evento.target.value = "";
              }}
            />
            <button
              type="button"
              className={BOTON.primario}
              disabled={ocupado}
              onClick={() => entrada.current?.click()}
            >
              {reemplazando ? "Elegir el archivo que sustituye al actual" : "Adjuntar"}
            </button>
            {reemplazando && (
              <button
                type="button"
                className={BOTON.neutro}
                disabled={ocupado}
                onClick={() => alReemplazar(false)}
              >
                Cancelar
              </button>
            )}
          </>
        )}
      </div>
    </li>
  );
}
