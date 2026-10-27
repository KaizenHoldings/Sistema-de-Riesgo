"use client";

/**
 * Estados financieros IHP del expediente corporativo.
 *
 * Distingue visualmente dos clases de partida: las que se teclean, con su campo
 * editable, y las que se deducen, sobre fondo azul institucional y sin control
 * de entrada. Un campo derivado que pareciera editable invitaría a cuadrar el
 * balance «a mano», que es justo lo que esta pantalla evita.
 *
 * Todo se recalcula en el mismo render en que cambia una entrada: no hay efecto
 * ni estado intermedio, así que no existe un instante en el que lo derivado
 * contradiga a lo tecleado.
 */

import { CampoNumero } from "@/components/sections/campos";
import type {
  EntradasIHP,
  EstadosFinancierosIHP as Derivados,
} from "@/business/finanzas/estadosFinancieros";

const MONEDA = new Intl.NumberFormat("es-VE", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function formatear(valor: number): string {
  return Number.isFinite(valor) ? MONEDA.format(valor) : "—";
}

/** Fila de una partida derivada. `enfasis` la marca como total de la sección. */
function Derivado({
  rotulo,
  valor,
  formula,
  enfasis = false,
}: {
  rotulo: string;
  valor: number;
  formula: string;
  enfasis?: boolean;
}) {
  return (
    <div
      className={`flex items-baseline justify-between gap-4 rounded-lg border px-4 py-3 ${
        enfasis
          ? "border-kaizen-800/25 bg-kaizen-800/10"
          : "border-kaizen-600/20 bg-kaizen-100/40"
      }`}
    >
      <span className="min-w-0">
        <span
          className={`block text-xs font-semibold tracking-wide uppercase ${
            enfasis ? "text-kaizen-900" : "text-kaizen-800"
          }`}
        >
          {rotulo}
        </span>
        <span className="block text-[11px] text-tinta-suave">{formula}</span>
      </span>
      {/*
        El color se elige una sola vez. Encadenar `text-kaizen-900` y
        `text-rojo-trazo` en el mismo atributo no funciona: entre dos utilidades
        de igual especificidad gana la que va después en la hoja de estilos, no
        la que va después en el atributo, así que el negativo podía quedarse azul.
      */}
      <output
        className={`shrink-0 tabular-nums ${
          enfasis ? "text-lg font-bold" : "text-base font-semibold"
        } ${
          valor < 0
            ? "text-rojo-trazo"
            : enfasis
              ? "text-kaizen-900"
              : "text-kaizen-800"
        }`}
      >
        {formatear(valor)}
      </output>
    </div>
  );
}

function Seccion({
  titulo,
  descripcion,
  children,
}: {
  titulo: string;
  descripcion: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mt-8 first:mt-0">
      <h4 className="border-b border-borde pb-2 text-sm font-bold text-kaizen-900 text-xl">
        {titulo}
      </h4>
      <p className="mt-1 text-xs text-tinta-suave">{descripcion}</p>
      <div className="mt-4 space-y-4">{children}</div>
    </section>
  );
}

/**
 * Subencabezado de grupo dentro de una hoja.
 *
 * La plantilla separa el balance en ACTIVOS, PASIVOS y PATRIMONIO, y el flujo en
 * sus tres tipos de actividad. Reproducir esas franjas ayuda a seguir la lectura
 * en paralelo con el Excel, que es como trabaja el analista.
 */
function Grupo({ children }: { children: React.ReactNode }) {
  return (
    <p className="mt-6 border-b border-kaizen-800/20 pb-1 text-md font-bold tracking-wider text-kaizen-800 uppercase first:mt-0">
      {children}
    </p>
  );
}

function Entradas({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">{children}</div>;
}

function Derivadas({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">{children}</div>;
}

export function EstadosFinancierosIHP({
  derivados,
  textos,
  fase,
  alCambiar,
}: {
  derivados: Derivados;
  /** Texto en crudo de cada campo, para no reformatear mientras se escribe. */
  textos: Record<keyof EntradasIHP, string>;
  /**
   * Fase del asistente que se está mostrando.
   *
   * 1 reúne lo que define el tamaño del negocio —ventas, costo de ventas y el
   * balance entero—; 2, lo que explica su resultado y su caja —gastos,
   * depreciación, impuesto y el flujo de efectivo—. Partirlo no cambia ningún
   * cálculo: las derivadas salen siempre de `derivarEstados` sobre el estado
   * completo, así que las de una fase reflejan también lo tecleado en la otra.
   */
  fase: 1 | 2;
  alCambiar: (clave: keyof EntradasIHP, valor: string) => void;
}) {
  const campo = (clave: keyof EntradasIHP, rotulo: string, ayuda?: string) => (
    <CampoNumero
      rotulo={rotulo}
      valor={textos[clave]}
      alCambiar={(v) => alCambiar(clave, v)}
      ayuda={ayuda}
    />
  );

  return (
    <div>
      <p className="rounded-lg border border-kaizen-600/20 bg-kaizen-100/40 px-4 py-3 text-xs text-tinta-suave">
        Los costes, gastos, la depreciación, el impuesto y el consumo de capital
        de trabajo se capturan <strong>en positivo</strong> y las fórmulas los
        restan. Un valor negativo sigue siendo válido y significa lo contrario
        —una devolución, una recuperación—: el signo que usted escriba se
        respeta. Los campos sobre fondo azul se calculan solos y no se editan.
      </p>

      {fase === 1 && (
        <>
      <Seccion
        titulo="Estado de Resultados — Ingresos y costos"
        descripcion="Cifras en USD miles. El margen bruto del período: lo que entra por ventas y lo que cuesta producirlo."
      >
        <Entradas>
          {campo("ingresos", "Ingresos por ventas")}
          {campo("costoVentas", "Costo de bienes vendidos (COGS)", "Importe positivo; se resta.")}
        </Entradas>
        <Derivadas>
          <Derivado
            rotulo="Utilidad bruta"
            valor={derivados.utilidadBruta}
            formula="Ingresos − Costo de ventas"
          />
        </Derivadas>
      </Seccion>

      <Seccion
        titulo="Balance General — IHP"
        descripcion="Cifras en USD miles. Activos, pasivos y patrimonio, con chequeo automático de cuadre contable."
      >
        <Grupo>ACTIVOS</Grupo>
        <Entradas>
          {campo("caja", "Caja y equivalentes")}
          {campo("cuentasPorCobrar", "Cuentas por cobrar comerciales, netas")}
          {campo("inventarios", "Inventarios")}
          {campo("otrosActivosCorrientes", "Otros activos corrientes")}
        </Entradas>
        <Derivadas>
          <Derivado
            rotulo="Total activos corrientes"
            valor={derivados.totalActivosCorrientes}
            formula="Caja + CxC + Inventarios + Otros corrientes"
          />
        </Derivadas>

        <Entradas>
          {campo("activosFijosNetos", "PP&E neto (propiedad, planta y equipo)")}
          {campo("otrosActivosNoCorrientes", "Otros activos no corrientes")}
        </Entradas>
        <Derivadas>
          <Derivado
            rotulo="Total activos"
            valor={derivados.totalActivos}
            formula="Corrientes + Fijos netos + Otros no corrientes"
            enfasis
          />
        </Derivadas>

        <Grupo>PASIVOS</Grupo>
        <Entradas>
          {campo("cuentasPorPagar", "Cuentas por pagar a proveedores")}
          {campo("deudaCortoPlazo", "Deuda financiera de corto plazo")}
          {campo("otrosPasivosCorrientes", "Otros pasivos corrientes (nómina, tributos, contingencias)")}
        </Entradas>
        <Derivadas>
          <Derivado
            rotulo="Total pasivos corrientes"
            valor={derivados.totalPasivosCorrientes}
            formula="CxP + Deuda CP + Otros corrientes"
          />
        </Derivadas>

        <Entradas>
          {campo("deudaLargoPlazo", "Deuda financiera de largo plazo")}
          {campo("otrosPasivosNoCorrientes", "Otros pasivos no corrientes")}
        </Entradas>

        <Grupo>PATRIMONIO</Grupo>
        <Entradas>{campo("patrimonio", "Patrimonio")}</Entradas>
        <Derivadas>
          <Derivado
            rotulo="Total pasivos"
            valor={derivados.totalPasivos}
            formula="Corrientes + Deuda LP + Otros no corrientes"
          />
          <Derivado
            rotulo="Total pasivo y patrimonio"
            valor={derivados.totalPasivoPatrimonio}
            formula="Total pasivos + Total patrimonio"
            enfasis
          />
        </Derivadas>

        <CuadreContable
          valor={derivados.cuadreContable}
          cuadrado={derivados.cuadrado}
        />
      </Seccion>
        </>
      )}

      {fase === 2 && (
        <>
      <Seccion
        titulo="Estado de Resultados — Gastos, depreciación e impuesto"
        descripcion="Cifras en USD miles. De la utilidad bruta a la utilidad neta, con el EBITDA que alimenta el motor de riesgo."
      >
        <Entradas>
          {campo("gastosVentaAdmin", "Gastos administrativos, comerciales y operativos", "Importe positivo; se resta.")}
          {campo("depreciacionAmortizacion", "Depreciación y amortización", "Importe positivo; se resta del EBIT y se devuelve al EBITDA. La plantilla IHP la captura en negativo.")}
          {campo(
            "provisionPerdidasCrediticias",
            "Provisión para pérdidas crediticias",
            "Importe positivo; se resta.",
          )}
          {campo(
            "costosContingencias",
            "Costos de contingencias laborales y paralizaciones",
            "Importe positivo; se resta.",
          )}
          {campo(
            "gastosFinancieros",
            "Gastos financieros, cambiarios y otros",
            "Importe positivo; se resta.",
          )}
        </Entradas>
        <Derivadas>
          <Derivado
            rotulo="Resultado operativo (EBIT)"
            valor={derivados.ebit}
            formula="Utilidad bruta − Gastos admin. − Provisión − Contingencias − D&A"
          />
          <Derivado
            rotulo="Resultado antes de impuesto"
            valor={derivados.resultadoAntesImpuesto}
            formula="EBIT − Gastos financieros"
          />
        </Derivadas>

        <Entradas>
          {campo("impuestoRenta", "Impuesto estimado", "Importe positivo; se resta.")}
        </Entradas>
        <Derivadas>
          <Derivado
            rotulo="Utilidad neta"
            valor={derivados.utilidadNeta}
            formula="Resultado antes de impuesto − Impuesto"
            enfasis
          />
          <Derivado
            rotulo="EBITDA (EBIT + Depreciación y amortización)"
            valor={derivados.ebitda}
            formula="EBIT + Depreciación y amortización"
            enfasis
          />
        </Derivadas>
      </Seccion>

      <Seccion
        titulo="Flujo de Efectivo (método simplificado) — IHP"
        descripcion="Cifras en USD miles. Utilidad neta más partidas no monetarias, con los cambios en capital de trabajo."
      >
        <p className="rounded-lg border border-kaizen-600/20 bg-kaizen-100/40 px-4 py-3 text-xs text-tinta-suave">
          Las <strong>actividades operativas se calculan solas</strong> con las
          fórmulas de la plantilla: los cambios de capital de trabajo salen de
          comparar el balance actual con los saldos del período anterior, y la
          línea de conciliación cierra la diferencia con la caja del balance. Las
          actividades de inversión y financiamiento se introducen con el signo de
          su efecto sobre la caja.
        </p>

        <Grupo>Valores de referencia del período anterior (USD miles)</Grupo>
        <Entradas>
          {campo("cxcAnterior", "CxC neta", "Cuentas por cobrar al cierre del período anterior.")}
          {campo("inventariosAnterior", "Inventarios", "Inventarios al cierre del período anterior.")}
          {campo("cxpAnterior", "CxP", "Cuentas por pagar al cierre del período anterior.")}
          {campo("cajaInicial", "Caja inicial", "Caja al cierre del período anterior.")}
        </Entradas>

        <Grupo>ACTIVIDADES OPERATIVAS</Grupo>
        <Derivadas>
          <Derivado
            rotulo="Utilidad neta"
            valor={derivados.utilidadNeta}
            formula="= Utilidad neta del Estado de Resultados"
          />
          <Derivado
            rotulo="Más: depreciación y amortización"
            valor={derivados.depreciacionFlujo}
            formula="= Depreciación y amortización del Estado de Resultados"
          />
          <Derivado
            rotulo="Menos: cambio en cuentas por cobrar (aumento resta)"
            valor={derivados.cambioCuentasPorCobrar}
            formula="= −(CxC actual − CxC anterior)"
          />
          <Derivado
            rotulo="Menos: cambio en inventarios (aumento resta)"
            valor={derivados.cambioInventarios}
            formula="= −(Inventarios actual − Inventarios anterior)"
          />
          <Derivado
            rotulo="Más: cambio en cuentas por pagar (aumento suma)"
            valor={derivados.cambioCuentasPorPagar}
            formula="= CxP actual − CxP anterior"
          />
          <Derivado
            rotulo="Otros cambios en capital de trabajo y partidas de conciliación (fórmula de cierre)"
            valor={derivados.otrosCambiosCapitalTrabajo}
            formula="= (Caja BG − Caja inicial) − las cinco líneas anteriores − Inversión − Financiamiento"
          />
        </Derivadas>
        <Derivadas>
          <Derivado
            rotulo="Flujo neto de actividades operativas"
            valor={derivados.flujoOperativo}
            formula="= Suma de las seis líneas operativas"
            enfasis
          />
        </Derivadas>

        <Grupo>ACTIVIDADES DE INVERSIÓN</Grupo>
        <Entradas>
          {campo("capexMantenimiento", "Capex de mantenimiento", "Negativo si sale caja.")}
          {campo("capexExpansion", "Capex de expansión", "Negativo si sale caja.")}
        </Entradas>
        <Derivadas>
          <Derivado
            rotulo="Flujo neto de actividades de inversión"
            valor={derivados.flujoInversion}
            formula="Capex de mantenimiento + Capex de expansión"
            enfasis
          />
        </Derivadas>

        <Grupo>ACTIVIDADES DE FINANCIAMIENTO</Grupo>
        <Entradas>
          {campo(
            "deudaNuevaAmortizacion",
            "Deuda nueva / (amortización)",
            "Positivo si se toma deuda, negativo si se amortiza.",
          )}
          {campo(
            "dividendosRetiros",
            "Dividendos y retiros a accionistas",
            "Negativo: sale caja hacia los accionistas.",
          )}
        </Entradas>
        <Derivadas>
          <Derivado
            rotulo="Flujo neto de actividades de financiamiento"
            valor={derivados.flujoFinanciamiento}
            formula="Deuda nueva / (amortización) + Dividendos y retiros"
            enfasis
          />
        </Derivadas>

        <Derivadas>
          <Derivado
            rotulo="Variación neta de caja"
            valor={derivados.variacionNetaCaja}
            formula="Operativas + Inversión + Financiamiento"
          />
          <Derivado
            rotulo="Caja final (debe coincidir con BG_3Años)"
            valor={derivados.cajaFinal}
            formula="Caja inicial + Variación neta"
            enfasis
          />
        </Derivadas>

        <ChequeoCaja
          valor={derivados.chequeoCajaBalance}
          conciliada={derivados.cajaConciliada}
        />
      </Seccion>
        </>
      )}
    </div>
  );
}

/**
 * Aviso del cuadre contable.
 *
 * Se muestra siempre, cuadre o no: dar por bueno un balance en silencio deja al
 * analista sin señal de que la comprobación llegó a hacerse.
 */
function CuadreContable({
  valor,
  cuadrado,
}: {
  valor: number;
  cuadrado: boolean;
}) {
  return (
    <div
      role={cuadrado ? undefined : "alert"}
      className={`flex flex-wrap items-center justify-between gap-3 rounded-lg border-l-4 px-4 py-3 ${
        cuadrado
          ? "border-l-verde-trazo bg-verde-fondo"
          : "border-l-rojo-trazo bg-rojo-fondo"
      }`}
    >
      <div className="min-w-0">
        <p
          className={`text-sm font-bold ${
            cuadrado ? "text-verde-trazo" : "text-rojo-trazo"
          }`}
        >
          Estado del cuadre contable: {cuadrado ? "Cuadrado" : "Descuadrado"}
        </p>
        <p
          className={`mt-0.5 text-xs ${
            cuadrado ? "text-verde-trazo/90" : "text-rojo-trazo/90"
          }`}
        >
          Chequeo: Total activos - (Total pasivos + Patrimonio)
          {cuadrado
            ? ". El activo coincide con el pasivo más el patrimonio."
            : ". Revise las partidas antes de calificar: el motor tomará cifras inconsistentes."}
        </p>
      </div>
      <output
        className={`shrink-0 text-xl font-black tabular-nums ${
          cuadrado ? "text-verde-trazo" : "text-rojo-trazo"
        }`}
      >
        {formatear(valor)}
      </output>
    </div>
  );
}

/**
 * Chequeo de la caja contra el balance.
 *
 * La plantilla cierra el flujo comprobando que la caja final coincide con la que
 * declara el Balance General. Un descuadre aquí no invalida el scoring —el motor
 * no usa el flujo—, pero delata que uno de los dos estados está mal transcrito.
 */
function ChequeoCaja({
  valor,
  conciliada,
}: {
  valor: number;
  conciliada: boolean;
}) {
  return (
    <div
      role={conciliada ? undefined : "alert"}
      className={`mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border-l-4 px-4 py-3 ${
        conciliada
          ? "border-l-verde-trazo bg-verde-fondo"
          : "border-l-ambar-trazo bg-ambar-fondo"
      }`}
    >
      <div className="min-w-0">
        <p
          className={`text-sm font-bold ${
            conciliada ? "text-verde-trazo" : "text-ambar-trazo"
          }`}
        >
          Chequeo vs. Balance General (diferencia)
        </p>
        <p
          className={`mt-0.5 text-xs ${
            conciliada ? "text-verde-trazo/90" : "text-ambar-trazo/90"
          }`}
        >
          {conciliada
            ? "La caja final del flujo coincide con la del balance."
            : "La caja final del flujo no coincide con «Caja y equivalentes» del balance: revise la transcripción de uno de los dos estados."}
        </p>
      </div>
      <output
        className={`shrink-0 text-xl font-black tabular-nums ${
          conciliada ? "text-verde-trazo" : "text-ambar-trazo"
        }`}
      >
        {formatear(valor)}
      </output>
    </div>
  );
}
