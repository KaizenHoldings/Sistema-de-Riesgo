"use client";

/**
 * Tablero institucional.
 *
 * Ocho cifras que responden a una sola pregunta: en qué estado está la cartera
 * de solicitudes. Cuántos clientes hay y cuántos créditos, cómo se reparten
 * entre las dos líneas, cuántos esperan al Comité y dónde se están parando.
 *
 * Todas salen de una única lectura agregada en el backend, así que o están las
 * ocho o no está ninguna: no hay tarjetas cargando a distinto ritmo ni mezcla de
 * cifras de momentos distintos.
 */

import { EncabezadoPagina } from "@/components/layout/MarcoApp";
import { Alerta } from "@/components/ui/Alerta";
import { SkeletonMetricas } from "@/components/ui/Skeleton";
import { TarjetaMetrica } from "@/components/ui/TarjetaMetrica";
import { useMetricasTablero } from "@/hooks/useTablero";
import type { MetricasTablero } from "@/types/api";
import type { Semaforo } from "@/utils/estados";
import { formatearEntero } from "@/utils/format";

interface Indicador {
  rotulo: string;
  valor: (m: MetricasTablero) => number;
  nota: string;
  acento?: Semaforo;
  icono?: string;
}

const INDICADORES: Indicador[] = [
  {
    rotulo: "Clientes",
    valor: (m) => m.clientes,
    nota: "Registrados en el padrón",
    icono: "▣",
  },
  {
    rotulo: "Créditos totales",
    valor: (m) => m.creditos_total,
    nota: "Solicitudes activas de las dos líneas",
    icono: "◈",
  },
  {
    rotulo: "Créditos corporativos",
    valor: (m) => m.creditos_corporativos,
    nota: "Línea de empresas",
    icono: "◆",
  },
  {
    rotulo: "Créditos automotrices",
    valor: (m) => m.creditos_automotrices,
    nota: "Línea de vehículos",
    icono: "◆",
  },
  {
    rotulo: "Listos para Comité",
    valor: (m) => m.listos_comite,
    nota: "Con las tres firmas y sin dictamen",
    acento: "verde",
    icono: "✓",
  },
  {
    rotulo: "Frenados en Cumplimiento",
    valor: (m) => m.frenados_cumplimiento,
    nota: "Rechazados o devueltos antes de certificar",
    acento: "rojo",
  },
  {
    rotulo: "Frenados en Riesgo",
    valor: (m) => m.frenados_riesgo,
    nota: "Parados en la etapa de Crédito",
    acento: "ambar",
  },
  {
    rotulo: "Frenados en Legal",
    valor: (m) => m.frenados_legal,
    nota: "Parados en la etapa de Legal",
    acento: "ambar",
  },
];

export default function TableroPage() {
  const { datos, cargando, error, recargar } = useMetricasTablero();

  return (
    <>
      <EncabezadoPagina
        icono="◆"
        miga="Inicio / Tablero"
        titulo="Tablero institucional"
        bajada="Estado de la cartera de solicitudes: volumen, reparto por línea y dónde se detiene el circuito."
        acciones={
          <button type="button" onClick={recargar}>
            <span className="rounded-lg border border-borde bg-white px-4 py-2 text-sm font-semibold text-tinta transition hover:border-kaizen-600 hover:text-kaizen-600">
              Actualizar
            </span>
          </button>
        }
      />

      {cargando && !datos ? (
        <SkeletonMetricas tarjetas={8} />
      ) : error ? (
        <Alerta error={error} alReintentar={recargar} />
      ) : datos ? (
        <section
          className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4"
          aria-label="Métricas del tablero"
        >
          {INDICADORES.map((indicador) => (
            <TarjetaMetrica
              key={indicador.rotulo}
              rotulo={indicador.rotulo}
              valor={formatearEntero(indicador.valor(datos))}
              nota={indicador.nota}
              acento={indicador.acento}
              icono={indicador.icono}
            />
          ))}
        </section>
      ) : null}

      <p className="mt-6 text-xs text-tinta-suave">
        Las tres últimas cifras se deducen del estado en que quedó cada
        expediente: el circuito registra cómo se detuvo, no quién lo detuvo. Un
        rechazo del Comité con las tres firmas puestas no se atribuye a ninguna
        etapa, así que las tres no tienen por qué sumar el total de paradas.
      </p>
    </>
  );
}
