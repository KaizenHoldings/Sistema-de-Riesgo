"use client";

/**
 * Formulario de Riesgo.
 *
 * Conserva la secuencia de dos pasos de la versión anterior: primero se calcula
 * el scoring con el motor y se revisa el resultado —score, tasa sugerida y las
 * métricas de cobertura—, y solo después se firma la etapa con esas cifras. Nada
 * se calcula aquí: la aritmética vive en el motor del backend, y esta pantalla
 * únicamente recoge las entradas y muestra lo que devuelve.
 *
 * Firmar sin haber calculado queda bloqueado a propósito: registrar la etapa con
 * un score de cero es lo que dejaba expedientes sin calificar en la versión
 * anterior.
 */

import { useCallback, useState, useEffect, useMemo, useRef } from "react";

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);
  return debouncedValue;
}

import {
  Bloque,
  CampoCasilla,
  CampoNumero,
  CampoSeleccion,
  CampoTextoLargo,
  aNumero,
} from "@/components/sections/campos";
import { BOTON } from "@/components/ui/Modal";
import { Girador } from "@/components/ui/Skeleton";
import {
  ENTRADAS_IHP_VACIAS,
  aEntradasScoring,
  normalizarEntradas,
  derivarEstados,
  type EntradasIHP,
} from "@/business/finanzas/estadosFinancieros";
import { EstadosFinancierosIHP } from "@/components/sections/EstadosFinancierosIHP";
import {
  claveBorradorRiesgo,
  fundirConocidas,
  useBorradorLocal,
  type EstadoBorrador,
} from "@/hooks/useBorradorLocal";
import { TARJETA_SEMAFORO, semaforoMotor } from "@/utils/estados";
import type {
  EvaluacionGuardada,
  EvaluacionRiesgo,
  EvaluacionRiesgoAuto,
  EvaluacionRiesgoCorp,
  ResultadoScoring,
  RiskAutoForm,
  RiskCorpForm,
  RiskForm,
  ServiceResult,
  TipoExpediente,
} from "@/business/workflows/types";

const MONEDAS = ["USD", "VES", "EUR"] as const;

/**
 * Persistencia de la hoja de trabajo en la base de datos.
 *
 * Llega como callbacks para que el formulario siga sin conocer rutas ni
 * transporte, igual que con la firma.
 */
export interface PersistenciaRiesgo {
  /** Riesgo y Superadmin escriben la hoja; los demás la leen. */
  puedeGuardar: boolean;
  cargar: (
    signal: AbortSignal,
  ) => Promise<ServiceResult<EvaluacionGuardada<EvaluacionRiesgo> | null>>;
  /**
   * `modo` dice quién guarda, para que el panel decida qué anunciar;
   * `avisarError` en falso pide callar un fallo que ya se avisó.
   */
  guardar: (
    datos: EvaluacionRiesgo,
    opciones: { modo: ModoGuardado; avisarError: boolean },
  ) => Promise<ServiceResult<unknown>>;
}

/** Origen de un guardado de la hoja de trabajo. */
export type ModoGuardado = "automatico" | "manual" | "firma";

export function FormularioRiesgo({
  tipo,
  expId,
  enviando,
  bloqueado,
  persistencia,
  onCalcular,
  onRegistrar,
}: {
  tipo: TipoExpediente;
  /** Expediente evaluado: identifica el borrador local de este formulario. */
  expId: number;
  enviando: boolean;
  /**
   * La etapa ya está firmada o el expediente tiene dictamen: el formulario se
   * muestra como consulta. El backend rechaza igualmente cualquier escritura;
   * esto solo evita ofrecerla.
   */
  bloqueado: boolean;
  persistencia: PersistenciaRiesgo;
  onCalcular: (
    entradas: Record<string, unknown>,
  ) => Promise<ServiceResult<ResultadoScoring>>;
  onRegistrar: (form: RiskForm) => Promise<ServiceResult<unknown>>;
}) {
  const [scoring, setScoring] = useState<ResultadoScoring | null>(null);
  const [calculando, setCalculando] = useState(false);

  const calcular = async (entradas: Record<string, unknown>) => {
    setCalculando(true);
    const resultado = await onCalcular(entradas);
    setCalculando(false);
    if (resultado.success) setScoring(resultado.data);
  };

  const claveBorrador = claveBorradorRiesgo(tipo, expId);

  return tipo === "corp" ? (
    <RiesgoCorporativo
      claveBorrador={claveBorrador}
      bloqueado={bloqueado}
      persistencia={persistencia}
      scoring={scoring}
      calculando={calculando}
      enviando={enviando}
      onCalcular={calcular}
      onRegistrar={onRegistrar}
    />
  ) : (
    <RiesgoAutomotriz
      claveBorrador={claveBorrador}
      bloqueado={bloqueado}
      persistencia={persistencia}
      scoring={scoring}
      calculando={calculando}
      enviando={enviando}
      onCalcular={calcular}
      onRegistrar={onRegistrar}
    />
  );
}

/** Fase del asistente del formulario corporativo. */
type Fase = 1 | 2 | 3;

const FASES: Array<{ numero: Fase; titulo: string; detalle: string }> = [
  { numero: 1, titulo: "Fase 1", detalle: "Ingresos, costos y balance" },
  { numero: 2, titulo: "Fase 2", detalle: "Gastos, depreciación y flujo" },
  { numero: 3, titulo: "Fase 3", detalle: "Datos de riesgo y conclusiones" },
];

const anterior = (fase: Fase): Fase => (fase === 3 ? 2 : 1);
const siguiente = (fase: Fase): Fase => (fase === 1 ? 2 : 3);

/**
 * Indicador de fases del asistente.
 *
 * Es navegación, no formulario: vive fuera del `fieldset` que bloquea la
 * edición, de modo que un expediente cerrado pueda recorrerse entero para
 * leerlo. Cada paso es además un botón, para saltar sin pasar por el medio.
 */
function PasosFase({
  fase,
  alCambiar,
}: {
  fase: Fase;
  alCambiar: (fase: Fase) => void;
}) {
  return (
    <div
      className="flex flex-wrap gap-2 border-b border-borde bg-lienzo px-5 py-3"
      role="tablist"
      aria-label="Fases del formulario"
    >
      {FASES.map((paso) => {
        const activa = paso.numero === fase;
        return (
          <button
            key={paso.numero}
            type="button"
            role="tab"
            aria-selected={activa}
            onClick={() => alCambiar(paso.numero)}
            className={`flex items-center gap-2 rounded-lg px-3 py-2 text-left transition ${
              activa
                ? "bg-white text-kaizen-900 shadow-sm"
                : "text-tinta-suave hover:text-kaizen-900"
            }`}
          >
            <span
              className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                activa
                  ? "bg-kaizen-800 text-white"
                  : "border border-borde bg-white text-tinta-suave"
              }`}
              aria-hidden
            >
              {paso.numero}
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-semibold">{paso.titulo}</span>
              <span className="block text-xs text-tinta-suave">{paso.detalle}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

function ResultadoDelMotor({
  scoring,
  extras,
}: {
  scoring: ResultadoScoring | null;
  extras: Array<{
    rotulo: string;
    valor: string;
    delta?: string;
    deltaColor?: "normal" | "inverse";
  }>;
}) {
  if (!scoring) {
    return (
      <p className="mt-5 rounded-lg bg-lienzo px-4 py-3 text-sm text-tinta-suave">
        Calcule el scoring antes de firmar la etapa: la firma registra las cifras
        que devuelve el motor.
      </p>
    );
  }

  const tono =
    scoring.score_final >= 7
      ? "bg-verde-fondo text-verde-trazo"
      : scoring.score_final >= 5
        ? "bg-ambar-fondo text-ambar-trazo"
        : "bg-rojo-fondo text-rojo-trazo";

  return (
    <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4 md:grid-cols-6">
      <div className={`col-span-1 rounded-lg px-4 py-3 ${tono}`}>
        <p className="text-xs font-semibold uppercase">Score final</p>
        <p className="mt-1 text-xl font-bold tabular-nums">
          {scoring.score_final.toFixed(2)}
        </p>
      </div>
      <div className="col-span-1 rounded-lg bg-kaizen-100/50 px-4 py-3">
        <p className="text-xs font-semibold text-tinta-suave uppercase">
          Tasa sugerida
        </p>
        <p className="mt-1 text-xl font-bold text-kaizen-900 tabular-nums">
          {scoring.tasa_sugerida.toFixed(2)}%
        </p>
      </div>
      {extras.map(({ rotulo, valor, delta, deltaColor }) => (
        <div key={rotulo} className="col-span-1 rounded-lg bg-lienzo px-4 py-3">
          <p className="text-xs font-semibold text-tinta-suave uppercase">
            {rotulo}
          </p>
          <div className="mt-1 flex items-center justify-between">
            <p className="text-xl font-bold text-kaizen-900 tabular-nums">
              {valor}
            </p>
            {delta && (
              <span
                className={`ml-2 text-xs font-bold ${
                  deltaColor === "inverse" ? "text-rojo-trazo" : "text-verde-trazo"
                }`}
              >
                {delta}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function RiesgoCorporativo({
  claveBorrador,
  bloqueado,
  persistencia,
  scoring,
  calculando,
  enviando,
  onCalcular,
  onRegistrar,
}: {
  claveBorrador: string;
  bloqueado: boolean;
  persistencia: PersistenciaRiesgo;
  scoring: ResultadoScoring | null;
  calculando: boolean;
  enviando: boolean;
  onCalcular: (entradas: Record<string, unknown>) => Promise<void>;
  onRegistrar: (form: RiskForm) => Promise<ServiceResult<unknown>>;
}) {
  // Las magnitudes del balance y el EBITDA ya no viven aquí: se derivan de los
  // estados financieros IHP. Solo queda lo que el analista teclea aparte.
  const [f, setF] = useState({
    ing_mensuales: "0",
    cuota_est: "0",
    rm_score: "0",
    moneda: "USD",
    estres: false,
    covenants: "",
    obs_riesgo: "",
  });
  
  const [tab, setTab] = useState<"formulario" | "indicadores" | "altman">(
    "formulario",
  );
  // Asistente de tres fases. Divide el formulario sin dividir el estado: las
  // tres escriben sobre el mismo `f`/`ihpTexto`, así que cambiar de fase no
  // pierde nada ni recalcula nada.
  const [fase, setFase] = useState<Fase>(1);

  // Las partidas IHP se guardan como texto para no reformatear lo que el
  // analista está escribiendo; la conversión a número ocurre al derivar.
  const [ihpTexto, setIhpTexto] = useState<Record<keyof EntradasIHP, string>>(
    () =>
      Object.fromEntries(
        Object.keys(ENTRADAS_IHP_VACIAS).map((clave) => [clave, "0"]),
      ) as Record<keyof EntradasIHP, string>,
  );

  const set = (clave: keyof typeof f, valor: string | boolean) =>
    setF((actual) => ({ ...actual, [clave]: valor }));

  const setIhp = (clave: keyof EntradasIHP, valor: string) =>
    setIhpTexto((actual) => ({ ...actual, [clave]: valor }));

  // Borrador local: lo tecleado sobrevive a una recarga o a un cierre accidental
  // de la pestaña. Se guarda el texto en crudo para restaurar los campos tal cual
  // se escribieron; la conversión y el saneado siguen pasando por `aNumero` y
  // `normalizarEntradas` al derivar.
  const estadoBorrador = useMemo(() => ({ f, ihpTexto }), [f, ihpTexto]);
  const borrador = useBorradorLocal(claveBorrador, estadoBorrador, (datos) => {
    setF((actual) => fundirConocidas(actual, datos?.f));
    setIhpTexto((actual) =>
      fundirConocidas(
        {
          ...(Object.fromEntries(
            Object.keys(ENTRADAS_IHP_VACIAS).map((clave) => [clave, "0"]),
          ) as Record<keyof EntradasIHP, string>),
          ...actual,
        },
        datos?.ihpTexto,
      ),
    );
  });

  // Lo guardado en la base prevalece sobre el borrador local: es lo que el
  // analista confirmó, desde este equipo o desde otro.
  const aplicarServidor = (crudo: EvaluacionGuardada<EvaluacionRiesgo>) => {
    const datos = crudo as EvaluacionGuardada<EvaluacionRiesgoCorp>;
    setF((actual) => ({
      ...actual,
      ing_mensuales: aTexto(datos.ingresos_mensuales),
      cuota_est: aTexto(datos.cuota_mensual),
      rm_score: aTexto(datos.kc_score),
      moneda: datos.moneda || actual.moneda,
      estres: Boolean(datos.aplicar_estres),
      covenants: datos.covenants ?? "",
      obs_riesgo: datos.obs_riesgo ?? "",
    }));
    setIhpTexto(
      Object.fromEntries(
        Object.keys(ENTRADAS_IHP_VACIAS).map((clave) => [
          clave,
          aTexto(datos.entradas_ihp?.[clave]),
        ]),
      ) as Record<keyof EntradasIHP, string>,
    );
  };

  /**
   * Partidas derivadas.
   *
   * Se recalculan en el mismo render en que cambia una entrada, sin efecto de
   * por medio: lo que se ve en pantalla y lo que se envía salen de la misma
   * llamada y no pueden discrepar.
   */
  // El estado se inicializa una sola vez al montar y la recarga en caliente lo
  // conserva, así que puede no traer los campos añadidos después. Se completa
  // con todas las claves del modelo: sin esto, un campo nuevo no tendría texto
  // que mostrar y su valor entraría como `undefined` en la derivación.
  const ihpTextoCompleto = useMemo(
    () =>
      ({
        ...(Object.fromEntries(
          Object.keys(ENTRADAS_IHP_VACIAS).map((clave) => [clave, "0"]),
        ) as Record<keyof EntradasIHP, string>),
        ...ihpTexto,
      }),
    [ihpTexto],
  );

  const ihp = useMemo(
    () =>
      Object.fromEntries(
        Object.entries(ihpTextoCompleto).map(([clave, texto]) => [clave, aNumero(texto)]),
      ) as unknown as EntradasIHP,
    [ihpTextoCompleto],
  );

  const derivados = useMemo(() => derivarEstados(ihp), [ihp]);

  const fDebounced = useDebounce(f, 500);
  const ihpDebounced = useDebounce(ihp, 500);
  const derivadosDebounced = useMemo(
    () => derivarEstados(ihpDebounced),
    [ihpDebounced],
  );

  const entradas = useMemo(() => ({
    ...aEntradasScoring(ihpDebounced, derivadosDebounced),
    ingresos_mensuales: aNumero(fDebounced.ing_mensuales),
    cuota_mensual: aNumero(fDebounced.cuota_est),
    aplicar_estres: fDebounced.estres,
    kc_score: aNumero(fDebounced.rm_score),
  }), [fDebounced, ihpDebounced, derivadosDebounced]);

  useEffect(() => {
    void onCalcular(entradas);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entradas]);

  /**
   * Hoja de trabajo tal como se guarda: el cuerpo de `ScoringCorporativoIn`
   * más las partidas IHP.
   *
   * Todo pasa por `normalizarEntradas`: `aEntradasScoring` y `derivarEstados` ya
   * lo aplican, y las partidas se normalizan también antes de viajar, de modo
   * que un campo a medio teclear nunca llega a la API como `NaN`.
   */
  const evaluacion = useMemo<EvaluacionRiesgoCorp>(
    () => ({
      ...aEntradasScoring(ihp, derivados),
      ingresos_mensuales: aNumero(f.ing_mensuales),
      cuota_mensual: aNumero(f.cuota_est),
      aplicar_estres: f.estres,
      kc_score: aNumero(f.rm_score),
      moneda: f.moneda,
      covenants: f.covenants.trim(),
      obs_riesgo: f.obs_riesgo.trim(),
      entradas_ihp: normalizarEntradas(ihp) as unknown as Record<string, number>,
    }),
    [f, ihp, derivados],
  );

  const servidor = useEvaluacionServidor(
    claveBorrador,
    borrador,
    persistencia,
    evaluacion,
    aplicarServidor,
    bloqueado,
  );

  const registrar = async () => {
    if (!scoring) return;
    // La hoja se guarda antes de firmar: si no se puede guardar, tampoco se
    // firma, para que no quede una firma sin las cifras que la sostienen.
    if (persistencia.puedeGuardar && !(await servidor.guardar("firma"))) {
      return;
    }
    const form: RiskCorpForm = {
      score_f: scoring.score_final,
      rm_score: aNumero(f.rm_score),
      // Se registran las cifras derivadas de los estados IHP: son las mismas
      // que el motor usó para calificar.
      ac: derivados.totalActivosCorrientes,
      pc: derivados.totalPasivosCorrientes,
      eb: derivados.ebitda,
      gf: ihp.gastosFinancieros,
      pt: derivados.totalPasivos,
      pa: ihp.patrimonio,
      ing_mensuales: aNumero(f.ing_mensuales),
      cuota_est: aNumero(f.cuota_est),
      moneda: f.moneda,
      estres_aplicado: f.estres,
      dscr: scoring.dscr ?? 0,
      margen_ebitda: scoring.margen_ebitda ?? 0,
      tasa_sugerida: scoring.tasa_sugerida,
      covenants: f.covenants.trim(),
      obs_riesgo: f.obs_riesgo.trim(),
    };
    // Solo con la firma aceptada deja de hacer falta el borrador: si el backend
    // la rechaza, lo tecleado debe seguir ahí para corregirlo y reenviar.
    const resultado = await onRegistrar(form);
    if (resultado.success) borrador.descartar();
  };

  return (
    <form
      className="rounded-xl border border-borde bg-white shadow-sm flex flex-col"
      onSubmit={(evento) => {
        evento.preventDefault();
        void registrar();
      }}
    >
      <AvisoBloqueo bloqueado={bloqueado} />
      <div className="p-5 border-b border-borde">
        <h3 className="text-sm font-semibold text-kaizen-900">
          Evaluación de Riesgo Corporativo
        </h3>
        <p className="mt-1 text-xs text-tinta-suave">
          Balance anualizado, capacidad de pago y calificación institucional.
        </p>
      </div>

      <div className="px-5 pt-1 pb-5 border-b border-borde bg-slate-50/50">
        <ResultadoDelMotor
          scoring={scoring}
          extras={[
            { rotulo: "DSCR", valor: (scoring?.dscr ?? 0).toFixed(2) + "x" },
            { rotulo: "Margen EBITDA", valor: `${(scoring?.margen_ebitda ?? 0).toFixed(2)}%` },
          ]}
        />
      </div>

      <div className="flex border-b border-borde bg-slate-50">
        <button
          type="button"
          onClick={() => setTab("formulario")}
          className={`flex-1 py-3 text-sm font-semibold transition-colors ${
            tab === "formulario" ? "bg-white text-kaizen-600 border-b-2 border-kaizen-600" : "text-tinta-suave hover:text-tinta hover:bg-lienzo"
          }`}
        >
          Formulario de evaluación
        </button>
        <button
          type="button"
          onClick={() => setTab("indicadores")}
          
          className={`flex-1 py-3 text-sm font-semibold transition-colors ${
            tab === "indicadores" ? "bg-white text-kaizen-600 border-b-2 border-kaizen-600" : "text-tinta-suave hover:text-tinta hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed"
          }`}
        >
          Indicadores Financieros
        </button>
       
      </div>

      {tab === "formulario" && (
        <PasosFase fase={fase} alCambiar={setFase} />
      )}

      {/* El bloqueo empieza aqui, despues de la barra de pestanas y del
          indicador de fases: el
          `fieldset` deshabilita de una vez cuanto contiene —campos, casillas y
          botones de accion—, mientras que navegar entre pestanas sigue siendo
          posible para consultar indicadores y Altman en un expediente cerrado. */}
      <fieldset disabled={bloqueado} className="contents">
      <div className="p-5 min-h-[300px]">
        {calculando && (
          <div className="absolute top-4 right-4 text-tinta-suave">
            <Girador /> <span className="text-xs">Calculando...</span>
          </div>
        )}
        
        {tab === "formulario" && fase !== 3 && (
          <EstadosFinancierosIHP
            derivados={derivados}
            textos={ihpTextoCompleto}
            fase={fase === 1 ? 1 : 2}
            alCambiar={setIhp}
          />
        )}

        <div className={tab === "formulario" && fase === 3 ? "block" : "hidden"}>
          <Bloque
            titulo="Balance"
            descripcion="Se deduce de los estados financieros; para cambiarlo, edite las partidas de las fases 1 y 2."
          >
            <ResumenDerivado rotulo="Total activos corrientes" valor={derivados.totalActivosCorrientes} />
            <ResumenDerivado rotulo="Total pasivos corrientes" valor={derivados.totalPasivosCorrientes} />
            <ResumenDerivado rotulo="Total pasivos" valor={derivados.totalPasivos} />
            <ResumenDerivado rotulo="Patrimonio" valor={ihp.patrimonio} />
          </Bloque>

          <Bloque titulo="Resultados y servicio de deuda">
            <ResumenDerivado rotulo="EBITDA" valor={derivados.ebitda} />
            <ResumenDerivado rotulo="Gastos financieros, cambiarios y otros" valor={ihp.gastosFinancieros} />
            <CampoNumero
              rotulo="Ingresos mensuales"
              valor={f.ing_mensuales}
              alCambiar={(v) => set("ing_mensuales", v)}
            />
            <CampoNumero
              rotulo="Cuota estimada"
              valor={f.cuota_est}
              alCambiar={(v) => set("cuota_est", v)}
            />
          </Bloque>

          <Bloque titulo="Calificación">
            <CampoNumero
              rotulo="Matriz Kaizen (0-10)"
              valor={f.rm_score}
              alCambiar={(v) => set("rm_score", v)}
              paso="0.1"
              minimo={0}
              maximo={10}
              ayuda="Calificación cualitativa que mejora el score base."
            />
            <CampoSeleccion
              rotulo="Moneda"
              valor={f.moneda}
              opciones={MONEDAS}
              alCambiar={(v) => set("moneda", v)}
            />
            <CampoCasilla
              rotulo="Aplicar escenario de estrés"
              valor={f.estres}
              alCambiar={(v) => set("estres", v)}
              ayuda="Endurece los supuestos del cálculo."
            />
          </Bloque>

          <Bloque titulo="Condiciones y conclusiones" columnas={1}>
            <CampoTextoLargo
              rotulo="Covenants"
              valor={f.covenants}
              alCambiar={(v) => set("covenants", v)}
              marcador="Compromisos exigidos al acreditado."
              filas={2}
            />
            <CampoTextoLargo
              rotulo="Observaciones de Riesgo"
              valor={f.obs_riesgo}
              alCambiar={(v) => set("obs_riesgo", v)}
            />
          </Bloque>
        </div>
{/*ACA ESTA LO DE INDICADORES */}
        {tab === "indicadores" && scoring?.indicadores && (
          <div className="">
            <div>
            <div className={`p-4 mb-4 rounded-lg mb-4 flex items-center justify-between border-l-4 ${TARJETA_SEMAFORO[semaforoMotor(scoring.altman?.semaforo)]}`}>
              <div>
                <p className="text-xs font-bold uppercase">Z-Score</p>
                <p className="text-2xl font-black tabular-nums">{scoring.altman?.z_fmt}</p>
              </div>
              <div className="text-right">
                <p className="text-sm font-bold uppercase">{scoring?.altman?.zona as string}</p>
                <p className="text-xs opacity-80">{scoring.altman?.detalle}</p>
              </div>
            </div>

            <div className="overflow-x-auto rounded-lg border border-borde ">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-tinta-suave">
                  <tr>
                    <th className="px-4 py-2">Variable</th>
                    <th className="px-4 py-2">Descripción</th>
                    <th className="px-4 py-2 text-right">Coeficiente</th>
                    <th className="px-4 py-2 text-right">Valor</th>
                    <th className="px-4 py-2 text-right">Aporte</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-borde bg-white">
                  {scoring.altman?.componentes.map((comp, i) => (
                    <tr key={i} className="hover:bg-slate-50">
                      <td className="px-4 py-2 font-mono font-bold">{comp.clave}</td>
                      <td className="px-4 py-2">{comp.etiqueta}</td>
                      <td className="px-4 py-2 text-right font-mono tabular-nums">{comp.coeficiente}</td>
                      <td className="px-4 py-2 text-right font-mono tabular-nums">{comp.valor_fmt}</td>
                      <td className="px-4 py-2 text-right font-mono font-bold tabular-nums">{comp.aporte_fmt}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className="space-y-6 mt-6">
            {Object.entries(scoring.indicadores).map(([categoria, lista]) => {
              if (!lista || lista.length === 0) return null;
              
              console.log("indicadores", lista)

              return (
                <div key={categoria}>
                  <h4 className="text-sm font-bold text-kaizen-900 mb-2 border-b border-borde pb-1">{categoria}</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                    {lista.map((ind, i) => (
                      <div
                        key={i}
                        className={`rounded-lg border p-3 ${TARJETA_SEMAFORO[semaforoMotor(ind.semaforo)]}`}
                      >
                        <p className="text-xs font-semibold uppercase">{ind.nombre}</p>
                        <p className="mt-1 text-lg font-bold tabular-nums">
                          {ind.valor ? ((Math.trunc(ind?.valor*1000)/1000)  * 100 ).toFixed(2) + "%" :  "N/A"}
                        </p>
                        {ind.detalle && <p className="mt-1 text-[10px] opacity-90">{ind.detalle}</p>}
                        {/* El color de la tarjeta ya comunica el estado; se nombra
                            para lectores de pantalla y para quien no distingue colores. */}
                        <span className="sr-only">Estado: {ind.semaforo ?? "sin umbral"}</span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
          </div>
        )}
      </div>
      
      </fieldset>

      <div className="flex flex-wrap items-center gap-3 border-t border-borde px-5 py-5">
        {/* Navegar entre fases queda fuera del `fieldset`: en un expediente
            histórico hay que poder recorrer las tres para leerlas. */}
        {tab === "formulario" && (
          <>
            <button
              type="button"
              className={BOTON.neutro}
              disabled={fase === 1}
              onClick={() => setFase((actual) => anterior(actual))}
            >
              Anterior
            </button>
            <button
              type="button"
              className={BOTON.neutro}
              disabled={fase === 3}
              onClick={() => setFase((actual) => siguiente(actual))}
            >
              Siguiente
            </button>
          </>
        )}

        <fieldset disabled={bloqueado} className="contents">
          <button
            type="submit"
            className={BOTON.primario}
            disabled={enviando || scoring === null}
          >
            {enviando && <Girador />}
            Registrar firma de Riesgo
          </button>
          {persistencia.puedeGuardar && (
            <button
              type="button"
              className={BOTON.neutro}
              disabled={enviando || servidor.guardando}
              onClick={() => void servidor.guardar("manual")}
            >
              {servidor.guardando && <Girador />}
              Guardar evaluación
            </button>
          )}
        </fieldset>
      </div>
    </form>
  );
}

function RiesgoAutomotriz({
  claveBorrador,
  bloqueado,
  persistencia,
  scoring,
  calculando,
  enviando,
  onCalcular,
  onRegistrar,
}: {
  claveBorrador: string;
  bloqueado: boolean;
  persistencia: PersistenciaRiesgo;
  scoring: ResultadoScoring | null;
  calculando: boolean;
  enviando: boolean;
  onCalcular: (entradas: Record<string, unknown>) => Promise<void>;
  onRegistrar: (form: RiskForm) => Promise<ServiceResult<unknown>>;
}) {
  const [f, setF] = useState({
    ingreso_mensual: "0",
    gastos_mensuales: "0",
    cuota_est: "0",
    ltv_ratio: "0",
    estabilidad_laboral: "0",
    rm_score: "0",
    moneda: "USD",
    estres: false,
    covenants: "",
    obs_riesgo: "",
  });

  const set = (clave: keyof typeof f, valor: string | boolean) =>
    setF((actual) => ({ ...actual, [clave]: valor }));

  const borrador = useBorradorLocal(claveBorrador, f, (datos) =>
    setF((actual) => fundirConocidas(actual, datos)),
  );

  const aplicarServidor = (crudo: EvaluacionGuardada<EvaluacionRiesgo>) => {
    const datos = crudo as EvaluacionGuardada<EvaluacionRiesgoAuto>;
    setF((actual) => ({
      ...actual,
      ingreso_mensual: aTexto(datos.ingreso_mensual),
      gastos_mensuales: aTexto(datos.gastos_fijos),
      cuota_est: aTexto(datos.cuota_mensual),
      ltv_ratio: aTexto(datos.ltv_ratio),
      estabilidad_laboral: aTexto(datos.estabilidad_laboral),
      rm_score: aTexto(datos.kc_score),
      moneda: datos.moneda || actual.moneda,
      estres: Boolean(datos.aplicar_estres),
      covenants: datos.covenants ?? "",
      obs_riesgo: datos.obs_riesgo ?? "",
    }));
  };

  /** Hoja de trabajo con la forma exacta de `ScoringAutomotrizIn`. */
  const evaluacion = useMemo<EvaluacionRiesgoAuto>(
    () => ({
      ingreso_mensual: aNumero(f.ingreso_mensual),
      gastos_fijos: aNumero(f.gastos_mensuales),
      cuota_mensual: aNumero(f.cuota_est),
      ltv_ratio: aNumero(f.ltv_ratio),
      estabilidad_laboral: aNumero(f.estabilidad_laboral),
      aplicar_estres: f.estres,
      kc_score: aNumero(f.rm_score),
      moneda: f.moneda,
      covenants: f.covenants.trim(),
      obs_riesgo: f.obs_riesgo.trim(),
    }),
    [f],
  );

  const servidor = useEvaluacionServidor(
    claveBorrador,
    borrador,
    persistencia,
    evaluacion,
    aplicarServidor,
    bloqueado,
  );

  const fDebounced = useDebounce(f, 500);

  const entradas = useMemo(() => ({
    ingreso_mensual: aNumero(fDebounced.ingreso_mensual),
    gastos_fijos: aNumero(fDebounced.gastos_mensuales),
    cuota_mensual: aNumero(fDebounced.cuota_est),
    ltv_ratio: aNumero(fDebounced.ltv_ratio),
    estabilidad_laboral: aNumero(fDebounced.estabilidad_laboral),
    aplicar_estres: fDebounced.estres,
    kc_score: aNumero(fDebounced.rm_score),
  }), [fDebounced]);

  useEffect(() => {
    void onCalcular(entradas);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entradas]);

  const registrar = async () => {
    if (!scoring) return;
    if (persistencia.puedeGuardar && !(await servidor.guardar("firma"))) {
      return;
    }
    const form: RiskAutoForm = {
      score_f: scoring.score_final,
      rm_score: aNumero(f.rm_score),
      ingreso_mensual: aNumero(f.ingreso_mensual),
      gastos_mensuales: aNumero(f.gastos_mensuales),
      cuota_est: aNumero(f.cuota_est),
      dti_ratio: scoring.dti ?? 0,
      estabilidad_laboral: aNumero(f.estabilidad_laboral),
      estres_aplicado: f.estres,
      tasa_sugerida: scoring.tasa_sugerida,
      moneda: f.moneda,
      covenants: f.covenants.trim(),
      obs_riesgo: f.obs_riesgo.trim(),
    };
    // Solo con la firma aceptada deja de hacer falta el borrador: si el backend
    // la rechaza, lo tecleado debe seguir ahí para corregirlo y reenviar.
    const resultado = await onRegistrar(form);
    if (resultado.success) borrador.descartar();
  };

  return (
    <form
      className="rounded-xl border border-borde bg-white p-5 shadow-sm relative"
      onSubmit={(evento) => {
        evento.preventDefault();
        void registrar();
      }}
    >
      <AvisoBloqueo bloqueado={bloqueado} />
      <fieldset disabled={bloqueado} className="contents">
      {calculando && (
        <div className="absolute top-4 right-4 text-tinta-suave">
          <Girador /> <span className="text-xs">Calculando...</span>
        </div>
      )}
      <h3 className="text-sm font-semibold text-kaizen-900">
        Evaluación de Riesgo
      </h3>
      <p className="mt-1 text-xs text-tinta-suave">
        Capacidad de pago del solicitante, cobertura del vehículo y estabilidad
        laboral.
      </p>

      <div className="-mx-5 px-5 pt-2 pb-6 mb-6 border-b border-borde bg-slate-50/50">
        <ResultadoDelMotor
          scoring={scoring}
          extras={[
            {
              rotulo: "Ingreso libre",
              valor: scoring?.ingreso_libre != null ? `$${scoring.ingreso_libre.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "$0.00"
            },
            {
              rotulo: "DTI Ratio",
              valor: `${(scoring?.dti ?? 0).toFixed(2)}%`,
              delta: scoring?.tramo_dti?.delta,
              deltaColor: scoring?.tramo_dti?.delta_color as "normal" | "inverse" | undefined
            },
            {
              rotulo: "Score Cap.",
              valor: `${(scoring?.score_capacidad ?? 0).toFixed(2)}/10`
            },
            {
              rotulo: "PTI Ratio",
              valor: `${(scoring?.pti ?? 0).toFixed(1)}%`
            }
          ]}
        />

        {scoring?.tramo_pti && (
          <div
            className="mt-4 mb-2 rounded-r-lg bg-white px-4 py-2 text-sm text-kaizen-900 border-l-4 shadow-sm"
            style={{ borderColor: scoring.tramo_pti.color }}
          >
            <strong>PTI (Payment-to-Income):</strong> {(scoring.pti ?? 0).toFixed(1)}% &mdash; {scoring.tramo_pti.label}
            <span className="ml-2 text-slate-400 text-xs">
              (Verde &lt;30% &middot; Amarillo 30-40% &middot; Rojo &gt;40%)
            </span>
          </div>
        )}

        {scoring?.dti && scoring.dti > 40 && (
          <div className="mt-2 rounded-lg bg-rojo-fondo p-3 text-sm font-medium text-rojo-trazo border-l-4 border-rojo-trazo">
            ❌ DTI superior al 40%. Riesgo elevado de sobreendeudamiento.
          </div>
        )}
        {scoring?.dti && scoring.dti > 30 && scoring.dti <= 40 && (
          <div className="mt-2 rounded-lg bg-ambar-fondo p-3 text-sm font-medium text-ambar-trazo">
            ⚠️ DTI entre 30-40%. Capacidad de pago ajustada.
          </div>
        )}
      </div>

      <Bloque titulo="Capacidad de pago">
        <CampoNumero
          rotulo="Ingreso mensual"
          valor={f.ingreso_mensual}
          alCambiar={(v) => set("ingreso_mensual", v)}
        />
        <CampoNumero
          rotulo="Gastos fijos mensuales"
          valor={f.gastos_mensuales}
          alCambiar={(v) => set("gastos_mensuales", v)}
        />
        <CampoNumero
          rotulo="Cuota estimada"
          valor={f.cuota_est}
          alCambiar={(v) => set("cuota_est", v)}
        />
        <CampoNumero
          rotulo="LTV del vehículo (%)"
          valor={f.ltv_ratio}
          alCambiar={(v) => set("ltv_ratio", v)}
          minimo={0}
          ayuda="Lo calcula Legal a partir del precio y la inicial."
        />
      </Bloque>

      <Bloque titulo="Calificación">
        <CampoNumero
          rotulo="Estabilidad laboral (0-10)"
          valor={f.estabilidad_laboral}
          alCambiar={(v) => set("estabilidad_laboral", v)}
          paso="0.1"
          minimo={0}
          maximo={10}
        />
        <CampoNumero
          rotulo="Matriz Kaizen (0-10)"
          valor={f.rm_score}
          alCambiar={(v) => set("rm_score", v)}
          paso="0.1"
          minimo={0}
          maximo={10}
        />
        <CampoSeleccion
          rotulo="Moneda"
          valor={f.moneda}
          opciones={MONEDAS}
          alCambiar={(v) => set("moneda", v)}
        />
        <CampoCasilla
          rotulo="Aplicar escenario de estrés"
          valor={f.estres}
          alCambiar={(v) => set("estres", v)}
        />
      </Bloque>

      <Bloque titulo="Condiciones y conclusiones" columnas={1}>
        <CampoTextoLargo
          rotulo="Covenants"
          valor={f.covenants}
          alCambiar={(v) => set("covenants", v)}
          filas={2}
        />
        <CampoTextoLargo
          rotulo="Observaciones de Riesgo"
          valor={f.obs_riesgo}
          alCambiar={(v) => set("obs_riesgo", v)}
        />
      </Bloque>

      <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-borde pt-5">
        <button
          type="submit"
          className={BOTON.primario}
          disabled={enviando || scoring === null}
        >
          {enviando && <Girador />}
          Registrar firma de Riesgo
        </button>
        {persistencia.puedeGuardar && (
          <button
            type="button"
            className={BOTON.neutro}
            disabled={enviando || servidor.guardando}
            onClick={() => void servidor.guardar("manual")}
          >
            {servidor.guardando && <Girador />}
            Guardar evaluación
          </button>
        )}
      </div>
      </fieldset>
    </form>
  );
}

/**
 * Cartel de solo lectura.
 *
 * Aparece cuando la etapa ya está firmada o el Comité se ha pronunciado: el
 * formulario queda visible para consultar lo evaluado, pero no admite cambios.
 */
function AvisoBloqueo({ bloqueado }: { bloqueado: boolean }) {
  if (!bloqueado) return null;
  return (
    <p className="border-b border-borde bg-ambar-fondo px-5 py-3 text-sm text-ambar-trazo">
      Evaluación firmada: el formulario queda en solo lectura. Para rehacerla,
      el expediente debe devolverse a la etapa de Crédito.
    </p>
  );
}

/** Texto de un campo a partir de lo que devuelve la API (número o `Decimal` en cadena). */
function aTexto(valor: unknown): string {
  const numero = typeof valor === "string" ? Number(valor) : valor;
  return typeof numero === "number" && Number.isFinite(numero)
    ? String(numero)
    : "0";
}

/** Cadencia del autoguardado periódico. */
const INTERVALO_AUTOGUARDADO_MS = 60_000;

interface EstadoServidor {
  guardando: boolean;
  /**
   * Guarda ya la hoja actual, esté o no modificada; devuelve si la base la
   * aceptó. `modo` distingue el botón (`manual`) del guardado previo a la
   * firma (`firma`), que no anuncia su éxito porque ya lo hace la firma.
   */
  guardar: (modo: Exclude<ModoGuardado, "automatico">) => Promise<boolean>;
}

/**
 * Carga, guardado y autoguardado de la hoja de trabajo en la base de datos.
 *
 * Con `soloLectura` la carga sigue haciéndose —el expediente histórico se
 * consulta con sus cifras— pero no se programa ningún autoguardado.
 *
 * **Carga.** Al montar pide la evaluación guardada. Si existe, prevalece: el
 * borrador local cede (`adoptar`) y se aplican los datos de la base. Si no
 * existe o la consulta falla, el formulario sigue con el borrador local.
 *
 * **Autoguardado.** Un `setInterval` revisa la hoja cada
 * `INTERVALO_AUTOGUARDADO_MS` y la sube solo si difiere de la última versión
 * que la base confirmó. La comparación es sobre el JSON exacto que viaja —ya
 * derivado con `normalizarEntradas`—, así que un minuto sin cambios reales, o
 * con una edición que se deshizo, no genera escrituras. Con la carga aún en
 * curso no se sube nada, para no pisar la base con un formulario que todavía
 * no la ha leído. El intervalo es fijo: teclear no lo reinicia, de modo que
 * una sesión de edición larga se guarda igualmente cada minuto.
 *
 * **Avisos.** El éxito del guardado automático se anuncia con un aviso
 * emergente que se retira solo. Un fallo automático se avisa una vez, no en
 * cada minuto que siga fallando; el siguiente éxito rearma el aviso.
 *
 * **Orden.** Todos los guardados pasan por una cola: uno lento no puede llegar
 * después de otro posterior y dejar en la base una versión antigua.
 *
 * **Salida.** Al desmontar —cambiar de pestaña— se sube lo pendiente. Si no, lo
 * tecleado desde el último ciclo quedaría solo en el borrador local, y al
 * volver la base, más antigua, lo pisaría.
 */
function useEvaluacionServidor(
  clave: string,
  borrador: EstadoBorrador,
  persistencia: PersistenciaRiesgo,
  evaluacion: EvaluacionRiesgo,
  aplicar: (datos: EvaluacionGuardada<EvaluacionRiesgo>) => void,
  soloLectura: boolean,
): EstadoServidor {
  const [guardando, setGuardando] = useState(false);

  /** Ya se avisó de un fallo automático que aún no se ha resuelto. */
  const falloAvisadoRef = useRef(false);
  const actualRef = useRef(evaluacion);
  const persistenciaRef = useRef(persistencia);
  /** JSON del formulario recién montado, antes de restaurar nada. */
  const inicialRef = useRef<string | null>(null);
  /** JSON de la última versión que la base tiene. `null`: carga sin resolver. */
  const sincronizadoRef = useRef<string | null>(null);
  /** El próximo render trae los datos de la base: su JSON es la referencia. */
  const capturarRef = useRef(false);
  const colaRef = useRef<Promise<unknown>>(Promise.resolve());

  useEffect(() => {
    actualRef.current = evaluacion;
    persistenciaRef.current = persistencia;
    const json = JSON.stringify(evaluacion);
    if (inicialRef.current === null) inicialRef.current = json;
    if (capturarRef.current) {
      capturarRef.current = false;
      sincronizadoRef.current = json;
    }
  });

  const ejecutar = useCallback((modo: ModoGuardado): Promise<boolean> => {
    const tarea = colaRef.current.then(async () => {
      const datos = actualRef.current;
      const json = JSON.stringify(datos);
      // Solo el automático se salta una hoja sin cambios; el botón y la firma
      // guardan siempre.
      if (modo === "automatico" && json === sincronizadoRef.current) return true;

      const automatico = modo === "automatico";
      setGuardando(true);
      const resultado = await persistenciaRef.current.guardar(datos, {
        modo,
        avisarError: !automatico || !falloAvisadoRef.current,
      });
      setGuardando(false);

      if (resultado.success) {
        sincronizadoRef.current = json;
        falloAvisadoRef.current = false;
        return true;
      }
      if (automatico) falloAvisadoRef.current = true;
      return false;
    });
    colaRef.current = tarea;
    return tarea;
  }, []);

  /** Autoguardado admitido y con cambios respecto de la base. */
  const pendiente = useCallback(
    () =>
      persistenciaRef.current.puedeGuardar &&
      sincronizadoRef.current !== null &&
      JSON.stringify(actualRef.current) !== sincronizadoRef.current,
    [],
  );

  // Carga, una vez por expediente.
  useEffect(() => {
    const controlador = new AbortController();
    sincronizadoRef.current = null;

    void persistenciaRef.current.cargar(controlador.signal).then((resultado) => {
      if (controlador.signal.aborted) return;
      if (resultado.success && resultado.data) {
        borrador.adoptar();
        aplicar(resultado.data);
        capturarRef.current = true;
        return;
      }
      // Sin evaluación en la base: la referencia es el formulario vacío. Así un
      // expediente que solo se abre no crea una fila, y un borrador local
      // restaurado se sube en el siguiente ciclo del intervalo.
      sincronizadoRef.current = inicialRef.current;
    });

    return () => controlador.abort();
    // Una carga por expediente: `borrador` y `aplicar` cambian en cada render y
    // volver a pedir con ellos pisaría lo que el analista teclea después.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clave]);

  // Autoguardado periódico: un único intervalo por montaje. `pendiente` y
  // `ejecutar` son estables y leen el estado vigente por referencia, así que el
  // intervalo no se reinicia al teclear.
  //
  // En solo lectura no se programa siquiera: el temporizador no llega a existir
  // mientras el expediente esté firmado o con dictamen, y si pasa a estarlo se
  // cancela en la limpieza del efecto.
  useEffect(() => {
    if (soloLectura) return;
    const intervalo = window.setInterval(() => {
      if (pendiente()) void ejecutar("automatico");
    }, INTERVALO_AUTOGUARDADO_MS);
    return () => window.clearInterval(intervalo);
  }, [soloLectura, pendiente, ejecutar]);

  // Lo pendiente sube al desmontar, salvo en solo lectura: ahí no hay nada que
  // subir y el backend lo rechazaría.
  useEffect(() => {
    if (soloLectura) return undefined;
    return () => {
      if (pendiente()) void ejecutar("automatico");
    };
  }, [soloLectura, pendiente, ejecutar]);

  const guardar = useCallback(
    (modo: Exclude<ModoGuardado, "automatico">) => ejecutar(modo),
    [ejecutar],
  );

  return { guardando, guardar };
}

/**
 * Magnitud derivada mostrada dentro de un bloque de campos.
 *
 * Comparte la altura y el ritmo de `CampoNumero` para que la rejilla no se
 * desalinee, pero sin control de entrada: lo que se deduce de los estados
 * financieros no se corrige aquí.
 */
function ResumenDerivado({ rotulo, valor }: { rotulo: string; valor: number }) {
  return (
    <div>
      <span className="text-xs font-semibold tracking-wide text-tinta-suave uppercase">
        {rotulo}
      </span>
      <output
        className={`mt-1.5 block rounded-lg border border-kaizen-600/20 bg-kaizen-100/40 px-3 py-2 text-sm font-semibold tabular-nums ${
          valor < 0 ? "text-rojo-trazo" : "text-kaizen-900"
        }`}
      >
        {new Intl.NumberFormat("es-VE", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }).format(Number.isFinite(valor) ? valor : 0)}
      </output>
      <span className="mt-1 block text-xs text-tinta-suave">Derivado</span>
    </div>
  );
}
