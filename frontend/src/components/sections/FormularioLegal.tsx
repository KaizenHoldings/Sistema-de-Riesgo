"use client";

/**
 * Formulario de Legal - Etapa Única Integral.
 *
 * Unifica en una sola etapa la descarga del contrato a nombre del cliente con
 * apartado formal de firma, la carga de recaudos legales en PDF, la evaluación
 * jurídica de garantías/vehículo y las decisiones del área (firma, devolución o
 * denegación).
 *
 * Cuando la etapa está aprobada, opera íntegramente en modo solo lectura.
 */

import { useState } from "react";

import { CajaDocumentos } from "@/components/evaluaciones/CajaDocumentos";
import {
  Bloque,
  CampoCasilla,
  CampoNumero,
  CampoSeleccion,
  CampoTexto,
  CampoTextoLargo,
  aNumero,
} from "@/components/sections/campos";
import { BOTON } from "@/components/ui/Modal";
import { Girador } from "@/components/ui/Skeleton";
import { useAvisos } from "@/components/ui/Toast";
import { descargarContrato } from "@/hooks/useDocumentos";
import { guardarComo } from "@/utils/descargas";
import {
  ETAPAS_DEVOLUCION_LEGAL,
  type EtapaDevolucion,
  type LegalAutoForm,
  type LegalCorpForm,
  type LegalForm,
  type ServiceResult,
  type TipoExpediente,
} from "@/business/workflows/types";

const TIPOS_VEHICULO = ["Nuevo", "Usado"] as const;

export function FormularioLegal({
  tipo,
  expId,
  montoCredito,
  enviando,
  bloqueado = false,
  datosExistentes,
  onRegistrar,
  onDevolver,
  onRechazar,
}: {
  tipo: TipoExpediente;
  expId: number;
  montoCredito: number;
  enviando: boolean;
  bloqueado?: boolean;
  datosExistentes?: Record<string, unknown>;
  onRegistrar: (form: LegalForm) => Promise<ServiceResult<unknown>>;
  onDevolver: (
    etapa: EtapaDevolucion,
    observaciones: string,
  ) => Promise<ServiceResult<unknown>>;
  onRechazar: (motivo: string) => Promise<ServiceResult<unknown>>;
}) {
  const { notificar } = useAvisos();
  const [descargandoContrato, setDescargandoContrato] = useState(false);
  const [mostrarSalidas, setMostrarSalidas] = useState(false);
  const [etapaDevolucion, setEtapaDevolucion] = useState<EtapaDevolucion>(
    ETAPAS_DEVOLUCION_LEGAL[0],
  );
  const [justificacion, setJustificacion] = useState("");

  // ── Estado Corporativo ─────────────────────────────────────────────
  const [descripcionGarantia, setDescripcionGarantia] = useState(() => {
    if (!datosExistentes?.garantias_json) return "";
    try {
      const gs =
        typeof datosExistentes.garantias_json === "string"
          ? JSON.parse(datosExistentes.garantias_json)
          : datosExistentes.garantias_json;
      if (Array.isArray(gs) && gs.length > 0) {
        return gs[0].descripcion || gs[0].desc || "";
      }
    } catch {}
    return "";
  });

  const [valorGarantia, setValorGarantia] = useState(() => {
    if (datosExistentes?.garantias_json) {
      try {
        const gs =
          typeof datosExistentes.garantias_json === "string"
            ? JSON.parse(datosExistentes.garantias_json)
            : datosExistentes.garantias_json;
        if (Array.isArray(gs) && gs.length > 0 && gs[0].valor) {
          return String(gs[0].valor);
        }
      } catch {}
    }
    return String(datosExistentes?.v_garantia ?? "0");
  });

  const [ltvCorp, setLtvCorp] = useState(() =>
    String(datosExistentes?.ltv_ratio ?? "0"),
  );
  const [vencimientoCorp, setVencimientoCorp] = useState(() =>
    datosExistentes?.fecha_vencimiento_garantia
      ? String(datosExistentes.fecha_vencimiento_garantia).slice(0, 10)
      : "",
  );
  const [custodiaCorp, setCustodiaCorp] = useState(() =>
    Boolean(datosExistentes?.custodia_fisica),
  );
  const [obsCorp, setObsCorp] = useState(() =>
    String(datosExistentes?.obs_leg ?? ""),
  );

  const recalcularLtvCorp = (valor: string) => {
    setValorGarantia(valor);
    const garantia = aNumero(valor);
    if (garantia > 0 && montoCredito > 0) {
      setLtvCorp(((montoCredito / garantia) * 100).toFixed(2));
    }
  };

  const enviarCorp = () => {
    const payload: LegalCorpForm = {
      garantias_json: JSON.stringify(
        descripcionGarantia.trim()
          ? [{ descripcion: descripcionGarantia.trim(), valor: aNumero(valorGarantia) }]
          : [],
      ),
      v_garantia: aNumero(valorGarantia),
      ltv_ratio: aNumero(ltvCorp),
      fecha_vencimiento_garantia: vencimientoCorp,
      custodia_fisica: custodiaCorp,
      obs_leg: obsCorp.trim(),
    };
    void onRegistrar(payload);
  };

  // ── Estado Automotriz ──────────────────────────────────────────────
  const [formAuto, setFormAuto] = useState(() => ({
    marca: String(datosExistentes?.marca ?? ""),
    modelo: String(datosExistentes?.modelo ?? ""),
    anio: String(datosExistentes?.anio ?? ""),
    vin: String(datosExistentes?.vin ?? ""),
    vehiculo_placa: String(datosExistentes?.vehiculo_placa ?? ""),
    tipo_vehiculo: String(datosExistentes?.tipo_vehiculo ?? "Nuevo"),
    precio_vehiculo: String(datosExistentes?.precio_vehiculo ?? "0"),
    enganche: String(datosExistentes?.enganche ?? "0"),
    plazo_meses: String(datosExistentes?.plazo_meses ?? "36"),
    ltv_ratio: String(datosExistentes?.ltv_ratio ?? "0"),
    seguro_vehiculo: Boolean(datosExistentes?.seguro_vehiculo),
    registro_lien: Boolean(datosExistentes?.registro_lien),
    fecha_vencimiento_seguro: datosExistentes?.fecha_vencimiento_seguro
      ? String(datosExistentes.fecha_vencimiento_seguro).slice(0, 10)
      : "",
    seguro_empresa: String(datosExistentes?.seguro_empresa ?? ""),
    seguro_poliza: String(datosExistentes?.seguro_poliza ?? ""),
    seguro_vigencia: datosExistentes?.seguro_vigencia
      ? String(datosExistentes.seguro_vigencia).slice(0, 10)
      : "",
    obs_leg: String(datosExistentes?.obs_leg ?? ""),
  }));

  const setAuto = (clave: keyof typeof formAuto, valor: string | boolean) =>
    setFormAuto((actual) => ({ ...actual, [clave]: valor }));

  const recalcularLtvAuto = (precio: string, enganche: string) => {
    const p = aNumero(precio);
    const e = aNumero(enganche);
    if (p > 0) {
      setFormAuto((actual) => ({
        ...actual,
        precio_vehiculo: precio,
        enganche: enganche,
        ltv_ratio: (((p - e) / p) * 100).toFixed(2),
      }));
    }
  };

  const enviarAuto = () => {
    const payload: LegalAutoForm = {
      marca: formAuto.marca.trim(),
      modelo: formAuto.modelo.trim(),
      anio: aNumero(formAuto.anio),
      vin: formAuto.vin.trim(),
      vehiculo_placa: formAuto.vehiculo_placa.trim(),
      tipo_vehiculo: formAuto.tipo_vehiculo as LegalAutoForm["tipo_vehiculo"],
      precio_vehiculo: aNumero(formAuto.precio_vehiculo),
      enganche: aNumero(formAuto.enganche),
      plazo_meses: aNumero(formAuto.plazo_meses),
      ltv_ratio: aNumero(formAuto.ltv_ratio),
      seguro_vehiculo: formAuto.seguro_vehiculo,
      registro_lien: formAuto.registro_lien,
      fecha_vencimiento_seguro: formAuto.fecha_vencimiento_seguro,
      seguro_empresa: formAuto.seguro_empresa.trim(),
      seguro_poliza: formAuto.seguro_poliza.trim(),
      seguro_vigencia: formAuto.seguro_vigencia,
      obs_leg: formAuto.obs_leg.trim(),
    };
    void onRegistrar(payload);
  };

  const manejarDescargaContrato = async () => {
    setDescargandoContrato(true);
    try {
      const archivo = await descargarContrato(tipo, expId);
      guardarComo(archivo);
      notificar(
        "exito",
        "Contrato generado",
        "El contrato formal se descargó correctamente a nombre del cliente.",
      );
    } catch (e) {
      notificar(
        "error",
        "Descarga de contrato",
        e instanceof Error ? e.message : "No se pudo descargar el contrato.",
      );
    } finally {
      setDescargandoContrato(false);
    }
  };

  return (
    <div className="rounded-xl border border-borde bg-white shadow-sm overflow-hidden">
      {/* ── Cabecera unificada de la etapa Legal ───────────────────── */}
      <div className="border-b border-borde p-5 bg-gradient-to-r from-kaizen-50/50 via-white to-white">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-kaizen-100 text-sm">
                ⚖️
              </span>
              <h3 className="text-sm font-semibold text-kaizen-900">
                Evaluación Legal
              </h3>
            </div>
            <p className="mt-1 text-xs text-tinta-suave">
              {tipo === "corp"
                ? "Gestión de contratos, garantías colaterales y suscripción jurídica."
                : "Gestión de contratos, identificación del vehículo, seguro, gravamen y suscripción."}
            </p>
          </div>

          {bloqueado ? (
            <span className="inline-flex items-center gap-1 rounded-full border border-verde-trazo/30 bg-verde-fondo px-3 py-1 text-xs font-semibold text-verde-trazo">
              <span>✓</span> Aprobada · Solo lectura
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full border border-kaizen-200 bg-kaizen-50 px-3 py-1 text-xs font-semibold text-kaizen-800">
              <span>●</span> Etapa en curso
            </span>
          )}
        </div>

        {bloqueado && (
          <div className="mt-3 rounded-lg border border-verde-trazo/30 bg-verde-fondo/70 p-3 text-xs text-verde-trazo">
            ✓ La evaluación Legal ya se encuentra firmada. Los campos se presentan en modo solo lectura para conservar la trazabilidad. Puede continuar descargando el contrato o revisando los recaudos adjuntos.
          </div>
        )}
      </div>

      <div className="p-5 space-y-6">
        {/* ── 1. Contrato y Documentos Legales ─────────────────────── */}
        <div className="rounded-xl border border-kaizen-200/80 bg-kaizen-50/30 p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-kaizen-100 px-2.5 py-0.5 text-xs font-semibold text-kaizen-800">
                <span>📄</span> Contrato del área de legal
              </span>
              <h4 className="mt-1.5 text-xs font-bold text-kaizen-900">
                Documento de contrato de crédito para firma del cliente
              </h4>
              <p className="mt-0.5 text-xs text-tinta-suave">
                Descargue el contrato formal emitido con la plantilla institucional a nombre del cliente con todas las condiciones y el apartado para su suscripción.
              </p>
            </div>
            <button
              type="button"
              onClick={() => void manejarDescargaContrato()}
              disabled={descargandoContrato}
              className={`${BOTON.primario} shrink-0 text-xs py-2 px-3.5`}
            >
              {descargandoContrato && <Girador />}
              {descargandoContrato ? "Generando…" : "Descargar contrato para firma"}
            </button>
          </div>

          <div className="mt-4 border-t border-kaizen-100 pt-3">
            <CajaDocumentos
              tipo={tipo}
              expId={expId}
              puedeCargar={!bloqueado}
              aceptar=".pdf"
              titulo="Carga del contrato firmado (PDF)"
              descripcion="Adjunte el contrato de crédito debidamente firmado por el cliente en formato PDF. Los recaudos generales del crédito son aportados por el área Comercial."
              variante="integrada"
              ocultarReferencia
            />
          </div>
        </div>

        {/* ── 2. Campos de la Evaluación Legal ─────────────────────── */}
        {tipo === "corp" ? (
          <>
            <Bloque titulo="Garantía y Cobertura">
              <CampoTexto
                rotulo="Descripción de la garantía"
                valor={descripcionGarantia}
                alCambiar={setDescripcionGarantia}
                deshabilitado={bloqueado}
                ayuda="Bien o derecho ofrecido en garantía."
              />
              <CampoNumero
                rotulo="Valor de la garantía"
                valor={valorGarantia}
                alCambiar={recalcularLtvCorp}
                minimo={0}
                deshabilitado={bloqueado}
                ayuda="Al fijarlo se recalcula el LTV."
              />
              <CampoNumero
                rotulo="LTV (%)"
                valor={ltvCorp}
                alCambiar={setLtvCorp}
                minimo={0}
                deshabilitado={bloqueado}
                ayuda={`Crédito de ${montoCredito.toLocaleString("es-VE")} sobre la garantía.`}
              />
              <CampoTexto
                rotulo="Vencimiento de la garantía"
                valor={vencimientoCorp}
                alCambiar={setVencimientoCorp}
                deshabilitado={bloqueado}
                tipo="date"
              />
            </Bloque>

            <Bloque titulo="Custodia y Conclusiones" columnas={1}>
              <CampoCasilla
                rotulo="Documentación en custodia física"
                valor={custodiaCorp}
                alCambiar={setCustodiaCorp}
                deshabilitado={bloqueado}
                ayuda="Los originales están bajo resguardo de la institución."
              />
              <CampoTextoLargo
                rotulo="Observaciones de Legal"
                valor={obsCorp}
                alCambiar={setObsCorp}
                deshabilitado={bloqueado}
                marcador="Situación jurídica de la garantía y del solicitante."
              />
            </Bloque>
          </>
        ) : (
          <>
            <Bloque titulo="Vehículo" columnas={3}>
              <CampoTexto
                rotulo="Marca"
                valor={formAuto.marca}
                alCambiar={(v) => setAuto("marca", v)}
                deshabilitado={bloqueado}
              />
              <CampoTexto
                rotulo="Modelo"
                valor={formAuto.modelo}
                alCambiar={(v) => setAuto("modelo", v)}
                deshabilitado={bloqueado}
              />
              <CampoNumero
                rotulo="Año"
                valor={formAuto.anio}
                alCambiar={(v) => setAuto("anio", v)}
                paso="1"
                minimo={1900}
                deshabilitado={bloqueado}
              />
              <CampoTexto
                rotulo="VIN"
                valor={formAuto.vin}
                alCambiar={(v) => setAuto("vin", v)}
                deshabilitado={bloqueado}
              />
              <CampoTexto
                rotulo="Placa"
                valor={formAuto.vehiculo_placa}
                alCambiar={(v) => setAuto("vehiculo_placa", v)}
                deshabilitado={bloqueado}
              />
              <CampoSeleccion
                rotulo="Condición"
                valor={formAuto.tipo_vehiculo}
                opciones={TIPOS_VEHICULO}
                alCambiar={(v) => setAuto("tipo_vehiculo", v)}
                deshabilitado={bloqueado}
              />
            </Bloque>

            <Bloque titulo="Condiciones de la operación">
              <CampoNumero
                rotulo="Precio del vehículo"
                valor={formAuto.precio_vehiculo}
                alCambiar={(v) => recalcularLtvAuto(v, formAuto.enganche)}
                minimo={0}
                deshabilitado={bloqueado}
              />
              <CampoNumero
                rotulo="Inicial"
                valor={formAuto.enganche}
                alCambiar={(v) => recalcularLtvAuto(formAuto.precio_vehiculo, v)}
                minimo={0}
                deshabilitado={bloqueado}
              />
              <CampoNumero
                rotulo="Plazo (meses)"
                valor={formAuto.plazo_meses}
                alCambiar={(v) => setAuto("plazo_meses", v)}
                paso="1"
                minimo={1}
                deshabilitado={bloqueado}
              />
              <CampoNumero
                rotulo="LTV (%)"
                valor={formAuto.ltv_ratio}
                alCambiar={(v) => setAuto("ltv_ratio", v)}
                minimo={0}
                deshabilitado={bloqueado}
                ayuda="Financiado sobre el precio del vehículo."
              />
            </Bloque>

            <Bloque titulo="Seguro y prenda">
              <CampoTexto
                rotulo="Aseguradora"
                valor={formAuto.seguro_empresa}
                alCambiar={(v) => setAuto("seguro_empresa", v)}
                deshabilitado={bloqueado}
              />
              <CampoTexto
                rotulo="Número de póliza"
                valor={formAuto.seguro_poliza}
                alCambiar={(v) => setAuto("seguro_poliza", v)}
                deshabilitado={bloqueado}
              />
              <CampoTexto
                rotulo="Vigencia de la póliza"
                valor={formAuto.seguro_vigencia}
                alCambiar={(v) => setAuto("seguro_vigencia", v)}
                tipo="date"
                deshabilitado={bloqueado}
              />
              <CampoTexto
                rotulo="Vencimiento del seguro"
                valor={formAuto.fecha_vencimiento_seguro}
                alCambiar={(v) => setAuto("fecha_vencimiento_seguro", v)}
                tipo="date"
                deshabilitado={bloqueado}
              />
              <CampoCasilla
                rotulo="Póliza vigente verificada"
                valor={formAuto.seguro_vehiculo}
                alCambiar={(v) => setAuto("seguro_vehiculo", v)}
                deshabilitado={bloqueado}
              />
              <CampoCasilla
                rotulo="Prenda inscrita"
                valor={formAuto.registro_lien}
                alCambiar={(v) => setAuto("registro_lien", v)}
                deshabilitado={bloqueado}
                ayuda="Gravamen registrado a favor de la institución."
              />
            </Bloque>

            <Bloque titulo="Conclusiones" columnas={1}>
              <CampoTextoLargo
                rotulo="Observaciones de Legal"
                valor={formAuto.obs_leg}
                alCambiar={(v) => setAuto("obs_leg", v)}
                deshabilitado={bloqueado}
                marcador="Situación registral del vehículo y del solicitante."
              />
            </Bloque>
          </>
        )}

        {/* ── 3. Acciones de la Etapa (Footer integrado) ────────────── */}
        {!bloqueado && (
          <div className="border-t border-borde pt-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <button
                type="button"
                className={BOTON.primario}
                disabled={enviando}
                onClick={tipo === "corp" ? enviarCorp : enviarAuto}
              >
                {enviando && <Girador />}
                Registrar firma de Legal
              </button>

              <button
                type="button"
                className={BOTON.neutro}
                disabled={enviando}
                onClick={() => setMostrarSalidas((prev) => !prev)}
              >
                {mostrarSalidas
                  ? "Ocultar opciones de devolución"
                  : "Devolver o denegar solicitud…"}
              </button>
            </div>

            {mostrarSalidas && (
              <div className="rounded-xl border border-borde bg-kaizen-50/40 p-4 space-y-3">
                <div>
                  <h5 className="text-xs font-bold uppercase tracking-wider text-kaizen-900">
                    Devolución o Denegación
                  </h5>
                  <p className="mt-0.5 text-xs text-tinta-suave">
                    Devolver reabre la etapa seleccionada con una tarea nueva; denegar concluye el expediente. Ambas acciones exigen justificación.
                  </p>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <CampoSeleccion
                    rotulo="Etapa destino"
                    valor={etapaDevolucion}
                    opciones={ETAPAS_DEVOLUCION_LEGAL}
                    alCambiar={(v) => setEtapaDevolucion(v as EtapaDevolucion)}
                    ayuda="A quién vuelve el expediente para subsanar."
                  />
                </div>

                <CampoTextoLargo
                  rotulo="Justificación"
                  valor={justificacion}
                  alCambiar={setJustificacion}
                  marcador="Motivo por el cual se devuelve o se deniega la solicitud."
                  filas={3}
                />

                <div className="flex flex-wrap gap-2 pt-1">
                  <button
                    type="button"
                    className={BOTON.neutro}
                    disabled={enviando || !justificacion.trim()}
                    onClick={() =>
                      void onDevolver(etapaDevolucion, justificacion.trim())
                    }
                  >
                    Devolver a {etapaDevolucion}
                  </button>
                  <button
                    type="button"
                    className={BOTON.peligro}
                    disabled={enviando || !justificacion.trim()}
                    onClick={() => void onRechazar(justificacion.trim())}
                  >
                    Denegar solicitud
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
