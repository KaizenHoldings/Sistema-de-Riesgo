"use client";

/**
 * Cartera de clientes.
 *
 * Directorio ligero: la tabla trae solo lo que se lee de un vistazo —identidad,
 * estado KYC y contacto— y el detalle queda para la ficha. La búsqueda y la
 * paginación se resuelven en el backend, así que escribir en el filtro dispara
 * una consulta nueva en lugar de recortar una lista ya descargada.
 */

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { EncabezadoPagina } from "@/components/layout/MarcoApp";
import { Alerta, SinResultados } from "@/components/ui/Alerta";
import { Paginador } from "@/components/ui/Paginador";
import { Insignia } from "@/components/ui/Semaforo";
import { Girador, SkeletonMetricas, SkeletonTabla } from "@/components/ui/Skeleton";
import { Tabla, type Columna } from "@/components/ui/Tabla";
import { TarjetaMetrica } from "@/components/ui/TarjetaMetrica";
import { useAvisos } from "@/components/ui/Toast";
import { useClientes } from "@/hooks/useClientes";
import type { Cliente } from "@/types/api";
import { semaforoKyc } from "@/utils/estados";
import { formatearEntero, formatearFecha, textoOGuion } from "@/utils/format";

const POR_PAGINA = 10;

const ESTADOS_KYC = [
  "Prospecto",
  "KYC Pendiente",
  "KYC Aprobado",
  "KYC Rechazado",
] as const;

/** Espera a que el usuario deje de teclear antes de consultar al backend. */
function useValorDemorado<T>(valor: T, milisegundos = 350): T {
  const [demorado, setDemorado] = useState(valor);

  useEffect(() => {
    const temporizador = window.setTimeout(() => setDemorado(valor), milisegundos);
    return () => window.clearTimeout(temporizador);
  }, [valor, milisegundos]);

  return demorado;
}

export default function ClientesPage() {
  const [pagina, setPagina] = useState(1);
  const [busqueda, setBusqueda] = useState("");
  const [estadoKyc, setEstadoKyc] = useState("");

  const busquedaDemorada = useValorDemorado(busqueda);

  // Cualquier cambio de filtro invalida la página en la que se estaba, así que
  // el reinicio se hace en el propio manejador y no reaccionando al cambio.
  const cambiarBusqueda = (valor: string) => {
    setBusqueda(valor);
    setPagina(1);
  };

  const cambiarEstadoKyc = (valor: string) => {
    setEstadoKyc(valor);
    setPagina(1);
  };

  const { datos, cargando, error, recargar } = useClientes({
    pagina,
    porPagina: POR_PAGINA,
    nombre: busquedaDemorada.trim() || undefined,
    kycStatus: estadoKyc || undefined,
  });

  const { notificarError } = useAvisos();
  useEffect(() => {
    if (error?.esDeRed) notificarError(error);
  }, [error, notificarError]);

  const clientes = useMemo(() => datos ?? [], [datos]);

  const resumen = useMemo(() => {
    const cuenta = (predicado: (c: Cliente) => boolean) =>
      clientes.filter(predicado).length;
    const estado = (c: Cliente) => (c.kyc_status ?? "").toLowerCase();
    return {
      total: clientes.length,
      aprobados: cuenta((c) => estado(c).includes("aprobado")),
      pendientes: cuenta((c) => estado(c).includes("pendiente")),
      juridicos: cuenta((c) => (c.tipo ?? "").toLowerCase().startsWith("jur")),
    };
  }, [clientes]);

  const columnas: Array<Columna<Cliente>> = [
    {
      clave: "accion",
      encabezado: "",
      celda: (cliente) =>
        cliente.id === null ? null : (
          <Link
            href={`/clients/${cliente.id}`}
            className="inline-flex rounded-lg bg-kaizen-800 px-3 py-1.5 text-xs font-semibold whitespace-nowrap text-white transition hover:bg-kaizen-900"
          >
            Ver ficha
          </Link>
        ),
    },
    {
      clave: "id",
      encabezado: "Código",
      alineacion: "derecha",
      celda: (cliente) => (
        <span className="font-mono text-xs text-tinta-suave tabular-nums">
          {cliente.id ?? "—"}
        </span>
      ),
    },
    {
      clave: "nombre",
      encabezado: "Cliente",
      anchoMinimo: "16rem",
      celda: (cliente) => (
        <div className="min-w-0">
          <p className="truncate font-semibold text-kaizen-900">
            {textoOGuion(cliente.nombre)}
          </p>
          <p className="truncate text-xs text-tinta-suave">
            {textoOGuion(cliente.cedula_rif)}
          </p>
        </div>
      ),
    },
    {
      clave: "tipo",
      encabezado: "Tipo",
      celda: (cliente) => (
        <span className="text-sm text-tinta-suave">{textoOGuion(cliente.tipo)}</span>
      ),
    },
    {
      clave: "kyc",
      encabezado: "Estado KYC",
      anchoMinimo: "11rem",
      celda: (cliente) => (
        <Insignia
          tono={semaforoKyc(cliente.kyc_status)}
          texto={textoOGuion(cliente.kyc_status)}
        />
      ),
    },
    {
      clave: "actividad",
      encabezado: "Actividad económica",
      anchoMinimo: "14rem",
      celda: (cliente) => (
        <span className="block max-w-xs truncate text-sm text-tinta-suave">
          {textoOGuion(cliente.actividad_economica)}
        </span>
      ),
    },
    {
      clave: "contacto",
      encabezado: "Contacto",
      anchoMinimo: "13rem",
      celda: (cliente) => (
        <div className="min-w-0 text-sm">
          <p className="truncate text-tinta">{textoOGuion(cliente.telefono)}</p>
          <p className="truncate text-xs text-tinta-suave">
            {textoOGuion(cliente.email)}
          </p>
        </div>
      ),
    },
    {
      clave: "alta",
      encabezado: "Alta",
      alineacion: "derecha",
      celda: (cliente) => (
        <span className="text-sm whitespace-nowrap text-tinta-suave tabular-nums">
          {formatearFecha(cliente.fecha_registro)}
        </span>
      ),
    },
  ];

  const controlBase =
    "rounded-lg border border-borde bg-white px-3 py-2 text-sm text-tinta " +
    "outline-none transition focus:border-kaizen-600 focus:ring-2 focus:ring-kaizen-600/20";

  return (
    <>
      <EncabezadoPagina
        icono="▣"
        miga="Inicio / Clientes"
        titulo="Cartera de clientes"
        bajada="Padrón único de clientes y situación de su expediente KYC."
        acciones={cargando && clientes.length > 0 ? <Girador /> : undefined}
      />

      <section className="mb-8">
        {cargando && clientes.length === 0 ? (
          <SkeletonMetricas />
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <TarjetaMetrica
              rotulo="En esta página"
              valor={formatearEntero(resumen.total)}
              nota={`Página ${pagina}, hasta ${POR_PAGINA} por página`}
            />
            <TarjetaMetrica
              rotulo="KYC aprobado"
              valor={formatearEntero(resumen.aprobados)}
              nota="Habilitados para originar"
              acento="verde"
            />
            <TarjetaMetrica
              rotulo="KYC pendiente"
              valor={formatearEntero(resumen.pendientes)}
              nota="A la espera de Cumplimiento"
              acento={resumen.pendientes > 0 ? "ambar" : "neutro"}
            />
            <TarjetaMetrica
              rotulo="Personas jurídicas"
              valor={formatearEntero(resumen.juridicos)}
              nota="El resto son personas naturales"
            />
          </div>
        )}
      </section>

      <section className="mb-5 flex flex-wrap items-end gap-4">
        <label className="flex min-w-64 flex-1 flex-col gap-1.5">
          <span className="text-xs font-semibold tracking-wide text-tinta-suave uppercase">
            Buscar por nombre o documento
          </span>
          <input
            type="search"
            value={busqueda}
            onChange={(evento) => cambiarBusqueda(evento.target.value)}
            placeholder="Nombre, cédula o RIF"
            className={controlBase}
          />
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="text-xs font-semibold tracking-wide text-tinta-suave uppercase">
            Estado KYC
          </span>
          <select
            value={estadoKyc}
            onChange={(evento) => cambiarEstadoKyc(evento.target.value)}
            className={controlBase}
          >
            <option value="">Todos</option>
            {ESTADOS_KYC.map((estado) => (
              <option key={estado} value={estado}>
                {estado}
              </option>
            ))}
          </select>
        </label>

        <button
          type="button"
          onClick={recargar}
          className="rounded-lg bg-kaizen-800 px-4 py-2 text-sm font-semibold text-white transition hover:bg-kaizen-900"
        >
          Actualizar
        </button>
      </section>

      <section>
        {cargando && clientes.length === 0 ? (
          <SkeletonTabla columnas={8} filas={8} />
        ) : error ? (
          <Alerta error={error} alReintentar={recargar} />
        ) : clientes.length === 0 ? (
          <SinResultados mensaje="Ningún cliente coincide con los filtros aplicados." />
        ) : (
          <Tabla
            columnas={columnas}
            filas={clientes}
            claveFila={(cliente, indice) => cliente.id ?? `fila-${indice}`}
            pie={
              <Paginador
                pagina={pagina}
                porPagina={POR_PAGINA}
                recibidas={clientes.length}
                alCambiar={setPagina}
              />
            }
          />
        )}
      </section>
    </>
  );
}
