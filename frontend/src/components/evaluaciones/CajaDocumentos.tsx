"use client";

/**
 * Caja de documentos de la solicitud.
 *
 * Una zona donde soltar archivos y, debajo, los que ya están cargados. No es un
 * checklist: la operación aporta los papeles que tenga —dos avalúos, tres
 * facturas— y ninguno es obligatorio para poder guardar, así que una lista de
 * casillas prometería una exigencia que el circuito no aplica aquí.
 *
 * La relación de documentos necesarios se muestra al final, como referencia de
 * lectura: dice qué conviene adjuntar sin convertirse en un formulario.
 *
 * Se presenta de dos formas. Como tarjeta propia en la pantalla de alta y en la
 * ficha, donde es un bloque más; «integrada» dentro del formulario de Legal,
 * sin marco propio, porque allí no es una sección aparte sino el material que
 * se está evaluando.
 *
 * Quien la ve está restringido: Comercial, que reúne los documentos, y Legal,
 * que los inspecciona y solo descarga. Para Riesgo, Cumplimiento y el Comité la
 * caja no existe —ni aquí ni en la API—: evalúan con lo que cada etapa registra
 * en el expediente, no con los títulos de propiedad del garante.
 *
 * **Antes de que el expediente exista.** En la pantalla de alta no hay todavía
 * un expediente contra el que cargar, así que con `expId` nulo la caja trabaja
 * en seco: acumula los archivos elegidos, los muestra igual y los entrega a la
 * pantalla, que los sube en cuanto la solicitud queda abierta. Así el análisis
 * se prepara entero de una vez en lugar de en dos pantallas.
 */

import { useRef, useState } from "react";

import { Alerta } from "@/components/ui/Alerta";
import { BOTON } from "@/components/ui/Modal";
import { Girador } from "@/components/ui/Skeleton";
import { useAvisos } from "@/components/ui/Toast";
import {
  cargarDocumentosOperacion,
  descargarDocumentoOperacion,
  retirarDocumentoOperacion,
  sincronizarDocumentoOperacion,
  useDocumentosOperacion,
  type DocumentoOperacion,
} from "@/hooks/useDocumentosOperacion";
import type { TipoExpediente } from "@/types/api";
import { ApiError } from "@/utils/apiClient";
import { guardarComo } from "@/utils/descargas";
import { formatearFecha } from "@/utils/format";

/** Roles que aportan los documentos del crédito en la ficha y alta general. Comercial los reúne. */
const ROLES_CARGA = ["Comercial", "Superadmin"];

/** Roles que pueden verlos: los mismos que admite la API. */
const ROLES_LECTURA = [
  "Comercial",
  "Legal",
  "Comité",
  "Riesgo",
  "Compliance",
  "Superadmin",
];

const NECESARIOS: Array<{ grupo: string; nota: string; items: string[] }> = [
  {
    grupo: "Documentos del solicitante (vigentes)",
    nota: "Acreditan quién pide y con qué respaldo.",
    items: [
      "Estados financieros recientes.",
      "Declaraciones de impuestos.",
      "Comprobantes de ingresos actuales.",
      "Certificados de vigencia de poderes de la empresa.",
    ],
  },
  {
    grupo: "Documentos de la operación y la garantía (específicos)",
    nota: "Acreditan el bien que respalda esta solicitud en concreto.",
    items: [
      "Títulos de propiedad del bien que se ofrece en garantía.",
      "Avalúos comerciales recientes.",
      "Facturas de los bienes a prendar.",
    ],
  },
];

export function puedeCargarDocumentos(rol: string | undefined): boolean {
  return Boolean(rol && ROLES_CARGA.includes(rol));
}

export function puedeVerDocumentos(rol: string | undefined): boolean {
  return Boolean(rol && ROLES_LECTURA.includes(rol));
}

/**
 * Tono del estado frente a SharePoint.
 *
 * «Desactualizado» no es un fallo: el archivo del repositorio es mas nuevo que
 * el que viajo, y por eso se avisa en ambar en lugar de en rojo.
 */
function tonoSincronia(estado: string): string {
  if (estado === "Sincronizado") return "bg-verde-fondo text-verde-trazo";
  if (estado === "Desactualizado") return "bg-ambar-fondo text-ambar-trazo";
  return "bg-neutro-fondo text-neutro-trazo";
}

/**
 * Avance de la carga.
 *
 * Mientras el navegador informa del total, la barra marca la fracción real
 * enviada. Si no lo informa —`lengthComputable` falso en archivos pequeños o
 * con ciertos proxys—, se muestra una barra indeterminada en lugar de inventar
 * un porcentaje que no se corresponde con nada.
 */
function BarraProgreso({ valor, etiqueta }: { valor: number; etiqueta: string }) {
  const porcentaje = Math.round(Math.min(Math.max(valor, 0), 1) * 100);
  const indeterminada = valor <= 0;

  return (
    <div className="mt-4" aria-live="polite">
      <div className="flex items-baseline justify-between gap-3">
        <p className="min-w-0 truncate text-xs text-tinta-suave">{etiqueta}</p>
        <p className="text-xs font-semibold text-tinta tabular-nums">
          {indeterminada ? "Enviando…" : `${porcentaje}%`}
        </p>
      </div>
      <div
        className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-borde"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={indeterminada ? undefined : porcentaje}
        aria-label={`Carga de ${etiqueta}`}
      >
        <div
          className={`h-full rounded-full bg-kaizen-600 transition-[width] duration-150 ${
            indeterminada ? "w-1/3 animate-pulse" : ""
          }`}
          style={indeterminada ? undefined : { width: `${porcentaje}%` }}
        />
      </div>
    </div>
  );
}

function tamanoLegible(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function CajaDocumentos({
  tipo,
  expId,
  puedeCargar,
  pendientes,
  alCambiarPendientes,
  variante = "tarjeta",
  titulo,
  descripcion,
  aceptar,
  ocultarReferencia = false,
}: {
  tipo: TipoExpediente;
  /** Nulo mientras la solicitud no esté abierta: la caja retiene los archivos. */
  expId: number | null;
  puedeCargar: boolean;
  pendientes?: File[];
  alCambiarPendientes?: (archivos: File[]) => void;
  /** `integrada` renuncia al marco propio para vivir dentro de otro formulario. */
  variante?: "tarjeta" | "integrada";
  titulo?: string;
  descripcion?: string;
  aceptar?: string;
  ocultarReferencia?: boolean;
}) {
  // Sin expediente no hay nada que consultar; el hook queda declarado igual
  // porque no se puede condicionar, pero inactivo.
  const consulta = useDocumentosOperacion(tipo, expId ?? 0, expId !== null);
  const enEspera = pendientes ?? [];
  const { notificar, notificarError } = useAvisos();
  const entrada = useRef<HTMLInputElement>(null);

  const [documentos, setDocumentos] = useState<DocumentoOperacion[] | null>(null);
  const [cargando, setCargando] = useState(false);
  const [encima, setEncima] = useState(false);
  // Fracción enviada y qué se está enviando: una carga de varios megabytes sin
  // señal de avance parece colgada.
  const [progreso, setProgreso] = useState(0);
  const [enCurso, setEnCurso] = useState<string>("");
  const [sincronizando, setSincronizando] = useState<number | null>(null);

  // La lista que manda es la que devuelve una carga; mientras no haya ninguna,
  // la de la consulta inicial.
  const lista = documentos ?? consulta.datos ?? [];

  const subir = async (archivos: File[]) => {
    if (archivos.length === 0) return;

    // Todavía sin expediente: se guardan en la pantalla y se suben al abrirlo.
    if (expId === null) {
      alCambiarPendientes?.([...enEspera, ...archivos]);
      if (entrada.current) entrada.current.value = "";
      return;
    }

    setCargando(true);
    setProgreso(0);
    setEnCurso(
      archivos.length === 1
        ? archivos[0].name
        : `${archivos.length} archivos (${tamanoLegible(
            archivos.reduce((suma, a) => suma + a.size, 0),
          )})`,
    );
    try {
      setDocumentos(
        await cargarDocumentosOperacion(tipo, expId, archivos, setProgreso),
      );
      notificar(
        "exito",
        "Documentos cargados",
        archivos.length === 1
          ? `Se guardó ${archivos[0].name}.`
          : `Se guardaron ${archivos.length} archivos.`,
      );
    } catch (fallo) {
      notificarError(
        fallo instanceof ApiError
          ? fallo
          : new ApiError(0, "No se pudieron cargar los documentos."),
      );
    } finally {
      setCargando(false);
      setProgreso(0);
      setEnCurso("");
      if (entrada.current) entrada.current.value = "";
    }
  };

  const descargar = async (documento: DocumentoOperacion) => {
    if (expId === null) return;
    try {
      guardarComo(await descargarDocumentoOperacion(tipo, expId, documento.id));
    } catch (fallo) {
      notificarError(
        fallo instanceof ApiError
          ? fallo
          : new ApiError(0, "No se pudo descargar el documento."),
      );
    }
  };

  const sincronizar = async (documento: DocumentoOperacion) => {
    if (expId === null) return;
    setSincronizando(documento.id);
    try {
      const actualizado = await sincronizarDocumentoOperacion(
        tipo,
        expId,
        documento.id,
      );
      setDocumentos(
        lista.map((d) => (d.id === actualizado.id ? actualizado : d)),
      );
      notificar(
        "exito",
        "Documento sincronizado",
        `${documento.file_name} ya está en SharePoint.`,
      );
    } catch (fallo) {
      notificarError(
        fallo instanceof ApiError
          ? fallo
          : new ApiError(0, "No se pudo sincronizar el documento."),
      );
    } finally {
      setSincronizando(null);
    }
  };

  const retirar = async (documento: DocumentoOperacion) => {
    if (expId === null) return;
    try {
      await retirarDocumentoOperacion(tipo, expId, documento.id);
      setDocumentos(lista.filter((d) => d.id !== documento.id));
      notificar("aviso", "Documento retirado", `${documento.file_name} ya no se ofrece.`);
    } catch (fallo) {
      notificarError(
        fallo instanceof ApiError
          ? fallo
          : new ApiError(0, "No se pudo retirar el documento."),
      );
    }
  };

  const integrada = variante === "integrada";
  const marco = integrada
    ? "border-t border-borde pt-5"
    : "rounded-xl border border-borde bg-white p-6 shadow-sm";
  const marcoReferencia = integrada
    ? "mt-5 rounded-lg bg-lienzo p-4"
    : "mt-4 rounded-xl border border-borde bg-white p-6 shadow-sm";

  return (
    <section
      className={integrada ? "mt-6" : "mb-8"}
      aria-label="Documentos de la solicitud"
    >
      <div className={marco}>
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-sm font-bold text-kaizen-900">
              {titulo ?? "Documentos de la solicitud"}
            </h2>
            <p className="mt-1 text-xs text-tinta-suave">
              {descripcion ??
                "Expediente y garantía. Legal los descarga desde aquí para inspeccionarlos."}
            </p>
          </div>
          <span className="text-xs text-tinta-suave">
            {(() => {
              const total = expId === null ? enEspera.length : lista.length;
              if (total === 0) return "Sin documentos";
              return `${total} ${total === 1 ? "documento" : "documentos"}`;
            })()}
          </span>
        </div>

        {puedeCargar && (
          <div
            onDragOver={(evento) => {
              evento.preventDefault();
              setEncima(true);
            }}
            onDragLeave={() => setEncima(false)}
            onDrop={(evento) => {
              evento.preventDefault();
              setEncima(false);
              void subir(Array.from(evento.dataTransfer.files));
            }}
            className={`mt-5 rounded-xl border-2 border-dashed px-6 py-8 text-center transition ${
              encima
                ? "border-kaizen-600 bg-kaizen-100/40"
                : "border-borde bg-lienzo"
            }`}
          >
            <p className="text-sm font-semibold text-tinta">
              Arrastre los archivos aquí
            </p>
            <p className="mt-1 text-xs text-tinta-suave">
              {aceptar === ".pdf" || aceptar === "application/pdf"
                ? "Archivos PDF (Contratos, anexos jurídicos) · hasta 25 MB"
                : "PDF, imágenes u hojas de cálculo · hasta 25 MB por archivo"}
            </p>

            <input
              ref={entrada}
              type="file"
              multiple
              accept={aceptar}
              className="hidden"
              onChange={(evento) =>
                void subir(Array.from(evento.target.files ?? []))
              }
            />
            <button
              type="button"
              className={`${BOTON.primario} mt-4`}
              disabled={cargando}
              onClick={() => entrada.current?.click()}
            >
              {cargando && <Girador />}
              {cargando ? "Cargando…" : "Seleccionar archivos"}
            </button>

            {cargando && <BarraProgreso valor={progreso} etiqueta={enCurso} />}
          </div>
        )}

        <div className="mt-5">
          {expId === null ? (
            enEspera.length === 0 ? (
              <p className="rounded-lg bg-lienzo px-4 py-3 text-sm text-tinta-suave">
                Todavía no ha elegido ningún documento. Se cargarán en cuanto
                abra la solicitud.
              </p>
            ) : (
              <ul className="space-y-2">
                {enEspera.map((archivo, indice) => (
                  <li
                    key={`${archivo.name}-${indice}`}
                    className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-borde px-4 py-3"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-tinta">
                        {archivo.name}
                      </p>
                      <p className="mt-0.5 text-xs text-tinta-suave">
                        {tamanoLegible(archivo.size)} · se cargará al abrir la
                        solicitud
                      </p>
                    </div>
                    <button
                      type="button"
                      className="rounded-lg px-3 py-1.5 text-xs font-semibold text-rojo-trazo transition hover:underline"
                      onClick={() =>
                        alCambiarPendientes?.(
                          enEspera.filter((_, i) => i !== indice),
                        )
                      }
                    >
                      Quitar
                    </button>
                  </li>
                ))}
              </ul>
            )
          ) : consulta.cargando && lista.length === 0 ? (
            <p className="text-sm text-tinta-suave">Consultando documentos…</p>
          ) : consulta.error && documentos === null ? (
            <Alerta error={consulta.error} alReintentar={consulta.recargar} />
          ) : lista.length === 0 ? (
            <p className="rounded-lg bg-lienzo px-4 py-3 text-sm text-tinta-suave">
              Todavía no hay documentos cargados en esta solicitud.
            </p>
          ) : (
            <ul className=" flex flex-wrap gap-2">
              {lista.map((documento) => (
                <li
                  key={documento.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-borde px-4 py-3 min-h-[100px] w-full md:w-[calc(50%-0.5rem)]"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-tinta">
                      {documento.file_name}
                    </p>
                    <p className="mt-0.5 text-xs text-tinta-suave">
                      {tamanoLegible(documento.tamano_bytes)} ·{" "}
                      {formatearFecha(documento.fecha_carga)} ·{" "}
                      {documento.cargado_por || "—"}
                    </p>
                    <p className="mt-1.5 flex flex-wrap items-center gap-2">
                      <span
                        className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${tonoSincronia(
                          documento.sp_sync_status,
                        )}`}
                      >
                        SharePoint: {documento.sp_sync_status}
                      </span>
                      {documento.fecha_sync && (
                        <span className="text-xs text-tinta-suave">
                          {formatearFecha(documento.fecha_sync)}
                        </span>
                      )}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      className="rounded-lg border border-borde px-3 py-1.5 text-xs font-semibold text-tinta transition hover:border-kaizen-600 hover:text-kaizen-600"
                      onClick={() => void descargar(documento)}
                    >
                      Descargar
                    </button>
                    {puedeCargar && (
                      <button
                        type="button"
                        className="rounded-lg border border-borde px-3 py-1.5 text-xs font-semibold text-tinta transition hover:border-kaizen-600 hover:text-kaizen-600 disabled:opacity-60"
                        disabled={sincronizando === documento.id}
                        onClick={() => void sincronizar(documento)}
                      >
                        {sincronizando === documento.id
                          ? "Sincronizando…"
                          : documento.sp_sync_status === "Sincronizado"
                            ? "Resincronizar"
                            : "Sincronizar"}
                      </button>
                    )}
                    {puedeCargar && (
                      <button
                        type="button"
                        className="rounded-lg px-3 py-1.5 text-xs font-semibold text-rojo-trazo transition hover:underline"
                        onClick={() => void retirar(documento)}
                      >
                        Retirar
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {!ocultarReferencia && (
        <div className={marcoReferencia}>
          <h3 className="text-sm font-bold text-kaizen-900">
            Documentos necesarios
          </h3>
          <p className="mt-1 text-xs text-tinta-suave">
            Relación de referencia de lo que conviene adjuntar a la solicitud.
          </p>

        <div className="mt-4 grid grid-cols-1 gap-5 md:grid-cols-2">
          {NECESARIOS.map((bloque) => (
            <div key={bloque.grupo}>
              <p className="text-xs font-semibold tracking-wide text-tinta uppercase">
                {bloque.grupo}
              </p>
              <p className="mt-1 text-xs text-tinta-suave">{bloque.nota}</p>
              <ul className="mt-2 space-y-1.5">
                {bloque.items.map((item) => (
                  <li key={item} className="flex gap-2 text-sm text-tinta-suave">
                    <span aria-hidden className="text-kaizen-600">
                      ·
                    </span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
      )}
    </section>
  );
}
