"use client";

/**
 * Gestión Integral de Cartera y Cobranzas.
 *
 * Integra:
 * 1. Operación de Cobro (Caja Mixta multi-moneda, Tasa BCV, Panel Financiero, Cascada Legal).
 * 2. Historial de Cobros y Recibos emitidos.
 * 3. Módulo de Arqueo Diario y Cierre de Caja del Cajero.
 * 4. Antigüedad de la Deuda (Aging) y Plan de Pagos consolidado.
 */

import { useEffect, useMemo, useState } from "react";

import { EncabezadoPagina } from "@/components/layout/MarcoApp";
import { Alerta, SinResultados } from "@/components/ui/Alerta";
import { Paginador } from "@/components/ui/Paginador";
import { BOTON } from "@/components/ui/Modal";
import { Insignia } from "@/components/ui/Semaforo";
import { Girador, SkeletonMetricas, SkeletonTabla } from "@/components/ui/Skeleton";
import { Tabla, type Columna } from "@/components/ui/Tabla";
import { TarjetaMetrica } from "@/components/ui/TarjetaMetrica";
import { useAvisos } from "@/components/ui/Toast";
import { useAccion } from "@/hooks/useAccion";
import {
  marcarCuotaPagada,
  useAging,
  useCuotas,
  useVencidos,
  useVencimientos,
  type CuotaVencida,
} from "@/hooks/useCartera";
import { useResumenExpedientes } from "@/hooks/useExpedientes";
import type { PlanPago, TipoExpediente } from "@/types/api";
import type { Semaforo } from "@/utils/estados";
import {
  formatearDinero,
  formatearEntero,
  formatearFecha,
  textoOGuion,
} from "@/utils/format";

import { BuscadorUniversal } from "@/components/cobranza/BuscadorUniversal";
import { PanelInformacionFinanciera } from "@/components/cobranza/PanelInformacionFinanciera";
import { MatrizPagoMixto } from "@/components/cobranza/MatrizPagoMixto";
import { HistorialCobros } from "@/components/cobranza/HistorialCobros";
import { ModuloArqueoDiario } from "@/components/cobranza/ModuloArqueoDiario";
import { ReciboModal } from "@/components/cobranza/ReciboModal";
import {
  useTasaCambio,
  useResumenFinanciero,
  useCreditosPagados,
  type CreditoEncontrado,
  type ResultadoPago,
} from "@/hooks/useCobranzas";
import { useSesion } from "@/components/providers/ProveedorSesion";

import { TableroCarteraCobranzas } from "@/components/cobranza/TableroCarteraCobranzas";
import { ListaCreditosCartera } from "@/components/cobranza/ListaCreditosCartera";
import { SeccionCreditosPagados } from "@/components/cobranza/SeccionCreditosPagados";
import { BuscadorTabla } from "@/components/ui/BuscadorTabla";
import {
  IconoDashboard,
  IconoTarjeta,
  IconoDocumento,
  IconoBalanza,
  IconoTrending,
  IconoChevronLeft,
  IconoCheck,
} from "@/components/ui/Iconos";

const POR_PAGINA = 10;
const TRAMOS = ["1-30 días", "31-60 días", "61-90 días", "> 90 días"] as const;
type Tramo = (typeof TRAMOS)[number];

function tramoDe(dias: number): Tramo {
  if (dias <= 30) return "1-30 días";
  if (dias <= 60) return "31-60 días";
  if (dias <= 90) return "61-90 días";
  return "> 90 días";
}

function acentoTramo(tramo: Tramo): Semaforo {
  if (tramo === "1-30 días") return "ambar";
  return "rojo";
}

type Pestana = "dashboard" | "caja" | "historial" | "arqueo" | "aging" | "pagados";

export default function CarteraPage() {
  const { sesion } = useSesion();
  const { tasa: tasaCambio, cargando: cargandoTasa } = useTasaCambio();
  const { resumen: resumenPagados } = useCreditosPagados();

  const [pestana, setPestana] = useState<Pestana>("dashboard");
  const [monedaPago, setMonedaPago] = useState<"USD" | "VES" | "COP">("USD");

  const [tipoExp, setTipoExp] = useState<TipoExpediente | null>(null);
  const [expId, setExpId] = useState<number | null>(null);

  const { resumen, cargando: cargandoResumen, recargar: recargarResumen } =
    useResumenFinanciero(tipoExp, expId);

  const [montoSugeridoCaja, setMontoSugeridoCaja] = useState<number>(0);
  const [reciboEmitido, setReciboEmitido] = useState<ResultadoPago | null>(null);
  const [modalReciboAbierto, setModalReciboAbierto] = useState(false);

  if (!sesion || !["Cobranzas", "Superadmin", "Comité"].includes(sesion.rol)) {
    return <SinResultados mensaje="Su rol no tiene acceso a las operaciones de cartera y cobranzas." />;
  }

  const manejarSeleccionCredito = (credito: CreditoEncontrado) => {
    setTipoExp(credito.tipo);
    setExpId(credito.id);
    setMontoSugeridoCaja(0);
  };

  const manejarSeleccionMonto = (monto: number) => {
    setMontoSugeridoCaja(monto);
  };

  const manejarPagoExitoso = (resultado: ResultadoPago) => {
    setReciboEmitido(resultado);
    setModalReciboAbierto(true);
    recargarResumen();
    setPestana("historial");
  };

  const irACaja = (id?: number, t?: "corp" | "auto") => {
    if (id && t) {
      setExpId(id);
      setTipoExp(t);
      setMontoSugeridoCaja(0);
    }
    setPestana("caja");
  };

  const irAArqueo = () => {
    setPestana("arqueo");
  };

  return (
    <div className="space-y-6">
      <EncabezadoPagina
        icono="▦"
        miga="Inicio / Cartera"
        titulo="Módulo de Cartera y Cobranzas"
        bajada="Gestión integral de cobros: KPIs del día, salud de cartera, Caja Mixta multi-moneda, Tasa BCV, Cascada Legal y Arqueo Diario."
      />

      {/* Selector de Pestañas Principales */}
      <div className="flex flex-wrap border-b border-borde">
        <button
          type="button"
          onClick={() => setPestana("dashboard")}
          className={`inline-flex items-center gap-2 px-5 py-2.5 text-xs font-semibold transition border-b-2 ${pestana === "dashboard"
            ? "border-kaizen-800 text-kaizen-900 bg-slate-50"
            : "border-transparent text-tinta-suave hover:text-kaizen-800"
            }`}
        >
          <IconoDashboard className="h-4 w-4" />
          <span>Monitoreo y KPIs Operativos</span>
        </button>
        <button
          type="button"
          onClick={() => setPestana("caja")}
          className={`inline-flex items-center gap-2 px-5 py-2.5 text-xs font-semibold transition border-b-2 ${pestana === "caja"
            ? "border-kaizen-800 text-kaizen-900 bg-slate-50"
            : "border-transparent text-tinta-suave hover:text-kaizen-800"
            }`}
        >
          <IconoTarjeta className="h-4 w-4" />
          <span>Operación de Cobro (Caja Mixta)</span>
        </button>
        <button
          type="button"
          onClick={() => setPestana("historial")}
          className={`inline-flex items-center gap-2 px-5 py-2.5 text-xs font-semibold transition border-b-2 ${pestana === "historial"
            ? "border-kaizen-800 text-kaizen-900 bg-slate-50"
            : "border-transparent text-tinta-suave hover:text-kaizen-800"
            }`}
        >
          <IconoDocumento className="h-4 w-4" />
          <span>Historial de Cobros del Cliente</span>
        </button>
        <button
          type="button"
          onClick={() => setPestana("arqueo")}
          className={`inline-flex items-center gap-2 px-5 py-2.5 text-xs font-semibold transition border-b-2 ${pestana === "arqueo"
            ? "border-kaizen-800 text-kaizen-900 bg-slate-50"
            : "border-transparent text-tinta-suave hover:text-kaizen-800"
            }`}
        >
          <IconoBalanza className="h-4 w-4" />
          <span>Arqueo Diario y Cierre de Caja</span>
        </button>
        <button
          type="button"
          onClick={() => setPestana("aging")}
          className={`inline-flex items-center gap-2 px-5 py-2.5 text-xs font-semibold transition border-b-2 ${pestana === "aging"
            ? "border-kaizen-800 text-kaizen-900 bg-slate-50"
            : "border-transparent text-tinta-suave hover:text-kaizen-800"
            }`}
        >
          <IconoTrending className="h-4 w-4" />
          <span>Indicadores y Antigüedad (Aging)</span>
        </button>
        <button
          type="button"
          onClick={() => setPestana("pagados")}
          className={`inline-flex items-center gap-2 px-5 py-2.5 text-xs font-semibold transition border-b-2 ${pestana === "pagados"
            ? "border-emerald-600 text-emerald-950 bg-emerald-50/60 font-bold"
            : "border-transparent text-tinta-suave hover:text-emerald-800"
            }`}
        >
          <IconoCheck className="h-4 w-4 text-emerald-600" />
          <span>Créditos Pagados</span>
          {resumenPagados.total_creditos_pagados > 0 && (
            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-800 border border-emerald-300">
              {resumenPagados.total_creditos_pagados}
            </span>
          )}
        </button>
      </div>

      {cargandoTasa && <SkeletonMetricas tarjetas={1} />}

      {/* ── PESTAÑA PRINCIPAL: Monitoreo y KPIs Operativos ─────────────── */}
      {pestana === "dashboard" && (
        <TableroCarteraCobranzas
          alIrACaja={irACaja}
          alIrAArqueo={irAArqueo}
          alIrAPagados={() => setPestana("pagados")}
        />
      )}

      {/* ── PESTAÑA 2: Caja Mixta y Operación de Cobro ──────────────────── */}
      {pestana === "caja" && (
        <div className="space-y-6">
          {/* 1. Buscador Universal y Selector de Moneda */}
          <BuscadorUniversal
            tasaCambio={tasaCambio}
            monedaPago={monedaPago}
            alCambiarMoneda={setMonedaPago}
            alSeleccionarCredito={manejarSeleccionCredito}
            creditoSeleccionadoId={expId}
          />

          {/* 2. Panel de Información Financiera o Lista de Créditos de Cartera */}
          {cargandoResumen ? (
            <SkeletonMetricas tarjetas={4} />
          ) : resumen ? (
            <>
              {/* Barra de Crédito Activo en Caja con opción de cambiar de crédito */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-xl border border-kaizen-200 bg-kaizen-50/70 p-3.5 text-xs shadow-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="flex h-2.5 w-2.5 rounded-full bg-verde-trazo"></span>
                  <span className="font-semibold text-kaizen-900">Crédito en Caja:</span>
                  <span className="rounded bg-kaizen-800 px-2 py-0.5 font-bold text-white uppercase text-[11px]">
                    {resumen.codigo_credito}
                  </span>
                  <span className="font-bold text-kaizen-900">{resumen.cliente}</span>
                  <span className="rounded border border-kaizen-200 bg-white px-2 py-0.5 font-mono text-[11px] text-tinta">
                    Doc: {resumen.documento}
                  </span>
                  <span className="text-tinta-suave">
                    · Saldo Capital: <strong className="text-kaizen-900 font-bold tabular-nums">${resumen.saldo_capital.toLocaleString("en-US", { minimumFractionDigits: 2 })}</strong>
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setExpId(null);
                    setTipoExp(null);
                    setMontoSugeridoCaja(0);
                  }}
                  className="inline-flex items-center gap-1.5 self-start sm:self-auto rounded-lg border border-kaizen-300 bg-white px-3 py-1.5 font-semibold text-kaizen-800 hover:bg-kaizen-100 transition shadow-xs"
                >
                  <IconoChevronLeft className="h-3.5 w-3.5" />
                  <span>Cambiar crédito / Ver lista de cartera</span>
                </button>
              </div>

              <PanelInformacionFinanciera
                resumen={resumen}
                alSeleccionarParaPagar={manejarSeleccionMonto}
              />

              {/* 3. Matriz de Pago Mixto */}
              <MatrizPagoMixto
                key={`${resumen.expediente_id}-${montoSugeridoCaja}`}
                resumen={resumen}
                tasaCambio={tasaCambio}
                monedaPredeterminada={monedaPago}
                montoSugeridoInicial={montoSugeridoCaja}
                alProcesarExitoso={manejarPagoExitoso}
              />
            </>
          ) : (
            /* Lista de Créditos Aprobados por el Comité paginada de 5 en 5 */
            <ListaCreditosCartera
              alSeleccionarCredito={manejarSeleccionCredito}
              creditoSeleccionadoId={expId}
              alIrAPagados={() => setPestana("pagados")}
            />
          )}
        </div>
      )}

      {/* ── PESTAÑA 3: Historial de Cobros ────────────────────────────── */}
      {pestana === "historial" && (
        <HistorialCobros tipo={tipoExp} expId={expId} resumen={resumen} />
      )}

      {/* ── PESTAÑA 4: Arqueo Diario ──────────────────────────────────── */}
      {pestana === "arqueo" && <ModuloArqueoDiario />}

      {/* ── PESTAÑA 5: Antigüedad de Deuda y Métricas Consolidadas ─────── */}
      {pestana === "aging" && <VistaAgingCartera />}

      {/* ── PESTAÑA 6: Créditos Pagados y Solvencias ───────────────────── */}
      {pestana === "pagados" && (
        <SeccionCreditosPagados
          alVerHistorial={(id, tipo) => {
            setExpId(id);
            setTipoExp(tipo);
            setPestana("historial");
          }}
        />
      )}

      {/* ── Modal de Emisión de Recibo Oficial ────────────────────────── */}
      <ReciboModal
        abierto={modalReciboAbierto}
        alCerrar={() => setModalReciboAbierto(false)}
        recibo={reciboEmitido}
      />
    </div>
  );
}

/** Componente de la vista de Aging de Cartera (previamente principal) */
function VistaAgingCartera() {
  const corporativos = useResumenExpedientes("corporativos");
  const automotrices = useResumenExpedientes("automotrices");
  const vencimientos = useVencimientos(30);
  const aging = useAging();
  const vencidos = useVencidos();
  const [tramo, setTramo] = useState<Tramo | null>(null);

  const { notificarError } = useAvisos();
  useEffect(() => {
    if (aging.error?.esDeRed) notificarError(aging.error);
  }, [aging.error, notificarError]);

  const cartera = useMemo(() => {
    const aprobado = (r: Record<string, { n: number; monto: number }> | null) =>
      r?.APROBADO ?? { n: 0, monto: 0 };
    const corp = aprobado(corporativos.datos);
    const auto = aprobado(automotrices.datos);
    return {
      monto: corp.monto + auto.monto,
      activos: corp.n + auto.n,
    };
  }, [corporativos.datos, automotrices.datos]);

  const filtradas = useMemo(() => {
    const filas = vencidos.datos ?? [];
    if (!tramo) return filas;
    return filas.filter((c) => tramoDe(c.dias_atraso) === tramo);
  }, [vencidos.datos, tramo]);

  const totalFiltrado = useMemo(
    () => filtradas.reduce((suma, c) => suma + (c.cuota ?? 0), 0),
    [filtradas],
  );

  const [busquedaVencidas, setBusquedaVencidas] = useState("");
  const filtradasPorBusqueda = useMemo(() => {
    if (!busquedaVencidas.trim()) return filtradas;
    const q = busquedaVencidas.toLowerCase().trim();
    return filtradas.filter(
      (c) =>
        `${c.tipo_expediente}/${c.expediente_id}`.toLowerCase().includes(q) ||
        String(c.periodo || "").includes(q) ||
        String(c.dias_atraso || "").includes(q) ||
        String(c.cuota || "").includes(q),
    );
  }, [filtradas, busquedaVencidas]);

  const [paginaVencidas, setPaginaVencidas] = useState(1);
  const vencidasPagina = useMemo(
    () =>
      filtradasPorBusqueda.slice(
        (paginaVencidas - 1) * POR_PAGINA,
        paginaVencidas * POR_PAGINA,
      ),
    [filtradasPorBusqueda, paginaVencidas],
  );

  const columnas: Array<Columna<CuotaVencida>> = [
    {
      clave: "expediente",
      encabezado: "Expediente",
      celda: (c) => (
        <span className="font-mono text-xs whitespace-nowrap text-tinta-suave">
          {c.tipo_expediente}/{c.expediente_id}
        </span>
      ),
    },
    {
      clave: "periodo",
      encabezado: "Cuota",
      alineacion: "derecha",
      celda: (c) => <span className="tabular-nums">{c.periodo ?? "—"}</span>,
    },
    {
      clave: "fecha",
      encabezado: "Vencimiento",
      alineacion: "derecha",
      celda: (c) => (
        <span className="whitespace-nowrap tabular-nums">
          {formatearFecha(c.fecha_pago)}
        </span>
      ),
    },
    {
      clave: "dias",
      encabezado: "Días",
      alineacion: "derecha",
      celda: (c) => (
        <Insignia
          tono={acentoTramo(tramoDe(c.dias_atraso))}
          texto={`${formatearEntero(c.dias_atraso)} d`}
        />
      ),
    },
    {
      clave: "monto",
      encabezado: "Importe",
      alineacion: "derecha",
      celda: (c) => (
        <span className="font-semibold whitespace-nowrap tabular-nums">
          {formatearDinero(c.cuota)}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-8">
      <section>
        {corporativos.cargando || vencimientos.cargando ? (
          <SkeletonMetricas />
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <TarjetaMetrica
              rotulo="Cartera colocada"
              valor={formatearDinero(cartera.monto)}
              nota={`${formatearEntero(cartera.activos)} créditos aprobados`}
            />
            <TarjetaMetrica
              rotulo="Vencido"
              valor={formatearDinero(vencimientos.datos?.monto_vencido ?? 0)}
              nota={`${formatearEntero(vencimientos.datos?.n_vencidas ?? 0)} cuotas sin cobrar`}
              acento={(vencimientos.datos?.n_vencidas ?? 0) > 0 ? "rojo" : "verde"}
            />
            <TarjetaMetrica
              rotulo="Vence en 30 días"
              valor={formatearDinero(vencimientos.datos?.monto_proximo ?? 0)}
              nota={`${formatearEntero(vencimientos.datos?.n_proximas ?? 0)} cuotas por vencer`}
              acento="ambar"
            />
            <TarjetaMetrica
              rotulo="Tramo seleccionado"
              valor={tramo ?? "Todos"}
              nota={`${formatearEntero(filtradas.length)} cuotas · ${formatearDinero(totalFiltrado)}`}
              acento={tramo ? acentoTramo(tramo) : "neutro"}
            />
          </div>
        )}
      </section>

      <section>
        <div className="mb-4 flex flex-wrap items-baseline justify-between gap-3">
          <h2 className="text-sm font-semibold tracking-wide text-tinta-suave uppercase">
            Antigüedad de la deuda
          </h2>
          {tramo && (
            <button
              type="button"
              onClick={() => setTramo(null)}
              className="text-sm font-semibold text-kaizen-600 transition hover:text-kaizen-900"
            >
              Quitar el filtro
            </button>
          )}
        </div>

        {aging.cargando ? (
          <SkeletonMetricas />
        ) : aging.error ? (
          <Alerta error={aging.error} alReintentar={aging.recargar} />
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {TRAMOS.map((nombre) => {
              const dato = aging.datos?.[nombre] ?? { n: 0, monto: 0, prom_dias: 0 };
              const activo = tramo === nombre;
              return (
                <button
                  key={nombre}
                  type="button"
                  aria-pressed={activo}
                  onClick={() => setTramo(activo ? null : nombre)}
                  className={`rounded-xl border bg-white p-5 text-left shadow-sm transition hover:shadow-md ${activo
                    ? "border-kaizen-600 ring-2 ring-kaizen-600/25"
                    : "border-borde"
                    }`}
                >
                  <p className="text-xs font-semibold tracking-wide text-tinta-suave uppercase">
                    {nombre}
                  </p>
                  <p className="mt-3 text-2xl font-bold text-kaizen-900 tabular-nums">
                    {formatearDinero(dato.monto)}
                  </p>
                  <p className="mt-2 text-xs text-tinta-suave">
                    {formatearEntero(dato.n)} cuotas ·{" "}
                    {formatearEntero(dato.prom_dias)} días de media
                  </p>
                </button>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}

function BotonPagada({
  planId,
  alPagar,
}: {
  planId: number;
  alPagar: () => void;
}) {
  const accion = useAccion(() => marcarCuotaPagada(planId));
  const { notificarError } = useAvisos();

  const pulsar = async () => {
    const hecho = await accion.ejecutar();
    if (hecho !== null) alPagar();
    else if (accion.error) notificarError(accion.error);
  };

  return (
    <button
      type="button"
      className={`${BOTON.neutro} px-3 py-1.5 text-xs`}
      disabled={accion.enviando}
      onClick={pulsar}
    >
      {accion.enviando && <Girador />}
      Marcar pagada
    </button>
  );
}

/** Detalle paginado de todas las cuotas, con su estado. */
function PlanDeCuotas({ alCobrar }: { alCobrar: () => void }) {
  const [pagina, setPagina] = useState(1);
  const [estado, setEstado] = useState("PENDIENTE");
  const [busqueda, setBusqueda] = useState("");
  const cuotas = useCuotas({
    pagina,
    porPagina: POR_PAGINA,
    estado: estado || undefined,
  });
  const { notificar } = useAvisos();

  const columnas: Array<Columna<PlanPago>> = [
    {
      clave: "accion",
      encabezado: "",
      alineacion: "derecha",
      celda: (c) =>
        c.estado !== "PAGADO" && c.id ? (
          <BotonPagada
            planId={c.id}
            alPagar={() => {
              notificar("exito", "Cuota cobrada", "La cuota ha quedado registrada como pagada.");
              cuotas.recargar();
              alCobrar();
            }}
          />
        ) : null,
    },
    {
      clave: "expediente",
      encabezado: "Expediente",
      celda: (c) => (
        <span className="font-mono text-xs whitespace-nowrap text-tinta-suave">
          {c.tipo_expediente}/{c.expediente_id}
        </span>
      ),
    },
    {
      clave: "periodo",
      encabezado: "Cuota",
      alineacion: "derecha",
      celda: (c) => <span className="tabular-nums">{c.periodo ?? "—"}</span>,
    },
    {
      clave: "fecha",
      encabezado: "Fecha",
      alineacion: "derecha",
      celda: (c) => (
        <span className="whitespace-nowrap tabular-nums">
          {formatearFecha(c.fecha_pago)}
        </span>
      ),
    },
    {
      clave: "cuota",
      encabezado: "Cuota",
      alineacion: "derecha",
      celda: (c) => <span className="tabular-nums">{formatearDinero(c.cuota)}</span>,
    },
    {
      clave: "capital",
      encabezado: "Capital",
      alineacion: "derecha",
      celda: (c) => (
        <span className="tabular-nums">{formatearDinero(c.capital)}</span>
      ),
    },
    {
      clave: "interes",
      encabezado: "Interés",
      alineacion: "derecha",
      celda: (c) => <span className="tabular-nums">{formatearDinero(c.interes)}</span>,
    },
    {
      clave: "saldo",
      encabezado: "Saldo",
      alineacion: "derecha",
      celda: (c) => <span className="tabular-nums">{formatearDinero(c.saldo)}</span>,
    },
    {
      clave: "estado",
      encabezado: "Estado",
      celda: (c) => (
        <Insignia
          tono={c.estado === "PAGADO" ? "verde" : "ambar"}
          texto={textoOGuion(c.estado)}
        />
      ),
    },
  ];

  const filas = cuotas.datos ?? [];

  const filasFiltradas = useMemo(() => {
    if (!busqueda.trim()) return filas;
    const q = busqueda.toLowerCase().trim();
    return filas.filter(
      (c) =>
        `${c.tipo_expediente}/${c.expediente_id}`.toLowerCase().includes(q) ||
        String(c.periodo || "").includes(q) ||
        String(c.estado || "").toLowerCase().includes(q) ||
        String(c.cuota || "").includes(q),
    );
  }, [filas, busqueda]);

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold tracking-wide text-tinta-suave uppercase">
            Plan de pagos consolidado
          </h2>
          <p className="text-xs text-tinta-suave mt-0.5">
            Cronograma general de amortización de créditos de la cartera
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="w-full sm:w-64">
            <BuscadorTabla
              valor={busqueda}
              alCambiar={setBusqueda}
              placeholder="Buscar por expediente, cuota..."
              conteoFiltrado={filasFiltradas.length}
              conteoTotal={filas.length}
            />
          </div>

          <label className="flex items-center gap-2">
            <span className="text-xs font-semibold tracking-wide text-tinta-suave uppercase">
              Estado:
            </span>
            <select
              value={estado}
              onChange={(evento) => {
                setEstado(evento.target.value);
                setPagina(1);
              }}
              className="rounded-lg border border-borde bg-white px-2.5 py-1.5 text-xs text-tinta outline-none transition focus:border-kaizen-600 focus:ring-1 focus:ring-kaizen-600/20"
            >
              <option value="">Todas</option>
              <option value="PENDIENTE">Pendientes</option>
              <option value="PAGADO">Pagadas</option>
            </select>
          </label>
        </div>
      </div>

      {cuotas.cargando && filas.length === 0 ? (
        <SkeletonTabla columnas={8} filas={6} />
      ) : cuotas.error ? (
        <Alerta error={cuotas.error} alReintentar={cuotas.recargar} />
      ) : filas.length === 0 ? (
        <SinResultados mensaje="No hay cuotas con el estado seleccionado." />
      ) : filasFiltradas.length === 0 ? (
        <div className="rounded-lg border border-dashed border-borde p-6 text-center text-xs text-tinta-suave">
          No se encontraron cuotas que coincidan con &ldquo;{busqueda}&rdquo;.
        </div>
      ) : (
        <Tabla
          columnas={columnas}
          filas={filasFiltradas}
          claveFila={(c, i) => c.id ?? `cuota-${i}`}
          pie={
            <>
              <p className="text-sm text-tinta-suave tabular-nums">
                Página {pagina}
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  className={`${BOTON.neutro} px-3 py-1.5 text-sm`}
                  disabled={pagina <= 1}
                  onClick={() => setPagina(pagina - 1)}
                >
                  Anterior
                </button>
                <button
                  type="button"
                  className={`${BOTON.neutro} px-3 py-1.5 text-sm`}
                  disabled={filas.length < POR_PAGINA}
                  onClick={() => setPagina(pagina + 1)}
                >
                  Siguiente
                </button>
              </div>
            </>
          }
        />
      )}
    </section>
  );
}
