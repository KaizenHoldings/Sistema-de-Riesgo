"use client";

/**
 * Nueva solicitud de crédito.
 *
 * Los datos de la operación y sus documentos se preparan en la misma pantalla,
 * que es como llega el caso: con los papeles delante. Los archivos no pueden
 * subirse antes —se guardan contra un expediente que todavía no existe—, así que
 * la caja los retiene y la pantalla los envía en cuanto la solicitud queda
 * abierta, sin pedir nada más al usuario.
 *
 * Si el expediente se abre pero alguna carga falla, la solicitud ya está hecha:
 * se avisa y se queda la caja del expediente para reintentarlo, en lugar de
 * dejar creer que se perdió todo.
 */

import Link from "next/link";
import { useMemo, useState, type FormEvent } from "react";

import {
  CajaDocumentos,
  puedeCargarDocumentos,
  puedeVerDocumentos,
} from "@/components/evaluaciones/CajaDocumentos";
import { EncabezadoPagina } from "@/components/layout/MarcoApp";
import { useSesion } from "@/components/providers/ProveedorSesion";
import { Alerta } from "@/components/ui/Alerta";
import { BOTON, CAMPO } from "@/components/ui/Modal";
import { Girador } from "@/components/ui/Skeleton";
import { useAvisos } from "@/components/ui/Toast";
import { useClientes, useCrearSolicitud } from "@/hooks/useClientes";
import { cargarDocumentosOperacion } from "@/hooks/useDocumentosOperacion";
import type { TipoExpediente } from "@/types/api";
import { ApiError } from "@/utils/apiClient";

interface Creada {
  id: number;
  tipo: TipoExpediente;
  cliente: string;
}

export default function NuevaSolicitudPage() {
  const { sesion } = useSesion();
  const { notificar, notificarError } = useAvisos();
  const clientes = useClientes({ pagina: 1, porPagina: 200 });
  const accion = useCrearSolicitud();

  const [tipo, setTipo] = useState<TipoExpediente>("corp");
  const [clienteId, setClienteId] = useState(0);
  const [monto, setMonto] = useState(0);
  const [descripcion, setDescripcion] = useState("");
  const [pendientes, setPendientes] = useState<File[]>([]);
  const [subiendo, setSubiendo] = useState(false);
  const [creada, setCreada] = useState<Creada | null>(null);

  const cliente = useMemo(
    () => clientes.datos?.find((c) => c.id === clienteId),
    [clientes.datos, clienteId],
  );

  const puedeCargar = puedeCargarDocumentos(sesion?.rol);
  const puedeVer = puedeVerDocumentos(sesion?.rol);

  const guardar = async (evento: FormEvent) => {
    evento.preventDefault();
    const creado = await accion.ejecutar({
      tipo,
      cliente_id: clienteId,
      cliente: cliente?.nombre ?? "",
      documento: cliente?.cedula_rif ?? "",
      fecha: new Date().toISOString().slice(0, 10),
      monto,
      descripcion,
    });
    if (!creado?.id) return;

    if (pendientes.length > 0) {
      setSubiendo(true);
      try {
        await cargarDocumentosOperacion(tipo, creado.id, pendientes);
        notificar(
          "exito",
          "Solicitud abierta",
          `Expediente ${creado.id} con ${pendientes.length} ${
            pendientes.length === 1 ? "documento" : "documentos"
          }.`,
        );
        setPendientes([]);
      } catch (fallo) {
        notificarError(
          fallo instanceof ApiError
            ? fallo
            : new ApiError(
                0,
                "La solicitud se abrió, pero no se pudieron cargar los documentos.",
              ),
        );
      } finally {
        setSubiendo(false);
      }
    }

    setCreada({ id: creado.id, tipo, cliente: cliente?.nombre ?? "" });
  };

  if (creada) {
    return (
      <>
        <EncabezadoPagina
          icono="+"
          miga="Originación / Nueva"
          titulo={`Solicitud ${creada.id} abierta`}
          bajada={`${creada.cliente} · el expediente entró al circuito por Cumplimiento.`}
          acciones={
            <Link
              href={`/evaluations/${creada.tipo}/${creada.id}`}
              className={BOTON.primario}
            >
              Ir al expediente
            </Link>
          }
        />

        <p className="mb-6 rounded-lg border border-verde-trazo/30 bg-verde-fondo px-4 py-3 text-sm text-verde-trazo">
          La solicitud quedó registrada. Puede seguir adjuntando documentos aquí:
          Legal los descarga desde el expediente para inspeccionarlos.
        </p>

        {puedeVer && (
          <CajaDocumentos
            tipo={creada.tipo}
            expId={creada.id}
            puedeCargar={puedeCargar}
          />
        )}

        <button
          type="button"
          className={BOTON.neutro}
          onClick={() => {
            setCreada(null);
            setClienteId(0);
            setMonto(0);
            setDescripcion("");
            setPendientes([]);
          }}
        >
          Abrir otra solicitud
        </button>
      </>
    );
  }

  const enviando = accion.enviando || subiendo;

  return (
    <>
      <EncabezadoPagina
        icono="+"
        miga="Originación / Nueva"
        titulo="Nueva solicitud"
        bajada="Abra un expediente en la etapa de Cumplimiento y adjunte su documentación."
      />

      <form onSubmit={guardar} className="max-w-5xl">
        <div className="rounded-xl border border-borde bg-white p-6 shadow-sm">
          <div className="grid gap-5 md:grid-cols-2">
            <label>
              <span className="text-sm font-semibold text-kaizen-900">
                Producto
              </span>
              <select
                className={`mt-1 ${CAMPO}`}
                value={tipo}
                onChange={(evento) =>
                  setTipo(evento.target.value as TipoExpediente)
                }
              >
                <option value="corp">Corporativo</option>
                <option value="auto">Automotriz</option>
              </select>
            </label>

            <label>
              <span className="text-sm font-semibold text-kaizen-900">
                Cliente
              </span>
              <select
                required
                className={`mt-1 ${CAMPO}`}
                value={clienteId || ""}
                onChange={(evento) => setClienteId(Number(evento.target.value))}
              >
                <option value="">Seleccione…</option>
                {clientes.datos?.map((c) => (
                  <option key={c.id} value={c.id ?? ""}>
                    {c.nombre} · {c.cedula_rif}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <span className="text-sm font-semibold text-kaizen-900">
                Monto solicitado
              </span>
              <input
                required
                min="0.01"
                step="0.01"
                type="number"
                className={`mt-1 ${CAMPO}`}
                value={monto || ""}
                onChange={(evento) => setMonto(Number(evento.target.value))}
              />
            </label>

            <label className="md:col-span-2">
              <span className="text-sm font-semibold text-kaizen-900">
                Destino y descripción
              </span>
              <textarea
                required
                rows={4}
                className={`mt-1 ${CAMPO}`}
                value={descripcion}
                onChange={(evento) => setDescripcion(evento.target.value)}
              />
            </label>
          </div>
        </div>

        {puedeVer && (
          <div className="mt-6">
            <CajaDocumentos
              tipo={tipo}
              expId={null}
              puedeCargar={puedeCargar}
              pendientes={pendientes}
              alCambiarPendientes={setPendientes}
            />
          </div>
        )}

        {(accion.error || clientes.error) && (
          <div className="mb-5">
            <Alerta error={accion.error ?? clientes.error!} />
          </div>
        )}

        <button
          type="submit"
          className={BOTON.primario}
          disabled={enviando || !cliente}
        >
          {enviando && <Girador />}
          {subiendo
            ? "Cargando documentos…"
            : accion.enviando
              ? "Abriendo…"
              : "Abrir solicitud"}
        </button>

        {pendientes.length > 0 && (
          <p className="mt-3 text-xs text-tinta-suave">
            {pendientes.length}{" "}
            {pendientes.length === 1
              ? "documento se cargará"
              : "documentos se cargarán"}{" "}
            al abrir la solicitud.
          </p>
        )}
      </form>
    </>
  );
}
