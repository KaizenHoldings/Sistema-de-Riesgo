"""
Motor de scoring crediticio de KFG Risk Architect.

Contiene la matemática financiera que antes vivía incrustada entre las llamadas
de renderizado de `views/risk.py`. Son funciones puras: reciben números y
devuelven números, sin tocar Streamlit, pandas ni la base de datos.

Las fórmulas, los pesos, los umbrales y las constantes son exactamente los que
ya estaban en producción; este módulo las traslada, no las modifica.
"""


class RiskScoreService:
    """Cálculo de ratios, scores y precio sugerido para ambas líneas de producto."""

    # ── Constantes de la fórmula ──────────────────────────────────────────
    # Escenario de estrés: recorte aplicado a la magnitud sensible de cada línea
    FACTOR_ESTRES_CORP = 0.8    # -20 % sobre el EBITDA
    FACTOR_ESTRES_AUTO = 0.85   # -15 % sobre el ingreso

    # Suelos que evitan divisiones por cero conservando el signo del ratio
    EPS_BALANCE = 0.001         # denominadores del balance corporativo
    EPS_INGRESO = 0.001         # ingreso mensual en la línea automotriz
    PESO_MINIMO = 0.1           # suma de pesos mínima admitida

    # Factores de conversión de cada ratio a una escala 0-10
    F_LIQUIDEZ = 5              # razón corriente -> puntos
    F_SOLVENCIA = 2.5           # apalancamiento -> penalización
    F_COBERTURA = 2             # cobertura de intereses -> puntos
    SCORE_MAX = 10.0

    # Umbrales de clasificación (porcentaje)
    PTI_ACEPTABLE = 30
    PTI_AJUSTADO = 40
    DTI_ALERTA = 30
    DTI_CRITICO = 40
    DTI_DELTA_OK = 35

    # ══ Bloque común ══════════════════════════════════════════════════════
    @staticmethod
    def aplicar_boost_kaizen(score_base, kc_score, boost_max):
        """
        Aplica la Matriz Kaizen Institucional sobre el score cuantitativo.

        Un `kc_score` de 10 sobre 10 concede el `boost_max` completo (en
        porcentaje); el resultado nunca supera 10 y se redondea a dos decimales.
        """
        con_boost = score_base * (1 + (kc_score / 10 * boost_max / 100))
        return round(min(con_boost, RiskScoreService.SCORE_MAX), 2)

    @staticmethod
    def tasa_sugerida(score_final, tasa_base, factor_riesgo):
        """Precio sugerido: la tasa base más la prima por cada punto de score perdido."""
        return round(tasa_base + ((10 - score_final) * factor_riesgo), 2)

    # ══ Línea corporativa ═════════════════════════════════════════════════
    @staticmethod
    def aplicar_estres_corporativo(ebitda, aplicar):
        """EBITDA ajustado por el escenario de estrés (-20 %)."""
        return ebitda * RiskScoreService.FACTOR_ESTRES_CORP if aplicar else ebitda

    @staticmethod
    def calcular_dscr(ebitda_calc, gastos_financieros, cuota_mensual):
        """Cobertura del servicio de deuda: EBITDA sobre intereses más las 12 cuotas."""
        denominador = gastos_financieros + (cuota_mensual * 12)
        return (ebitda_calc / denominador) if denominador > 0 else 0

    @staticmethod
    def calcular_margen_ebitda(ebitda_calc, ingresos_mensuales):
        """Margen EBITDA sobre los ingresos anualizados, en porcentaje."""
        return (ebitda_calc / (ingresos_mensuales * 12) * 100) if ingresos_mensuales > 0 else 0

    @staticmethod
    def score_liquidez(activos_corrientes, pasivos_corrientes):
        """Razón corriente llevada a escala 0-10, con techo en 10."""
        pc_s = max(pasivos_corrientes, RiskScoreService.EPS_BALANCE)
        return min(activos_corrientes / pc_s * RiskScoreService.F_LIQUIDEZ,
                   RiskScoreService.SCORE_MAX)

    @staticmethod
    def score_solvencia(pasivos_totales, patrimonio):
        """Apalancamiento como penalización sobre 10, con suelo en 0."""
        pa_s = max(patrimonio, RiskScoreService.EPS_BALANCE)
        return max(10 - pasivos_totales / pa_s * RiskScoreService.F_SOLVENCIA, 0)

    @staticmethod
    def score_cobertura(ebitda_calc, gastos_financieros):
        """Cobertura de gastos financieros llevada a escala 0-10, con techo en 10."""
        gf_s = max(gastos_financieros, RiskScoreService.EPS_BALANCE)
        return min(ebitda_calc / gf_s * RiskScoreService.F_COBERTURA,
                   RiskScoreService.SCORE_MAX)

    @staticmethod
    def score_base_corporativo(s_liquidez, s_solvencia, s_cobertura,
                               w_liq, w_sol, w_cob):
        """Media ponderada de los tres scores cuantitativos corporativos."""
        suma_pesos = w_liq + w_sol + w_cob
        return (((s_liquidez) * w_liq) +
                ((s_solvencia) * w_sol) +
                ((s_cobertura) * w_cob)) / max(suma_pesos, RiskScoreService.PESO_MINIMO)

    @staticmethod
    def evaluar_corporativo(activos_corrientes, pasivos_corrientes, ebitda,
                            gastos_financieros, pasivos_totales, patrimonio,
                            ingresos_mensuales, cuota_mensual, aplicar_estres,
                            kc_score, w_liq, w_sol, w_cob, boost_max,
                            tasa_base, factor_riesgo,
                            # ── Estado de resultados ampliado ──
                            costo_ventas=0.0, depreciacion_amortizacion=0.0,
                            impuestos_estimados=0.0,
                            utilidad_neta=0.0,
                            # ── Balance general ampliado ──
                            activos_totales=0.0, caja_equivalentes=0.0,
                            cuentas_por_cobrar=0.0, cuentas_por_pagar=0.0,
                            inventarios=0.0, deuda_financiera_total=0.0,
                            utilidades_retenidas=0.0,
                            valor_patrimonio_mercado=0.0,
                            # ── Estructura del crédito ──
                            monto_credito=0.0, tasa_interes_anual=0.0,
                            plazo_meses=0, meses_gracia=0):
        """
        Evaluación completa de un expediente corporativo.

        Los parámetros del estado de resultados ampliado, del balance general
        ampliado y de la estructura del crédito son opcionales. Alimentan la
        batería informativa de `calcular_indicadores` y se devuelven íntegros
        en `entradas_extendidas`, pero **no intervienen en el score Kaizen ni
        en la tasa sugerida**: al tener valor por defecto, los resultados
        existentes no cambian. Los de la estructura del crédito siguen sin uso
        en ningún cálculo, a la espera del DSCR ampliado y del Altman Z-Score.

        Returns:
            dict con `ebitda_calc`, `dscr`, `margen_ebitda`, los tres scores
            parciales, `score_base`, `score_final`, `tasa_sugerida`,
            `indicadores` y `entradas_extendidas`.
        """
        ebitda_calc = RiskScoreService.aplicar_estres_corporativo(ebitda, aplicar_estres)

        dscr = RiskScoreService.calcular_dscr(ebitda_calc, gastos_financieros, cuota_mensual)
        margen = RiskScoreService.calcular_margen_ebitda(ebitda_calc, ingresos_mensuales)

        s_liq = RiskScoreService.score_liquidez(activos_corrientes, pasivos_corrientes)
        s_sol = RiskScoreService.score_solvencia(pasivos_totales, patrimonio)
        s_cob = RiskScoreService.score_cobertura(ebitda_calc, gastos_financieros)

        s_base = RiskScoreService.score_base_corporativo(s_liq, s_sol, s_cob,
                                                         w_liq, w_sol, w_cob)
        score_final = RiskScoreService.aplicar_boost_kaizen(s_base, kc_score, boost_max)
        tasa = RiskScoreService.tasa_sugerida(score_final, tasa_base, factor_riesgo)

        # Bateria informativa: no interviene en el score ni en la tasa. Los
        # ingresos se anualizan con el mismo criterio que el margen EBITDA.
        indicadores = RiskScoreService.calcular_indicadores(
            activos_corrientes=activos_corrientes,
            pasivos_corrientes=pasivos_corrientes,
            pasivos_totales=pasivos_totales,
            patrimonio=patrimonio,
            activos_totales=activos_totales,
            caja_equivalentes=caja_equivalentes,
            cuentas_por_cobrar=cuentas_por_cobrar,
            cuentas_por_pagar=cuentas_por_pagar,
            inventarios=inventarios,
            deuda_financiera_total=deuda_financiera_total,
            ebitda=ebitda,
            depreciacion_amortizacion=depreciacion_amortizacion,
            ingresos_ventas=float(ingresos_mensuales) * 12,
            costo_ventas=costo_ventas,
            utilidad_neta=utilidad_neta)

        # Modelo de insolvencia: informativo, no interviene en el score Kaizen
        altman = RiskScoreService.calcular_altman_z(
            activos_corrientes=activos_corrientes,
            pasivos_corrientes=pasivos_corrientes,
            activos_totales=activos_totales,
            utilidades_retenidas=utilidades_retenidas,
            ebitda=ebitda,
            depreciacion_amortizacion=depreciacion_amortizacion,
            patrimonio=patrimonio,
            pasivos_totales=pasivos_totales,
            ingresos_ventas=float(ingresos_mensuales) * 12,
            valor_patrimonio_mercado=valor_patrimonio_mercado)

        return {
            'ebitda_calc': ebitda_calc,
            'dscr': dscr,
            'margen_ebitda': margen,
            'indicadores': indicadores,
            'altman': altman,
            'score_liquidez': s_liq,
            'score_solvencia': s_sol,
            'score_cobertura': s_cob,
            'score_base': s_base,
            'score_final': score_final,
            'tasa_sugerida': tasa,
            # Datos capturados sin uso todavia en el calculo; viajan intactos
            'entradas_extendidas': {
                'costo_ventas': costo_ventas,
                'depreciacion_amortizacion': depreciacion_amortizacion,
                'impuestos_estimados': impuestos_estimados,
                'utilidad_neta': utilidad_neta,
                'activos_totales': activos_totales,
                'caja_equivalentes': caja_equivalentes,
                'cuentas_por_cobrar': cuentas_por_cobrar,
                'cuentas_por_pagar': cuentas_por_pagar,
                'inventarios': inventarios,
                'deuda_financiera_total': deuda_financiera_total,
                'utilidades_retenidas': utilidades_retenidas,
                'valor_patrimonio_mercado': valor_patrimonio_mercado,
                'monto_credito': monto_credito,
                'tasa_interes_anual': tasa_interes_anual,
                'plazo_meses': plazo_meses,
                'meses_gracia': meses_gracia,
            },
        }


    # ══ Batería de indicadores financieros ════════════════════════════════
    #
    # Umbrales institucionales. `modo` define como se lee el valor:
    #   'alto'  -> cuanto mayor, mejor  (>= verde -> Verde; >= amarillo -> Amarillo)
    #   'bajo'  -> cuanto menor, mejor  (<= verde -> Verde; <= amarillo -> Amarillo)
    #   'banda' -> hay un rango sano; fuera de el se degrada por tramos
    # Los indicadores sin umbral devuelven "Referencial".
    UMBRALES = {
        # Liquidez
        'razon_corriente':      {'modo': 'alto', 'verde': 1.50, 'amarillo': 1.00},
        'prueba_acida':         {'modo': 'alto', 'verde': 1.00, 'amarillo': 0.75},
        'kt_sobre_activos':     {'modo': 'alto', 'verde': 0.20, 'amarillo': 0.05},
        # Endeudamiento
        'deuda_patrimonio':     {'modo': 'bajo', 'verde': 1.50, 'amarillo': 2.50},
        'pasivo_activo':        {'modo': 'bajo', 'verde': 0.60, 'amarillo': 0.75},
        'dfn_ebitda':           {'modo': 'bajo', 'verde': 3.00, 'amarillo': 4.00},
        # Rentabilidad (valores en tanto por uno, no en porcentaje)
        'margen_bruto':         {'modo': 'alto', 'verde': 0.25, 'amarillo': 0.15},
        'margen_ebit':          {'modo': 'alto', 'verde': 0.10, 'amarillo': 0.05},
        'margen_neto':          {'modo': 'alto', 'verde': 0.05, 'amarillo': 0.01},
        'roa':                  {'modo': 'alto', 'verde': 0.05, 'amarillo': 0.01},
        'roe':                  {'modo': 'alto', 'verde': 0.10, 'amarillo': 0.03},
        'rotacion_activos':     {'modo': 'alto', 'verde': 1.00, 'amarillo': 0.60},
        # Ciclo de conversión de efectivo (días)
        'dio':                  {'modo': 'bajo', 'verde': 90,  'amarillo': 120},
        'dso':                  {'modo': 'bajo', 'verde': 60,  'amarillo': 90},
        'dpo':                  {'modo': 'banda', 'verde': (30, 90), 'amarillo': (15, 120)},
        'cce_dias':             {'modo': 'bajo', 'verde': 90,  'amarillo': 120},
    }

    SEMAFORO_EMOJI = {'Verde': '🟢', 'Amarillo': '🟡', 'Rojo': '🔴', 'Referencial': '⚪'}

    DIAS_ANIO = 365

    @staticmethod
    def clasificar_semaforo(clave, valor):
        """
        Semáforo de un indicador segun los umbrales institucionales.

        Devuelve `None` si el valor no se pudo calcular y "Referencial" si el
        indicador no tiene umbral definido.
        """
        if valor is None:
            return None
        umbral = RiskScoreService.UMBRALES.get(clave)
        if umbral is None:
            return 'Referencial'

        modo = umbral['modo']
        if modo == 'alto':
            if valor >= umbral['verde']:
                return 'Verde'
            return 'Amarillo' if valor >= umbral['amarillo'] else 'Rojo'
        if modo == 'bajo':
            if valor <= umbral['verde']:
                return 'Verde'
            return 'Amarillo' if valor <= umbral['amarillo'] else 'Rojo'
        # 'banda': rango sano y rango tolerable
        v_lo, v_hi = umbral['verde']
        a_lo, a_hi = umbral['amarillo']
        if v_lo <= valor <= v_hi:
            return 'Verde'
        return 'Amarillo' if a_lo <= valor <= a_hi else 'Rojo'

    @staticmethod
    def _formatear(valor, formato):
        """Representacion legible de un indicador segun su naturaleza."""
        if valor is None:
            return "N/A"
        if formato == 'porcentaje':
            return f"{valor * 100:,.2f}%"
        if formato == 'dias':
            return f"{valor:,.0f} días"
        if formato == 'veces':
            return f"{valor:,.2f}x"
        return f"{valor:,.2f}"

    @staticmethod
    def _empaquetar(clave, nombre, categoria, valor, expresion, detalle,
                    formato='numero', semaforo_forzado=None):
        """Estructura comun de todos los indicadores."""
        semaforo = semaforo_forzado or RiskScoreService.clasificar_semaforo(clave, valor)
        return {
            'clave': clave,
            'nombre': nombre,
            'categoria': categoria,
            'valor': valor,
            'valor_fmt': RiskScoreService._formatear(valor, formato),
            'formula': expresion,
            'detalle': detalle,
            'semaforo': semaforo,
            'emoji': RiskScoreService.SEMAFORO_EMOJI.get(semaforo, ''),
        }

    @staticmethod
    def _cociente(numerador, denominador):
        """Division protegida: devuelve None si el denominador es cero o invalido."""
        try:
            if denominador is None or float(denominador) == 0:
                raise ZeroDivisionError
            return float(numerador) / float(denominador)
        except (ZeroDivisionError, TypeError, ValueError):
            return None

    @staticmethod
    def _indicador(clave, nombre, categoria, numerador, denominador,
                   expresion, formato='numero', semaforo_forzado=None):
        """
        Calcula un cociente y lo empaqueta con su formula y su semaforo.

        Un denominador nulo o cero no lanza `ZeroDivisionError`: el indicador
        queda con `valor = None` y `valor_fmt = "N/A"`.
        """
        print("Calculando indicador:", clave, nombre, categoria, numerador, denominador)
        print("Valores recibidos:", numerador, denominador)
        valor = RiskScoreService._cociente(numerador, denominador)

        print("----Valor calculado:", valor)
        if valor is None:
            detalle = f"{expresion} → denominador en cero, no calculable"
        else:
            detalle = (f"{expresion} = {float(numerador):,.2f} / "
                       f"{float(denominador):,.2f} = "
                       f"{RiskScoreService._formatear(valor, formato)}")
        return RiskScoreService._empaquetar(clave, nombre, categoria, valor,
                                            expresion, detalle, formato,
                                            semaforo_forzado)
    
    @staticmethod
    def calcular_indicadores(activos_corrientes=0.0, pasivos_corrientes=0.0,
                             pasivos_totales=0.0, patrimonio=0.0,
                             activos_totales=0.0, caja_equivalentes=0.0,
                             cuentas_por_cobrar=0.0, inventarios=0.0,
                             cuentas_por_pagar=0.0, deuda_financiera_total=0.0,
                             ebitda=0.0, depreciacion_amortizacion=0.0,
                             ingresos_ventas=0.0, costo_ventas=0.0,
                             utilidad_neta=0.0):
        """
        Bateria de indicadores financieros agrupados por categoria.

        Todas las magnitudes se esperan anualizadas y en la misma moneda. Los
        saldos de inventario, cuentas por cobrar y cuentas por pagar se usan
        como promedios del periodo. El EBIT se despeja de la identidad contable
        `EBITDA = EBIT + D&A`, y la utilidad bruta de `Ventas - Costo de ventas`.

        Ningun indicador interviene en el score Kaizen ni en la tasa: son
        informativos.

        Returns:
            dict {categoria: [indicador, ...]} en el orden de presentacion.
        """
        ebit = float(ebitda) - float(depreciacion_amortizacion)
        utilidad_bruta = float(ingresos_ventas) - float(costo_ventas)

        print("---------------------Calculando indicadores con:", activos_corrientes, pasivos_corrientes)
        capital_trabajo = (float(activos_corrientes) - float(pasivos_corrientes))
        
        print("78525555",capital_trabajo, float(activos_corrientes), float(pasivos_corrientes))
        print("total activos", activos_totales)


        deuda_financiera_neta = float(deuda_financiera_total) - float(caja_equivalentes)
        activos_liquidos = float(caja_equivalentes) + float(cuentas_por_cobrar)

        ind = RiskScoreService._indicador
        coc = RiskScoreService._cociente

        aux = capital_trabajo

        if(activos_totales > 0):
            print("total activos", activos_totales)
            aux = aux / activos_totales

        
        
        # ── Liquidez ──────────────────────────────────────────────────────
        liquidez = [
            ind('razon_corriente', 'Razón corriente', 'Liquidez',
                activos_corrientes, pasivos_corrientes,
                'Activo corriente / Pasivo corriente'),
            ind('prueba_acida', 'Prueba ácida', 'Liquidez',
                activos_liquidos, pasivos_corrientes,
                '(Caja + CxC neta) / Pasivo corriente'),
            ind('kt_sobre_activos', 'Capital de trabajo / Activos', 'Liquidez',
                capital_trabajo, activos_totales,
                '(Activo corriente - Pasivo corriente) / Activos totales'),
        ]

        # ── Endeudamiento ─────────────────────────────────────────────────
        # La deuda financiera neta sobre EBITDA se marca en rojo cuando el
        # EBITDA no es positivo, tal como exige la política: un EBITDA nulo o
        # negativo hace que el cociente pierda sentido economico.
        ebitda_no_positivo = float(ebitda) <= 0
        endeudamiento = [
            ind('deuda_patrimonio', 'Deuda total / Patrimonio', 'Endeudamiento',
                pasivos_totales, patrimonio,
                'Total pasivos / Patrimonio'),
            ind('pasivo_activo', 'Pasivo total / Activo total', 'Endeudamiento',
                pasivos_totales, activos_totales,
                'Total pasivos / Total activos'),
            ind('dfn_ebitda', 'Deuda financiera neta / EBITDA', 'Endeudamiento',
                deuda_financiera_neta, ebitda,
                '(Deuda financiera CP+LP - Caja) / EBITDA',
                semaforo_forzado='Rojo' if ebitda_no_positivo else None),
        ]

        # ── Rentabilidad ──────────────────────────────────────────────────
        rentabilidad = [
            ind('margen_bruto', 'Margen bruto', 'Rentabilidad',
                utilidad_bruta, ingresos_ventas,
                'Utilidad bruta / Ventas', formato='porcentaje'),
            ind('margen_ebit', 'Margen EBIT', 'Rentabilidad',
                ebit, ingresos_ventas,
                'EBIT / Ventas', formato='porcentaje'),
            ind('margen_neto', 'Margen neto', 'Rentabilidad',
                utilidad_neta, ingresos_ventas,
                'Utilidad neta / Ventas', formato='porcentaje'),
            ind('roa', 'ROA', 'Rentabilidad',
                utilidad_neta, activos_totales,
                'Utilidad neta / Activos totales', formato='porcentaje'),
            ind('roe', 'ROE', 'Rentabilidad',
                utilidad_neta, patrimonio,
                'Utilidad neta / Patrimonio', formato='porcentaje'),
            ind('rotacion_activos', 'Rotación de activos', 'Rentabilidad',
                ingresos_ventas, activos_totales,
                'Ventas / Activos totales', formato='veces'),
        ]

        # ── Ciclo de conversión de efectivo ───────────────────────────────
        rot_inv = coc(costo_ventas, inventarios)
        rot_cxc = coc(ingresos_ventas, cuentas_por_cobrar)
        rot_cxp = coc(costo_ventas, cuentas_por_pagar)
        dio = coc(RiskScoreService.DIAS_ANIO, rot_inv)
        dso = coc(RiskScoreService.DIAS_ANIO, rot_cxc)
        dpo = coc(RiskScoreService.DIAS_ANIO, rot_cxp)

        if None in (dio, dso, dpo):
            cce = None
            detalle_cce = ("DSO + DIO - DPO → falta alguno de los tres plazos, "
                           "no calculable")
        else:
            cce = dso + dio - dpo
            detalle_cce = (f"DSO + DIO - DPO = {dso:,.0f} + {dio:,.0f} - "
                           f"{dpo:,.0f} = {cce:,.0f} días")

        cce_lista = [
            ind('rotacion_inventarios', 'Rotación de inventarios', 'Ciclo de Conversión de Efectivo',
                costo_ventas, inventarios,
                'COGS / Inventario promedio', formato='veces'),
            RiskScoreService._empaquetar(
                'dio', 'Días de inventario (DIO)', 'Ciclo de Conversión de Efectivo',
                dio, '365 / Rotación de inventarios',
                (f"365 / {rot_inv:,.2f} = {dio:,.0f} días" if dio is not None
                 else "365 / Rotación de inventarios → rotación no calculable"),
                formato='dias'),
            ind('rotacion_cxc', 'Rotación de CxC', 'Ciclo de Conversión de Efectivo',
                ingresos_ventas, cuentas_por_cobrar,
                'Ventas / CxC promedio', formato='veces'),
            RiskScoreService._empaquetar(
                'dso', 'DSO', 'Ciclo de Conversión de Efectivo',
                dso, '365 / Rotación de CxC',
                (f"365 / {rot_cxc:,.2f} = {dso:,.0f} días" if dso is not None
                 else "365 / Rotación de CxC → rotación no calculable"),
                formato='dias'),
            ind('rotacion_cxp', 'Rotación de CxP', 'Ciclo de Conversión de Efectivo',
                costo_ventas, cuentas_por_pagar,
                'COGS / CxP promedio', formato='veces'),
            RiskScoreService._empaquetar(
                'dpo', 'DPO', 'Ciclo de Conversión de Efectivo',
                dpo, '365 / Rotación de CxP',
                (f"365 / {rot_cxp:,.2f} = {dpo:,.0f} días" if dpo is not None
                 else "365 / Rotación de CxP → rotación no calculable"),
                formato='dias'),
            RiskScoreService._empaquetar(
                'cce_dias', 'Ciclo de conversión (CCE)', 'Ciclo de Conversión de Efectivo',
                cce, 'DSO + DIO - DPO', detalle_cce, formato='dias'),
        ]

        # ── Análisis DuPont ───────────────────────────────────────────────
        # ROE = Margen neto × Rotación de activos × Multiplicador de patrimonio.
        # El indice se calcula con esa descomposicion y debe reproducir el ROE.
        multiplicador = coc(activos_totales, patrimonio)
        margen_neto_val = coc(utilidad_neta, ingresos_ventas)
        rot_activos_val = coc(ingresos_ventas, activos_totales)
        roe_val = coc(utilidad_neta, patrimonio)

        if None in (margen_neto_val, rot_activos_val, multiplicador):
            dupont = None
            detalle_dupont = ("Margen neto × Rotación de activos × Multiplicador "
                              "→ falta algun componente, no calculable")
        else:
            dupont = margen_neto_val * rot_activos_val * multiplicador
            detalle_dupont = (
                f"{margen_neto_val:,.4f} × {rot_activos_val:,.4f} × "
                f"{multiplicador:,.4f} = {dupont * 100:,.2f}%")
            if roe_val is not None:
                coincide = abs(dupont - roe_val) < 1e-9
                detalle_dupont += (f"  ·  ROE directo = {roe_val * 100:,.2f}% "
                                   f"({'coincide' if coincide else 'NO coincide'})")

        dupont_lista = [
            ind('multiplicador_patrimonio', 'Multiplicador de patrimonio', 'Análisis DuPont',
                activos_totales, patrimonio,
                'Activos totales / Patrimonio', formato='veces'),
            RiskScoreService._empaquetar(
                'indice_dupont', 'Índice DuPont (ROE)', 'Análisis DuPont',
                dupont, 'Margen neto × Rotación de activos × Multiplicador',
                detalle_dupont, formato='porcentaje'),
        ]

        return {
            'Liquidez': liquidez,
            'Endeudamiento': endeudamiento,
            'Rentabilidad': rentabilidad,
            'Ciclo de Conversión de Efectivo': cce_lista,
            'Análisis DuPont': dupont_lista,
        }



    # ══ Altman Z-Score (empresas privadas) ════════════════════════════════
    #
    # Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5
    # Coeficientes y cortes del modelo para empresas no cotizadas.
    ALTMAN_COEFICIENTES = {'X1': 1.2, 'X2': 1.4, 'X3': 3.3, 'X4': 0.6, 'X5': 1.0}
    ALTMAN_CORTE_ANGUSTIA = 1.81   # por debajo: zona de angustia
    ALTMAN_CORTE_SEGURA = 2.99     # por encima: zona segura

    ALTMAN_ETIQUETAS = {
        'X1': 'X1 = Capital de trabajo / Activos totales',
        'X2': 'X2 = Utilidades retenidas / Activos totales',
        'X3': 'X3 = EBIT / Activos totales',
        'X4': 'X4 = Valor de mercado del patrimonio / Deuda total',
        'X5': 'X5 = Ventas / Activos totales',
    }

    ALTMAN_FORMULAS = {
        'X1': '(Activo corriente - Pasivo corriente) / Activos totales',
        'X2': 'Utilidades retenidas / Activos totales',
        'X3': 'EBIT / Activos totales, con EBIT = EBITDA - D&A',
        'X4': 'Patrimonio / Total pasivos',
        'X5': 'Ingresos por ventas / Activos totales',
    }

    @staticmethod
    def clasificar_altman(z):
        """
        Zona del modelo Altman y su semaforo.

        Angustia por debajo de 1.81, gris entre 1.81 y 2.99 inclusive, segura
        por encima de 2.99. Un Z no calculable devuelve zona y semaforo nulos.
        """
        if z is None:
            return None, None
        if z < RiskScoreService.ALTMAN_CORTE_ANGUSTIA:
            return 'Zona de angustia', 'Rojo'
        if z <= RiskScoreService.ALTMAN_CORTE_SEGURA:
            return 'Zona gris', 'Amarillo'
        return 'Zona segura', 'Verde'

    @staticmethod
    def calcular_altman_z(activos_corrientes=0.0, pasivos_corrientes=0.0,
                          activos_totales=0.0, utilidades_retenidas=0.0,
                          ebitda=0.0, depreciacion_amortizacion=0.0,
                          patrimonio=0.0, pasivos_totales=0.0,
                          ingresos_ventas=0.0, valor_patrimonio_mercado=0.0):
        """
        Altman Z-Score en su variante para empresas privadas.

        X4 usa el valor estimado del patrimonio que captura la vista. Cuando
        ese campo se deja en cero se recurre al patrimonio contable, que es la
        adaptacion habitual del modelo para empresas no cotizadas: sin precio
        de mercado no hay capitalizacion observable.

        Las cinco componentes se calculan con division protegida. Si alguna no
        es calculable —activos totales o pasivos totales en cero— el Z queda en
        `None` y se muestra como "N/A", en lugar de sumar una descomposicion
        incompleta.

        Returns:
            dict con `z`, `z_fmt`, `zona`, `semaforo`, `emoji`, `formula`,
            `detalle`, `componentes` (lista con clave, etiqueta, formula,
            coeficiente, valor, valor_fmt y aporte al Z) y `variables_base`
            (las siete magnitudes de partida con su origen).
        """
        coc = RiskScoreService._cociente
        capital_trabajo = float(activos_corrientes) - float(pasivos_corrientes)
        ebit = float(ebitda) - float(depreciacion_amortizacion)

        # X4: se prefiere el valor estimado de mercado; si no se informa, se
        # cae al patrimonio contable y se deja constancia en la formula.
        usa_estimado = bool(valor_patrimonio_mercado)
        base_x4 = float(valor_patrimonio_mercado) if usa_estimado else float(patrimonio)

        valores = {
            'X1': coc(capital_trabajo, activos_totales),
            'X2': coc(utilidades_retenidas, activos_totales),
            'X3': coc(ebit, activos_totales),
            'X4': coc(base_x4, pasivos_totales),
            'X5': coc(ingresos_ventas, activos_totales),
        }

        if any(v is None for v in valores.values()):
            z = None
        else:
            z = sum(RiskScoreService.ALTMAN_COEFICIENTES[k] * valores[k]
                    for k in ('X1', 'X2', 'X3', 'X4', 'X5'))

        zona, semaforo = RiskScoreService.clasificar_altman(z)

        # Magnitudes de partida del modelo, tal como llegan de la captura o se
        # derivan de ella. Se exponen para que la ficha pueda mostrarlas junto
        # a las componentes y el analista vea de donde sale cada X.
        variables_base = [
            {'clave': 'activos_corrientes', 'etiqueta': 'Activos corrientes',
             'valor': float(activos_corrientes)},
            {'clave': 'pasivos_corrientes', 'etiqueta': 'Pasivos corrientes',
             'valor': float(pasivos_corrientes)},
            {'clave': 'capital_trabajo', 'etiqueta': 'Capital de trabajo',
             'valor': capital_trabajo,
             'origen': 'Activos corrientes - Pasivos corrientes'},
            {'clave': 'activos_totales', 'etiqueta': 'Activos totales',
             'valor': float(activos_totales)},
            {'clave': 'ebit', 'etiqueta': 'EBIT', 'valor': ebit,
             'origen': 'EBITDA - Depreciación y amortización'},
            {'clave': 'ventas', 'etiqueta': 'Ventas', 'valor': float(ingresos_ventas),
             'origen': 'Ingresos mensuales × 12'},
            {'clave': 'deuda_total', 'etiqueta': 'Deuda total (total pasivos)',
             'valor': float(pasivos_totales)},
        ]
        for v in variables_base:
            v['valor_fmt'] = f"{v['valor']:,.2f}"
            v.setdefault('origen', 'Capturado en Datos Financieros')

        formulas = dict(RiskScoreService.ALTMAN_FORMULAS)
        formulas['X4'] = ('Valor estimado del patrimonio / Total pasivos'
                          if usa_estimado
                          else 'Patrimonio contable / Total pasivos '
                               '(sin valor de mercado informado)')

        componentes = []
        for clave in ('X1', 'X2', 'X3', 'X4', 'X5'):
            valor = valores[clave]
            coef = RiskScoreService.ALTMAN_COEFICIENTES[clave]
            componentes.append({
                'clave': clave,
                'etiqueta': RiskScoreService.ALTMAN_ETIQUETAS[clave],
                'formula': formulas[clave],
                'coeficiente': coef,
                'valor': valor,
                'valor_fmt': ('N/A' if valor is None else f"{valor:,.4f}"),
                'aporte': (None if valor is None else coef * valor),
                'aporte_fmt': ('N/A' if valor is None else f"{coef * valor:,.4f}"),
            })

        formula = 'Z = 1.2·X1 + 1.4·X2 + 3.3·X3 + 0.6·X4 + 1.0·X5'
        if z is None:
            detalle = (f"{formula} → alguna componente no es calculable "
                       f"(denominador en cero)")
        else:
            partes = " + ".join(
                f"{c['coeficiente']:g}·{c['valor']:,.4f}" for c in componentes)
            detalle = f"Z = {partes} = {z:,.2f}  ·  {zona}"

        return {
            'z': z,
            'variables_base': variables_base,
            'z_fmt': ('N/A' if z is None else f"{z:,.2f}"),
            'zona': zona,
            'semaforo': semaforo,
            'emoji': RiskScoreService.SEMAFORO_EMOJI.get(semaforo, ''),
            'formula': formula,
            'detalle': detalle,
            'componentes': componentes,
        }

    # ══ Línea automotriz ══════════════════════════════════════════════════
    @staticmethod
    def aplicar_estres_auto(ingreso_mensual, aplicar):
        """Ingreso ajustado por el escenario de estrés (-15 %)."""
        return ingreso_mensual * RiskScoreService.FACTOR_ESTRES_AUTO if aplicar else ingreso_mensual

    @staticmethod
    def calcular_ingreso_libre(ingreso_calc, gastos_fijos):
        """Ingreso disponible tras los gastos fijos, nunca negativo."""
        return max(ingreso_calc - gastos_fijos, 0)

    @staticmethod
    def calcular_dti(cuota_mensual, ingreso_calc):
        """Relación cuota/ingreso en porcentaje. El PTI comparte esta definición."""
        return (cuota_mensual / max(ingreso_calc, RiskScoreService.EPS_INGRESO)) * 100

    @staticmethod
    def score_capacidad(ingreso_libre, cuota_mensual, ingreso_calc):
        """Holgura tras pagar la cuota, llevada a escala 0-10 y acotada."""
        bruto = (ingreso_libre - cuota_mensual) / max(ingreso_calc,
                                                      RiskScoreService.EPS_INGRESO) * 10
        return min(max(bruto, 0), RiskScoreService.SCORE_MAX)

    @staticmethod
    def score_ltv(ltv_ratio):
        """Loan-to-Value convertido en puntos: cada 10 % de LTV resta un punto."""
        return max(10 - (ltv_ratio / 10), 0)

    @staticmethod
    def score_base_auto(s_capacidad, s_ltv, estabilidad_laboral,
                        w_cap, w_ltv, w_est):
        """Media ponderada de capacidad, LTV y estabilidad laboral."""
        suma_pesos = w_cap + w_ltv + w_est
        return ((s_capacidad * w_cap) + (s_ltv * w_ltv) +
                (estabilidad_laboral * w_est)) / max(suma_pesos,
                                                     RiskScoreService.PESO_MINIMO)

    @staticmethod
    def clasificar_pti(pti):
        """
        Tramo de riesgo del PTI (Payment-to-Income).

        Verde por debajo del 30 %, ámbar entre 30 y 40 %, rojo por encima.
        """
        if pti < RiskScoreService.PTI_ACEPTABLE:
            return {'nivel': 'aceptable', 'color': '#10B981', 'label': '🟢 Aceptable'}
        if pti <= RiskScoreService.PTI_AJUSTADO:
            return {'nivel': 'ajustado', 'color': '#F59E0B', 'label': '🟡 Ajustado'}
        return {'nivel': 'alto', 'color': '#EF4444', 'label': '🔴 Alto'}

    @staticmethod
    def clasificar_dti(dti):
        """
        Tramo de riesgo del DTI, con el indicador de variación de la métrica.

        Por encima del 40 % la capacidad se considera crítica; entre 30 y 40 %,
        ajustada. El indicador de la métrica cambia a partir del 35 %.
        """
        if dti > RiskScoreService.DTI_CRITICO:
            nivel = 'critico'
        elif dti > RiskScoreService.DTI_ALERTA:
            nivel = 'ajustado'
        else:
            nivel = 'ok'
        return {
            'nivel': nivel,
            'delta': "✓ OK" if dti < RiskScoreService.DTI_DELTA_OK else "⚠ ALTO",
            'delta_color': "normal" if dti < RiskScoreService.DTI_DELTA_OK else "inverse",
        }

    @staticmethod
    def evaluar_automotriz(ingreso_mensual, gastos_fijos, cuota_mensual, ltv_ratio,
                           estabilidad_laboral, aplicar_estres, kc_score,
                           w_cap, w_ltv, w_est, boost_max, tasa_base, factor_riesgo):
        """
        Evaluación completa de un expediente automotriz.

        Returns:
            dict con `ingreso_calc`, `ingreso_libre`, `dti`, `pti`, los scores
            parciales, `score_base`, `score_final`, `tasa_sugerida` y los tramos
            de clasificación de PTI y DTI.
        """
        ingreso_calc = RiskScoreService.aplicar_estres_auto(ingreso_mensual, aplicar_estres)

        ingreso_libre = RiskScoreService.calcular_ingreso_libre(ingreso_calc, gastos_fijos)
        dti = RiskScoreService.calcular_dti(cuota_mensual, ingreso_calc)

        s_cap = RiskScoreService.score_capacidad(ingreso_libre, cuota_mensual, ingreso_calc)
        s_ltv = RiskScoreService.score_ltv(ltv_ratio)

        s_base = RiskScoreService.score_base_auto(s_cap, s_ltv, estabilidad_laboral,
                                                  w_cap, w_ltv, w_est)
        score_final = RiskScoreService.aplicar_boost_kaizen(s_base, kc_score, boost_max)
        tasa = RiskScoreService.tasa_sugerida(score_final, tasa_base, factor_riesgo)

        # El PTI comparte definición con el DTI, pero se clasifica por su propia escala
        pti = RiskScoreService.calcular_dti(cuota_mensual, ingreso_calc)

        return {
            'ingreso_calc': ingreso_calc,
            'ingreso_libre': ingreso_libre,
            'dti': dti,
            'pti': pti,
            'score_capacidad': s_cap,
            'score_ltv': s_ltv,
            'score_base': s_base,
            'score_final': score_final,
            'tasa_sugerida': tasa,
            'tramo_pti': RiskScoreService.clasificar_pti(pti),
            'tramo_dti': RiskScoreService.clasificar_dti(dti),
        }
