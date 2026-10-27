"use client";

/**
 * Bandeja de evaluaciones.
 *
 * Qué expedientes entran en cada pestaña no se decide aquí: el backend lo
 * resuelve con el rol del token, de modo que «pendientes» significa lo que
 * espera la firma de quien mira —y, para quien no firma, lo que se le ha
 * devuelto—. La pantalla solo dice qué pestaña está activa.
 *
 * Los tres desplegables recortan lo ya recibido, sin volver a consultar: sirven
 * para buscar dentro de la bandeja, no para cambiar su alcance.
 */

import { useEffect, useMemo, useState } from "react";

import {
  FiltrosExpedientes,
  coincideDictamen,
  coincideEtapa,
  coincideTexto,
  type Categoria,
  type DictamenFiltro,
  type EtapaFiltro,
  type FilaExpediente,
} from "@/components/evaluaciones/FiltrosExpedientes";
import { columnasExpedientes } from "@/components/evaluaciones/columnasExpedientes";
import { EncabezadoPagina } from "@/components/layout/MarcoApp";
import { Alerta, SinResultados } from "@/components/ui/Alerta";
import { Paginador } from "@/components/ui/Paginador";
import { Girador, SkeletonTabla } from "@/components/ui/Skeleton";
import { Tabla } from "@/components/ui/Tabla";
import { useAvisos } from "@/components/ui/Toast";
import { useSesion } from "@/components/providers/ProveedorSesion";
import {
  useExpedientesAutomotrices,
  useExpedientesCorporativos,
  type VistaExpedientes,
} from "@/hooks/useExpedientes";

/** Filas que se pintan por pagina, ya mezcladas las dos lineas. */
const POR_PAGINA = 10;

/**
 * Tamano del lote que se pide al backend.
 *
 * Las dos lineas de producto se consultan por separado y se mezclan aqui, asi
 * que pedir diez de cada una daria paginas de hasta veinte filas y saltos al
 * cambiar de pagina. Se trae un lote amplio —el maximo que admite la ruta— y la
 * pantalla pagina sobre lo ya filtrado, que ademas hace que los filtros y la
 * busqueda actuen sobre todo el conjunto y no solo sobre la pagina visible.
 */
const LOTE = 200;

const VISTAS: Array<[VistaExpedientes, string]> = [
  ["pending", "Evaluaciones pendientes"],
  ["history", "Histórico de aprobación"],
];

export default function EvaluacionesPage() {
  const [vista, setVista] = useState<VistaExpedientes>("pending");
  const [pagina, setPagina] = useState(1);
  const [categoria, setCategoria] = useState<Categoria>("todos");
  const [etapa, setEtapa] = useState<EtapaFiltro>("todas");
  const [dictamen, setDictamen] = useState<DictamenFiltro>("todos");
  const [busqueda, setBusqueda] = useState("");

  // El lote no depende de la pagina: la paginacion es local.
  const filtros = { pagina: 1, porPagina: LOTE, vista };
  const corporativos = useExpedientesCorporativos(filtros);
  const automotrices = useExpedientesAutomotrices(filtros);

  const { sesion } = useSesion();
  const { notificarError } = useAvisos();
  const fallo = corporativos.error ?? automotrices.error;
  useEffect(() => {
    if (fallo?.esDeRed) notificarError(fallo);
  }, [fallo, notificarError]);

  // Las dos consultas se declaran siempre —los hooks no admiten condicionales—
  // y la categoría decide cuál de las dos entra en la tabla.
  const filas = useMemo<FilaExpediente[]>(
    () => [
      ...(categoria === "auto"
        ? []
        : (corporativos.datos ?? []).reverse().map((exp) => ({ ...exp, linea: "corp" as const }))),
      ...(categoria === "corp"
        ? []
        : (automotrices.datos ?? []).reverse().map((exp) => ({ ...exp, linea: "auto" as const }))),
    ],
    [categoria, corporativos.datos, automotrices.datos],
  );

  // Los filtros se aplican en cascada: primero los desplegables, que recortan
  // por criterios del circuito, y sobre lo que queda la busqueda por texto.
  const filtradas = useMemo(() => {
    const termino = busqueda.trim().toLowerCase();
    return filas
      .filter((fila) => coincideEtapa(fila, etapa) && coincideDictamen(fila, dictamen))
      .filter((fila) => coincideTexto(fila, termino));
  }, [filas, etapa, dictamen, busqueda]);

  // Pagina sobre lo filtrado: diez filas, vengan de una linea o de las dos.
  const paginadas = useMemo(
    () => filtradas.slice((pagina - 1) * POR_PAGINA, pagina * POR_PAGINA),
    [filtradas, pagina],
  );

  const columnas = useMemo(
    () => columnasExpedientes("evaluar", sesion?.rol),
    [sesion?.rol],
  );

  const cargando =
    (categoria !== "auto" && corporativos.cargando) ||
    (categoria !== "corp" && automotrices.cargando);

  const recargar = () => {
    corporativos.recargar();
    automotrices.recargar();
  };

  const cambiar = (aplicar: () => void) => {
    aplicar();
    setPagina(1);
  };

  return (
    <>
      <EncabezadoPagina
        icono="◈"
        miga="Inicio / Evaluaciones"
        titulo="Comité de crédito"
        bajada="Circuito de evaluación de las dos líneas de producto, de Cumplimiento a dictamen."
        acciones={cargando && filas.length > 0 ? <Girador /> : undefined}
      />

      <div
        className="mb-6 inline-flex flex-wrap gap-1 rounded-lg bg-lienzo p-1"
        role="tablist"
        aria-label="Estado de las evaluaciones"
      >
        {VISTAS.map(([valor, etiqueta]) => (
          <button
            key={valor}
            type="button"
            role="tab"
            aria-selected={vista === valor}
            onClick={() => cambiar(() => setVista(valor))}
            className={`rounded-md px-4 py-2 text-sm font-semibold transition ${
              vista === valor
                ? "bg-white text-kaizen-900 shadow-sm"
                : "text-tinta-suave hover:text-kaizen-900"
            }`}
          >
            {etiqueta}
          </button>
        ))}
      </div>

      <FiltrosExpedientes
        categoria={categoria}
        etapa={etapa}
        dictamen={dictamen}
        alCambiarCategoria={(valor) => cambiar(() => setCategoria(valor))}
        alCambiarEtapa={(valor) => cambiar(() => setEtapa(valor))}
        alCambiarDictamen={(valor) => cambiar(() => setDictamen(valor))}
        busqueda={busqueda}
        alCambiarBusqueda={(valor) => cambiar(() => setBusqueda(valor))}
        acciones={
          <button type="button" onClick={recargar}>
            <span className="rounded-lg border border-borde bg-white px-4 py-2 text-sm font-semibold text-tinta transition hover:border-kaizen-600 hover:text-kaizen-600">
              Actualizar
            </span>
          </button>
        }
      />

      <section>
        {cargando && filas.length === 0 ? (
          <SkeletonTabla columnas={8} filas={7} />
        ) : fallo ? (
          <Alerta error={fallo} alReintentar={recargar} />
        ) : filtradas.length === 0 ? (
          <SinResultados
            mensaje={
              filas.length > 0
                ? "Ningún expediente de la bandeja coincide con los filtros seleccionados."
                : vista === "pending"
                  ? "No hay expedientes esperando su evaluación."
                  : "Todavía no hay expedientes en su histórico."
            }
          />
        ) : (
          <Tabla
            columnas={columnas}
            filas={paginadas}
            claveFila={(exp, i) => `${exp.linea}-${exp.id ?? i}`}
            pie={
              <Paginador
                pagina={pagina}
                porPagina={POR_PAGINA}
                recibidas={paginadas.length}
                alCambiar={setPagina}
              />
            }
          />
        )}
      </section>
    </>
  );
}
