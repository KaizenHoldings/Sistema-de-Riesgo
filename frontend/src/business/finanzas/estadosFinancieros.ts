/**
 * Estados financieros IHP: derivación de los campos calculados.
 *
 * Funciones puras, sin React ni transporte: reciben las partidas que teclea el
 * analista y devuelven las que se deducen de ellas. Al no depender de nada más,
 * el mismo cálculo sirve para pintar la pantalla y para componer el cuerpo que
 * viaja al motor de riesgo, sin riesgo de que las dos cosas discrepen.
 *
 * **Convención de signos.** Los costes, gastos, la depreciación, el impuesto y
 * el consumo de capital de trabajo se capturan como **magnitudes positivas** y
 * las fórmulas los **restan** explícitamente. Es la convención natural de quien
 * transcribe un estado financiero —«costo de ventas: 600.000», no «−600.000»— y
 * elimina el error de teclear un gasto sin signo y ver el margen inflado.
 *
 * Un valor negativo en una de esas partidas sigue siendo válido y significa lo
 * contrario: una devolución, una recuperación de impuesto o una liberación de
 * capital de trabajo. Por eso el signo del usuario se respeta y nunca se fuerza
 * a positivo.
 *
 * Las tres partidas que sí son netas y admiten cualquier signo de forma natural
 * —ingresos, flujo de inversión y flujo de financiamiento— se suman tal cual.
 */

/** Partidas que el analista introduce a mano. */
export interface EntradasIHP {
  // ── Estado de resultados ──
  /** Neto del período. */
  ingresos: number;
  /** Magnitudes positivas: se restan. */
  costoVentas: number;
  gastosVentaAdmin: number;
  provisionPerdidasCrediticias: number;
  costosContingencias: number;
  depreciacionAmortizacion: number;
  gastosFinancieros: number;
  impuestoRenta: number;

  // ── Balance: activo ──
  caja: number;
  cuentasPorCobrar: number;
  inventarios: number;
  otrosActivosCorrientes: number;
  activosFijosNetos: number;
  otrosActivosNoCorrientes: number;

  // ── Balance: pasivo y patrimonio ──
  cuentasPorPagar: number;
  deudaCortoPlazo: number;
  otrosPasivosCorrientes: number;
  deudaLargoPlazo: number;
  otrosPasivosNoCorrientes: number;
  patrimonio: number;

  // ── Flujo de efectivo ──
  /**
   * Saldos del período anterior («Valores de referencia» de la plantilla).
   *
   * Las actividades operativas ya no se teclean: la plantilla calcula los
   * cambios de capital de trabajo por diferencia entre el balance actual y el
   * anterior, y estos son los tres saldos previos que necesita esa diferencia.
   */
  cxcAnterior: number;
  inventariosAnterior: number;
  cxpAnterior: number;

  /** Actividades de inversión, negativas si sale caja. */
  capexMantenimiento: number;
  capexExpansion: number;

  /** Actividades de financiamiento, negativas si sale caja. */
  deudaNuevaAmortizacion: number;
  dividendosRetiros: number;

  cajaInicial: number;
}

/** Partidas que se deducen de las anteriores. Ninguna se teclea. */
export interface EstadosFinancierosIHP {
  // Estado de resultados
  utilidadBruta: number;
  ebit: number;
  resultadoAntesImpuesto: number;
  utilidadNeta: number;
  ebitda: number;

  // Balance
  totalActivosCorrientes: number;
  totalActivos: number;
  totalPasivosCorrientes: number;
  totalPasivos: number;
  totalPasivoPatrimonio: number;
  /** Activos menos pasivo más patrimonio. Debe ser cero. */
  cuadreContable: number;
  cuadrado: boolean;

  // Flujo de efectivo
  /**
   * Depreciación tal y como entra en el flujo.
   *
   * Es la misma partida del estado de resultados y por eso no se vuelve a
   * teclear: la plantilla la repite como fila propia y aquí se expone derivada.
   */
  depreciacionFlujo: number;
  cambioCuentasPorCobrar: number;
  cambioInventarios: number;
  cambioCuentasPorPagar: number;
  /** Partida de cierre de la plantilla: cuadra la caja con el balance. */
  otrosCambiosCapitalTrabajo: number;
  cambiosCapitalTrabajo: number;
  flujoOperativo: number;
  flujoInversion: number;
  flujoFinanciamiento: number;
  variacionNetaCaja: number;
  cajaFinal: number;
  /** Caja final del flujo menos la caja del balance. Debe ser cero. */
  chequeoCajaBalance: number;
  cajaConciliada: boolean;

  // Magnitudes derivadas que consume el motor de riesgo
  deudaFinancieraTotal: number;
}

export const ENTRADAS_IHP_VACIAS: EntradasIHP = {
  ingresos: 0,
  costoVentas: 0,
  gastosVentaAdmin: 0,
  provisionPerdidasCrediticias: 0,
  costosContingencias: 0,
  depreciacionAmortizacion: 0,
  gastosFinancieros: 0,
  impuestoRenta: 0,
  caja: 0,
  cuentasPorCobrar: 0,
  inventarios: 0,
  otrosActivosCorrientes: 0,
  activosFijosNetos: 0,
  otrosActivosNoCorrientes: 0,
  cuentasPorPagar: 0,
  deudaCortoPlazo: 0,
  otrosPasivosCorrientes: 0,
  deudaLargoPlazo: 0,
  otrosPasivosNoCorrientes: 0,
  patrimonio: 0,
  cxcAnterior: 0,
  inventariosAnterior: 0,
  cxpAnterior: 0,
  capexMantenimiento: 0,
  capexExpansion: 0,
  deudaNuevaAmortizacion: 0,
  dividendosRetiros: 0,
  cajaInicial: 0,
};

/**
 * Tolerancia del cuadre contable, en unidades monetarias.
 *
 * Las sumas en coma flotante dejan residuos del orden de 1e-10, así que exigir
 * un cero exacto marcaría en rojo balances que están perfectamente cuadrados.
 * Medio céntimo es holgado para el residuo y estricto para un descuadre real.
 */
export const TOLERANCIA_CUADRE = 0.005;

/**
 * Completa y sanea las entradas antes de derivar.
 *
 * Cualquier partida ausente o no finita entra como cero. Sin esto, una sola
 * clave que falte —por ejemplo en un formulario montado antes de que se añadiera
 * ese campo, cuyo estado conserva la recarga en caliente de `next dev`— vale
 * `undefined`, contamina toda la aritmética con `NaN` y deja la conciliación y
 * la caja final sin valor, con el chequeo contra el balance en alerta.
 */
export function normalizarEntradas(
  entrada: Partial<Record<keyof EntradasIHP, unknown>>,
): EntradasIHP {
  const limpio = { ...ENTRADAS_IHP_VACIAS };
  for (const clave of Object.keys(ENTRADAS_IHP_VACIAS) as Array<keyof EntradasIHP>) {
    const valor = Number(entrada[clave]);
    limpio[clave] = Number.isFinite(valor) ? valor : 0;
  }
  return limpio;
}

export function derivarEstados(
  entrada: Partial<Record<keyof EntradasIHP, unknown>>,
): EstadosFinancierosIHP {
  const e = normalizarEntradas(entrada);
  // ── Estado de resultados ──
  const utilidadBruta = e.ingresos - e.costoVentas;
  const ebit =
    utilidadBruta -
    e.gastosVentaAdmin -
    e.provisionPerdidasCrediticias -
    e.costosContingencias -
    e.depreciacionAmortizacion;
  const resultadoAntesImpuesto = ebit - e.gastosFinancieros;
  const utilidadNeta = resultadoAntesImpuesto - e.impuestoRenta;
  // La depreciación se restó al llegar al EBIT: sumarla lo devuelve al EBITDA.
  const ebitda = ebit + e.depreciacionAmortizacion;

  // ── Balance ──
  const totalActivosCorrientes =
    e.caja + e.cuentasPorCobrar + e.inventarios + e.otrosActivosCorrientes;
  const totalActivos =
    totalActivosCorrientes + e.activosFijosNetos + e.otrosActivosNoCorrientes;
  const totalPasivosCorrientes =
    e.cuentasPorPagar + e.deudaCortoPlazo + e.otrosPasivosCorrientes;
  const totalPasivos =
    totalPasivosCorrientes + e.deudaLargoPlazo + e.otrosPasivosNoCorrientes;
  const totalPasivoPatrimonio = totalPasivos + e.patrimonio;
  const cuadreContable = totalActivos - totalPasivoPatrimonio;

  // ── Flujo de efectivo ──
  // Réplica literal de la hoja Flujo_3Años. La plantilla captura la
  // depreciación en negativo en ER_3Años y la devuelve con «=-ER!C12»; aquí se
  // captura en positivo, así que el mismo efecto es sumarla tal cual.
  const depreciacionFlujo = e.depreciacionAmortizacion; //      C11 = -ER!C12

  // Cambios de capital de trabajo por diferencia de balances.
  const cambioCuentasPorCobrar = -(e.cuentasPorCobrar - e.cxcAnterior); // C12
  const cambioInventarios = -(e.inventarios - e.inventariosAnterior); //  C13
  const cambioCuentasPorPagar = e.cuentasPorPagar - e.cxpAnterior; //    C14

  const flujoInversion = e.capexMantenimiento + e.capexExpansion; //     C21
  const flujoFinanciamiento = e.deudaNuevaAmortizacion + e.dividendosRetiros; // C26

  // C15, fórmula de cierre: lo que falta para que la caja del flujo llegue
  // exactamente a la del balance.
  const otrosCambiosCapitalTrabajo =
    (e.caja -
    e.cajaInicial) -
    utilidadNeta -
    depreciacionFlujo -
    cambioCuentasPorCobrar -
    cambioInventarios -
    cambioCuentasPorPagar -
    -Math.abs(flujoInversion) -
    -Math.abs(flujoFinanciamiento);

  const cambiosCapitalTrabajo =
    cambioCuentasPorCobrar +
    cambioInventarios +
    cambioCuentasPorPagar +
    otrosCambiosCapitalTrabajo;

  const flujoOperativo = utilidadNeta + depreciacionFlujo + cambiosCapitalTrabajo; // C16
  
  //variación neta de caja: flujo operativo + flujo inversión + flujo financiamiento
  const variacionNetaCaja =
    flujoOperativo + - Math.abs(flujoInversion) +  -Math.abs(flujoFinanciamiento); //             C28
  const cajaFinal = e.cajaInicial + variacionNetaCaja; //                 C30
  // La caja que cierra el flujo debe ser la misma que declara el balance.
  const chequeoCajaBalance = cajaFinal - e.caja;

  return {
    utilidadBruta,
    ebit,
    resultadoAntesImpuesto,
    utilidadNeta,
    ebitda,
    totalActivosCorrientes,
    totalActivos,
    totalPasivosCorrientes,
    totalPasivos,
    totalPasivoPatrimonio,
    cuadreContable,
    cuadrado: Math.abs(cuadreContable) < TOLERANCIA_CUADRE,
    depreciacionFlujo,
    cambioCuentasPorCobrar,
    cambioInventarios,
    cambioCuentasPorPagar,
    otrosCambiosCapitalTrabajo,
    cambiosCapitalTrabajo,
    flujoOperativo,
    flujoInversion,
    flujoFinanciamiento,
    variacionNetaCaja,
    cajaFinal,
    chequeoCajaBalance,
    cajaConciliada: Math.abs(chequeoCajaBalance) < TOLERANCIA_CUADRE,
    deudaFinancieraTotal: e.deudaCortoPlazo + e.deudaLargoPlazo,
  };
}

/**
 * Traduce los estados al cuerpo que espera `POST /api/v1/risk/scoring/corporativo`.
 *
 * El motor razona con magnitudes positivas para los conceptos de coste, que es
 * ya la convención con la que se capturan, así que las partidas viajan tal cual:
 * no se fuerza ningún signo. Si el analista introdujo un valor negativo a
 * propósito —una recuperación de impuesto, por ejemplo—, el motor lo recibe con
 * su signo y no convertido en un coste que nunca existió.
 */
export function aEntradasScoring(
  entrada: Partial<Record<keyof EntradasIHP, unknown>>,
  d: EstadosFinancierosIHP,
): Record<string, number> {
  const e = normalizarEntradas(entrada);
  return {
    activos_corrientes: d.totalActivosCorrientes,
    pasivos_corrientes: d.totalPasivosCorrientes,
    pasivos_totales: d.totalPasivos,
    patrimonio: e.patrimonio,
    activos_totales: d.totalActivos,
    caja_equivalentes: e.caja,
    cuentas_por_cobrar: e.cuentasPorCobrar,
    cuentas_por_pagar: e.cuentasPorPagar,
    inventarios: e.inventarios,
    deuda_financiera_total: d.deudaFinancieraTotal,
    ebitda: d.ebitda,
    gastos_financieros: e.gastosFinancieros,
    depreciacion_amortizacion: e.depreciacionAmortizacion,
    costo_ventas: e.costoVentas,
    impuestos_estimados: e.impuestoRenta,
    utilidad_neta: d.utilidadNeta,
  };
}
