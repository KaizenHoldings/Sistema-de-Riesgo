"use client";

/**
 * Status de créditos.
 *
 * Seguimiento, no operación: el área comercial presenta las solicitudes y desde
 * aquí ve en qué punto está cada una, incluidas las que avanzan sin pedirle
 * nada. Por eso pide la cartera completa —`view_mode=all`— mientras que su
 * bandeja de evaluaciones se queda con lo que le devuelven para subsanar.
 *
 * La tabla no ofrece ninguna acción de circuito: quien no firma no necesita un
 * botón que le lleve a un formulario que el backend le va a rechazar. El enlace
 * de cada fila abre la ficha, que es donde puede leer el motivo de una parada y
 * pedir la reevaluación.
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
import { useSesion } from "@/components/providers/ProveedorSesion";
import { Alerta, SinResultados } from "@/components/ui/Alerta";
import { Paginador } from "@/components/ui/Paginador";
import { Girador, SkeletonTabla } from "@/components/ui/Skeleton";
import { Tabla } from "@/components/ui/Tabla";
import { useAvisos } from "@/components/ui/Toast";
import {
  useExpedientesAutomotrices,
  useExpedientesCorporativos,
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
const ROLES_SEGUIMIENTO = ["Comercial", "Superadmin"];

export default function StatusCreditosPage() {
  const { sesion } = useSesion();
  const [pagina, setPagina] = useState(1);
  const [categoria, setCategoria] = useState<Categoria>("todos");
  const [etapa, setEtapa] = useState<EtapaFiltro>("todas");
  const [dictamen, setDictamen] = useState<DictamenFiltro>("todos");
  const [busqueda, setBusqueda] = useState("");

  // La cartera entera: es lo que distingue esta pantalla de la bandeja.
  // El lote no depende de la pagina: la paginacion es local.
  const filtros = { pagina: 1, porPagina: LOTE, vista: "all" as const };
  const corporativos = useExpedientesCorporativos(filtros);
  const automotrices = useExpedientesAutomotrices(filtros);

  const { notificarError } = useAvisos();
  const fallo = corporativos.error ?? automotrices.error;
  useEffect(() => {
    if (fallo?.esDeRed) notificarError(fallo);
  }, [fallo, notificarError]);

  const filas = useMemo<FilaExpediente[]>(
    () => [
      ...(categoria === "auto"
        ? []
        : (corporativos.datos ?? []).map((exp) => ({ ...exp, linea: "corp" as const }))),
      ...(categoria === "corp"
        ? []
        : (automotrices.datos ?? []).map((exp) => ({ ...exp, linea: "auto" as const }))),
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
    () => columnasExpedientes("ficha", sesion?.rol),
    [sesion?.rol],
  );

  const cargando =
    (categoria !== "auto" && corporativos.cargando) ||
    (categoria !== "corp" && automotrices.cargando);

  const recargar = () => {
    corporativos.recargar();
    automotrices.recargar();
  };

  if (!sesion || !ROLES_SEGUIMIENTO.includes(sesion.rol)) {
    return (
      <>
        <EncabezadoPagina
          icono="≡"
          miga="Gestión / Seguimiento"
          titulo="Acceso denegado"
          bajada="El seguimiento de solicitudes corresponde al área comercial."
        />
        <SinResultados mensaje="Acceso denegado: su rol no tiene acceso al status de créditos." />
      </>
    );
  }

  return (
    <>
      <EncabezadoPagina
        icono="≡"
        miga="Gestión / Seguimiento"
        titulo="Status de créditos"
        bajada="Todas las solicitudes presentadas, con la etapa y el dictamen en que se encuentran."
        acciones={cargando && filas.length > 0 ? <Girador /> : undefined}
      />

      <FiltrosExpedientes
        categoria={categoria}
        etapa={etapa}
        dictamen={dictamen}
        alCambiarCategoria={(valor) => {
          setCategoria(valor);
          setPagina(1);
        }}
        alCambiarEtapa={(valor) => {
          setEtapa(valor);
          setPagina(1);
        }}
        alCambiarDictamen={(valor) => {
          setDictamen(valor);
          setPagina(1);
        }}
        busqueda={busqueda}
        alCambiarBusqueda={(valor) => {
          setBusqueda(valor);
          setPagina(1);
        }}
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
                ? "Ninguna solicitud coincide con los filtros seleccionados."
                : "Todavía no hay solicitudes presentadas."
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
