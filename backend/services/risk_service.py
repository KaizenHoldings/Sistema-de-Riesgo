from datetime import datetime, timedelta

from database.daos_sqlserver import PlanPagoDAO


class AmortizationService:
    """
    Plan de amortización francés.

    El cálculo y la persistencia están separados: `calcular_plan` es una función
    pura que no toca la base y puede probarse o exponerse por HTTP sin conexión,
    mientras que `generar` orquesta cálculo más escritura, que es lo que siguen
    llamando las vistas.

    La fórmula es exactamente la que estaba en producción: no se ha modificado
    ni el cálculo de la cuota, ni el reparto capital/interés, ni el redondeo a
    dos decimales, ni el suelo de saldo en 0,005, ni el paso de 30 días entre
    vencimientos.
    """

    @staticmethod
    def calcular_plan(monto, tasa_anual, plazo_meses, fecha_inicio_str=None):
        """
        Calcula la tabla de amortización sin persistir nada.

        Args:
            monto: capital financiado.
            tasa_anual: tasa nominal anual en porcentaje.
            plazo_meses: número de cuotas.
            fecha_inicio_str: fecha base `AAAA-MM-DD`; hoy si se omite o no parsea.

        Returns:
            list[dict] con `periodo`, `fecha_pago`, `cuota`, `capital`,
            `interes`, `saldo` y `estado` por cada vencimiento.
        """
        r = tasa_anual / 12 / 100
        if r == 0:
            cuota = monto / plazo_meses
        else:
            cuota = monto * (r * (1 + r) ** plazo_meses) / ((1 + r) ** plazo_meses - 1)

        saldo = monto
        if fecha_inicio_str:
            try:
                fecha_base = datetime.strptime(str(fecha_inicio_str)[:10], "%Y-%m-%d")
            except Exception:
                fecha_base = datetime.now()
        else:
            fecha_base = datetime.now()

        plan = []
        for p in range(1, int(plazo_meses) + 1):
            interes_p = saldo * r
            capital_p = cuota - interes_p
            saldo -= capital_p
            if saldo < 0.005:
                saldo = 0.0
            fecha_pago = (fecha_base + timedelta(days=30 * p)).strftime("%Y-%m-%d")
            plan.append({
                "periodo": p,
                "fecha_pago": fecha_pago,
                "cuota": round(cuota, 2),
                "capital": round(capital_p, 2),
                "interes": round(interes_p, 2),
                "saldo": round(saldo, 2),
                "estado": "PENDIENTE",
            })
        return plan

    @staticmethod
    def persistir_plan(exp_id, tipo, plan, session=None):
        """
        Escribe en `plan_pagos` un plan ya calculado, reemplazando el anterior.

        Se mantiene aparte del cálculo para que una ruta pueda devolver la tabla
        sin guardarla, y para que la escritura pueda participar de la
        transacción del llamador a través de `session`.
        """
        PlanPagoDAO.delete_by_expediente(exp_id, tipo, session=session)
        filas = [(exp_id, tipo, c["periodo"], c["fecha_pago"], c["cuota"],
                  c["capital"], c["interes"], c["saldo"], c["estado"])
                 for c in plan]
        PlanPagoDAO.insert_many(filas, session=session)
        return len(filas)

    @staticmethod
    def generar(exp_id, tipo, monto, tasa_anual, plazo_meses, fecha_inicio_str=None,
                session=None):
        """
        Genera e inserta el plan de amortización francés en `plan_pagos`.

        Conserva la firma que usan las vistas: calcula y persiste en un paso.
        """
        plan = AmortizationService.calcular_plan(monto, tasa_anual, plazo_meses,
                                                 fecha_inicio_str)
        AmortizationService.persistir_plan(exp_id, tipo, plan, session=session)
        return plan


class RiskScoreService:
    # Marcador histórico: la matemática de scoring vive en
    # `services/risk_score_service.py`. Se conserva el nombre para no romper
    # ninguna importación antigua.
    pass
