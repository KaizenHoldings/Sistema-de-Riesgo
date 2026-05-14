from datetime import datetime, timedelta
from database.daos_sqlserver import PlanPagoDAO

class AmortizationService:
    @staticmethod
    def generar(exp_id, tipo, monto, tasa_anual, plazo_meses, fecha_inicio_str=None):
        """Genera e inserta el plan de amortización francés en plan_pagos."""
        PlanPagoDAO.delete_by_expediente(exp_id, tipo)
        
        r = tasa_anual / 12 / 100
        if r == 0:
            cuota = monto / plazo_meses
        else:
            cuota = monto * (r * (1 + r) ** plazo_meses) / ((1 + r) ** plazo_meses - 1)
        
        saldo = monto
        if fecha_inicio_str:
            try:
                fecha_base = datetime.strptime(fecha_inicio_str[:10], "%Y-%m-%d")
            except Exception:
                fecha_base = datetime.now()
        else:
            fecha_base = datetime.now()
            
        rows = []
        for p in range(1, int(plazo_meses) + 1):
            interes_p = saldo * r
            capital_p = cuota - interes_p
            saldo -= capital_p
            if saldo < 0.005:
                saldo = 0.0
            fecha_pago = (fecha_base + timedelta(days=30 * p)).strftime("%Y-%m-%d")
            # (exp_id, tipo, periodo, fecha_pago, cuota, capital, interes, saldo, estado)
            rows.append((exp_id, tipo, p, fecha_pago, round(cuota, 2), round(capital_p, 2),
                         round(interes_p, 2), round(saldo, 2), 'PENDIENTE'))
            
        PlanPagoDAO.insert_many(rows)

class RiskScoreService:
    # La matemática de scoring (DSCR, LTV, etc.) se mudará aquí 
    # progresivamente cuando dividamos las vistas.
    pass
