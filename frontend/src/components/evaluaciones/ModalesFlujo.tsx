"use client";

/**
 * Modales de las transiciones del circuito.
 *
 * Todos comparten la misma mecánica: recogen lo que el backend exige, lo envían
 * y, si la guarda lo rechaza, muestran el motivo dentro del propio modal en
 * lugar de cerrarlo. Cerrar tras un 409 obligaría al usuario a reabrirlo y
 * volver a escribir la justificación.
 *
 * Ninguno decide si la transición es legítima: eso es de
 * `services/workflow_service`, y aquí solo se traduce su respuesta.
 */

import { useState, type ReactNode } from "react";

import { useAccion } from "@/hooks/useAccion";
import { Alerta } from "@/components/ui/Alerta";
import { BOTON, CAMPO, Modal } from "@/components/ui/Modal";
import { Girador } from "@/components/ui/Skeleton";
import type { ResultadoTransicion } from "@/types/api";

interface BaseProps {
  abierto: boolean;
  alCerrar: () => void;
  /** Se invoca solo cuando la transición se completó en el backend. */
  alCompletar: (resultado: ResultadoTransicion) => void;
}

/** Confirmación sin campos: certificar Cumplimiento o rechazar en Comité. */
export function ModalConfirmacion({
  abierto,
  titulo,
  descripcion,
  cuerpo,
  textoAccion,
  estilo = "primario",
  accion,
  alCerrar,
  alCompletar,
}: BaseProps & {
  titulo: string;
  descripcion?: string;
  cuerpo?: ReactNode;
  textoAccion: string;
  estilo?: keyof typeof BOTON;
  accion: () => Promise<ResultadoTransicion>;
}) {
  const { ejecutar, enviando, error, limpiarError } = useAccion(accion);

  const cerrar = () => {
    limpiarError();
    alCerrar();
  };

  const confirmar = async () => {
    const resultado = await ejecutar();
    if (resultado) {
      alCompletar(resultado);
      cerrar();
    }
  };

  return (
    <Modal
      abierto={abierto}
      titulo={titulo}
      descripcion={descripcion}
      alCerrar={cerrar}
      pie={
        <>
          <button type="button" className={BOTON.neutro} onClick={cerrar}>
            Cancelar
          </button>
          <button
            type="button"
            className={BOTON[estilo]}
            disabled={enviando}
            onClick={confirmar}
          >
            {enviando && <Girador />}
            {textoAccion}
          </button>
        </>
      }
    >
      {cuerpo}
      {error && (
        <div className={cuerpo ? "mt-4" : ""}>
          <Alerta error={error} />
        </div>
      )}
    </Modal>
  );
}

/** Transición con justificación obligatoria: observar, rechazar o devolver. */
export function ModalJustificacion({
  abierto,
  titulo,
  descripcion,
  etiqueta,
  marcador,
  textoAccion,
  estilo = "aviso",
  etapas,
  accion,
  alCerrar,
  alCompletar,
}: BaseProps & {
  titulo: string;
  descripcion?: string;
  etiqueta: string;
  marcador?: string;
  textoAccion: string;
  estilo?: keyof typeof BOTON;
  /** Si se indican, el modal pide además a qué etapa se devuelve. */
  etapas?: readonly string[];
  accion: (texto: string, etapa: string) => Promise<ResultadoTransicion>;
}) {
  const [texto, setTexto] = useState("");
  const [etapa, setEtapa] = useState(etapas?.[0] ?? "");
  const { ejecutar, enviando, error, limpiarError } = useAccion(accion);

  const cerrar = () => {
    limpiarError();
    setTexto("");
    alCerrar();
  };

  const confirmar = async () => {
    const resultado = await ejecutar(texto, etapa);
    if (resultado) {
      alCompletar(resultado);
      cerrar();
    }
  };

  const vacio = texto.trim().length === 0;

  return (
    <Modal
      abierto={abierto}
      titulo={titulo}
      descripcion={descripcion}
      alCerrar={cerrar}
      pie={
        <>
          <button type="button" className={BOTON.neutro} onClick={cerrar}>
            Cancelar
          </button>
          <button
            type="button"
            className={BOTON[estilo]}
            disabled={enviando || vacio}
            onClick={confirmar}
          >
            {enviando && <Girador />}
            {textoAccion}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        {etapas && (
          <label className="block">
            <span className="text-xs font-semibold tracking-wide text-tinta-suave uppercase">
              Etapa destino
            </span>
            <select
              value={etapa}
              onChange={(evento) => setEtapa(evento.target.value)}
              className={`mt-1.5 ${CAMPO}`}
            >
              {etapas.map((e) => (
                <option key={e} value={e}>
                  {e}
                </option>
              ))}
            </select>
          </label>
        )}

        <label className="block">
          <span className="text-xs font-semibold tracking-wide text-tinta-suave uppercase">
            {etiqueta}
          </span>
          <textarea
            rows={4}
            value={texto}
            placeholder={marcador}
            onChange={(evento) => setTexto(evento.target.value)}
            className={`mt-1.5 resize-y ${CAMPO}`}
          />
          <span className="mt-1 block text-xs text-tinta-suave">
            Queda registrada en la traza del expediente; es obligatoria.
          </span>
        </label>

        {error && <Alerta error={error} />}
      </div>
    </Modal>
  );
}

/** Aprobación del Comité: exige tasa y plazo además de las tres firmas. */
export function ModalAprobacion({
  abierto,
  tasaSugerida,
  plazoSugerido,
  accion,
  alCerrar,
  alCompletar,
}: BaseProps & {
  tasaSugerida: number;
  plazoSugerido: number;
  accion: (tasa: number, plazo: number) => Promise<ResultadoTransicion>;
}) {
  const [tasa, setTasa] = useState(String(tasaSugerida || 0));
  const [plazo, setPlazo] = useState(String(plazoSugerido || 36));
  const { ejecutar, enviando, error, limpiarError } = useAccion(accion);

  const cerrar = () => {
    limpiarError();
    alCerrar();
  };

  const confirmar = async () => {
    const resultado = await ejecutar(Number(tasa) || 0, Number(plazo) || 0);
    if (resultado) {
      alCompletar(resultado);
      cerrar();
    }
  };

  const plazoValido = Number(plazo) > 0;

  return (
    <Modal
      abierto={abierto}
      titulo="Aprobar expediente"
      descripcion="Al aprobar se genera el plan de amortización francés con estas condiciones."
      alCerrar={cerrar}
      pie={
        <>
          <button type="button" className={BOTON.neutro} onClick={cerrar}>
            Cancelar
          </button>
          <button
            type="button"
            className={BOTON.primario}
            disabled={enviando || !plazoValido}
            onClick={confirmar}
          >
            {enviando && <Girador />}
            Aprobar y generar el plan
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <label className="block">
            <span className="text-xs font-semibold tracking-wide text-tinta-suave uppercase">
              Tasa aprobada (%)
            </span>
            <input
              type="number"
              step="0.01"
              min="0"
              value={tasa}
              onChange={(evento) => setTasa(evento.target.value)}
              className={`mt-1.5 ${CAMPO}`}
            />
          </label>
          <label className="block">
            <span className="text-xs font-semibold tracking-wide text-tinta-suave uppercase">
              Plazo (meses)
            </span>
            <input
              type="number"
              step="1"
              min="1"
              value={plazo}
              onChange={(evento) => setPlazo(evento.target.value)}
              className={`mt-1.5 ${CAMPO}`}
            />
          </label>
        </div>

        <p className="rounded-lg bg-kaizen-100/50 px-4 py-3 text-sm text-tinta-suave">
          La tasa que propuso Riesgo fue {tasaSugerida.toFixed(2)}%. El backend
          rechaza la aprobación si falta alguna de las tres firmas del circuito.
        </p>

        {error && <Alerta error={error} />}
      </div>
    </Modal>
  );
}
