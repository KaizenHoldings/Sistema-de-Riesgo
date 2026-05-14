from fpdf import FPDF
import json
import pandas as pd

class KFG_PDF(FPDF):
    def footer(self):
        self.set_y(-20)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, "CONFIDENCIAL - KAIZEN FINANCIAL GROUP. DOCUMENTO TECNICO VINCULANTE.", align='C')

class DocumentReportService:
    @staticmethod
    def generar_pdf_corporativo(r):
        pdf = KFG_PDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "KAIZEN FINANCIAL GROUP", ln=True, align='C')
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 7, "MEMORANDUM TECNICO Y RESOLUCION DEL COMITE - CREDITO CORPORATIVO v32.0", ln=True, align='C')
        pdf.ln(5)
    
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 8, " 1. RESOLUCION Y PERFIL DE OPERACION", ln=True, fill=True)
        pdf.set_font("Arial", '', 9)
        pdf.cell(95, 8, f"Cliente: {r['cliente']} (RIF: {r['rif']})", 1)
        pdf.cell(95, 8, f"Fecha de Analisis: {r['fecha']}", 1, ln=True)
        pdf.cell(95, 8, f"Monto Solicitado: {r['monto']:,.2f} {r['moneda']}", 1)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(95, 8, f"DICTAMEN FINAL: {r['dictamen']}", 1, ln=True)
        pdf.set_font("Arial", '', 9)
        pdf.cell(95, 8, f"Tasa de Riesgo Sugerida (Sistema): {r.get('tasa_sugerida', 0):.2f}%", 1)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(95, 8, f"TASA FINAL APROBADA (Comite): {r.get('tasa_aprobada', 0):.2f}%", 1, ln=True)
        pdf.set_font("Arial", 'I', 8)
        diferencia = round(float(r.get('tasa_aprobada', 0)) - float(r.get('tasa_sugerida', 0)), 2)
        signo = "+" if diferencia >= 0 else ""
        pdf.cell(0, 6, f"  Diferencia Tasa Sugerida vs. Aprobada: {signo}{diferencia}% (spread de Comite)", ln=True)
    
        pdf.ln(3); pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 8, " 2. CUMPLIMIENTO (AML/CFT)", ln=True, fill=True)
        pdf.set_font("Arial", '', 9)
        pdf.cell(95, 8, f"Riesgo AML: {r['riesgo_aml']}", 1)
        pdf.cell(95, 8, f"Origen de Fondos: {r['origen_fondos']}", 1, ln=True)
        chk_ofac = "SI" if r.get('check_sanciones') else "NO"
        chk_pep = "SI" if r.get('check_pep') else "NO"
        pdf.cell(95, 8, f"Verif. Sanciones (OFAC/ONU): {chk_ofac}", 1)
        pdf.cell(95, 8, f"Check PEP: {chk_pep}", 1, ln=True)
        if r.get('obs_comp'): pdf.multi_cell(0, 6, f"Observaciones Cumplimiento: {r['obs_comp']}", 1)
    
        pdf.ln(3); pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 8, " 3. ANALISIS FINANCIERO Y CAPACIDAD DE PAGO", ln=True, fill=True)
        pdf.set_font("Arial", '', 9)
        str_txt = "SI (-20% EBITDA)" if r.get('estres_aplicado') else "NO"
        pdf.cell(63, 6, f"EBITDA Anual: ${r.get('eb', 0):,.2f}", 1)
        pdf.cell(63, 6, f"Ingresos Mens.: ${r.get('ing_mensuales', 0):,.2f}", 1)
        pdf.cell(64, 6, f"Cuota Mens.: ${r.get('cuota_est', 0):,.2f}", 1, ln=True)
        pdf.cell(63, 6, f"DSCR: {r.get('dscr', 0):.2f}x", 1)
        pdf.cell(63, 6, f"Margen EBITDA: {r.get('margen_ebitda', 0):.2f}%", 1)
        pdf.cell(64, 6, f"Escenario de Estres: {str_txt}", 1, ln=True)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(95, 8, f"Matriz Kaizen (Cualitativo): {r.get('rm_score', 0)}/10", 1)
        pdf.cell(95, 8, f"SCORE FINAL: {r.get('score_f', 0)} / 10", 1, ln=True)
        if r.get('obs_riesgo'): pdf.set_font("Arial", '', 9); pdf.multi_cell(0, 6, f"Observaciones Riesgo: {r['obs_riesgo']}", 1)
    
        pdf.ln(3); pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 8, " 4. ESTRUCTURA LEGAL Y COLATERALES", ln=True, fill=True)
        pdf.set_font("Arial", '', 9)
        cust_txt = "SI" if r.get('custodia_fisica') else "NO"
        pdf.cell(63, 8, f"Total Colateral: ${r.get('v_garantia', 0):,.2f}", 1)
        pdf.cell(63, 8, f"LTV Ratio: {r.get('ltv_ratio', 0):.2f}%", 1)
        pdf.cell(64, 8, f"Custodia Fisica: {cust_txt}", 1, ln=True)
        try:
            gs = json.loads(r.get('garantias_json', '[]')) if r.get('garantias_json') else []
        except (json.JSONDecodeError, TypeError):
            gs = []
        for g in gs:
            pdf.cell(0, 6, f" - {g['tipo']}: {g['desc']} (Valor: ${g['valor']:,.2f})", ln=True)
        if r.get('obs_leg'): pdf.multi_cell(0, 6, f"Observaciones Legales: {r['obs_leg']}", 1)
    
        pdf.ln(3); pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 8, " 5. COVENANTS Y CONDICIONES ESPECIALES", ln=True, fill=True)
        pdf.set_font("Arial", '', 9)
        cov_val = "null" if pd.isna(r.get('covenants')) else str(r.get('covenants', ''))
        pdf.multi_cell(0, 6, cov_val, 1)
    
        pdf.ln(12)
        pdf.cell(63, 10, "________________", align='C')
        pdf.cell(63, 10, "________________", align='C')
        pdf.cell(64, 10, "________________", ln=True, align='C')
        pdf.set_font("Arial", '', 8)
        pdf.cell(63, 5, "Firma Cumplimiento", align='C')
        pdf.cell(63, 5, "Firma Legal", align='C')
        pdf.cell(64, 5, "Firma Riesgo", align='C')
    
        if r['dictamen'] == 'APROBADO':
            pdf.ln(8); pdf.set_font("Arial", 'I', 9)
            pdf.cell(0, 5, f">>> Operacion certificada y aprobada en Comite por: {r.get('aprobado_por', '')} el dia {r.get('fecha_decision', '')} <<<", ln=True, align='C')
    
        return pdf.output(dest='S').encode('latin-1')
        
    @staticmethod
    def generar_pdf_auto(r):
        pdf = KFG_PDF(); pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "KAIZEN FINANCIAL GROUP", ln=True, align='C')
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 7, "MEMORANDUM TECNICO Y RESOLUCION DEL COMITE - CREDITO AUTOMOTRIZ v32.0", ln=True, align='C')
        pdf.ln(5)
    
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 8, " 1. RESOLUCION Y PERFIL DEL SOLICITANTE", ln=True, fill=True)
        pdf.set_font("Arial", '', 9)
        pdf.cell(95, 8, f"Solicitante: {r['cliente']} (C.I.: {r['cedula']})", 1)
        pdf.cell(95, 8, f"Fecha de Analisis: {r['fecha']}", 1, ln=True)
        pdf.cell(95, 8, f"Ocupacion: {r.get('ocupacion', '')}", 1)
        pdf.cell(95, 8, f"Empleador: {r.get('empleador', '')}", 1, ln=True)
        pdf.cell(95, 8, f"Monto Financiado: {r['monto']:,.2f} {r['moneda']}", 1)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(95, 8, f"DICTAMEN FINAL: {r['dictamen']}", 1, ln=True)
        pdf.set_font("Arial", '', 9)
        pdf.cell(95, 8, f"Tasa de Riesgo Sugerida (Sistema): {r.get('tasa_sugerida', 0):.2f}%", 1)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(95, 8, f"TASA FINAL APROBADA (Comite): {r.get('tasa_aprobada', 0):.2f}%", 1, ln=True)
        pdf.set_font("Arial", 'I', 8)
        diferencia_a = round(float(r.get('tasa_aprobada', 0)) - float(r.get('tasa_sugerida', 0)), 2)
        signo_a = "+" if diferencia_a >= 0 else ""
        pdf.cell(0, 6, f"  Diferencia Tasa Sugerida vs. Aprobada: {signo_a}{diferencia_a}% (spread de Comite)", ln=True)
    
        pdf.ln(3); pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 8, " 2. DETALLES DE LA GARANTIA PRENDARIA (VEHICULO)", ln=True, fill=True)
        pdf.set_font("Arial", '', 9)
        placa_pdf = r.get('vehiculo_placa', '') or ''
        seg_emp_pdf = r.get('seguro_empresa', '') or ''
        seg_pol_pdf = r.get('seguro_poliza', '') or ''
        seg_vig_pdf = r.get('seguro_vigencia', '') or r.get('fecha_vencimiento_seguro', '') or ''
        pdf.cell(63, 8, f"Vehiculo: {r.get('marca', '')} {r.get('modelo', '')} {r.get('anio', '')}", 1)
        pdf.cell(63, 8, f"Tipo: {r.get('tipo_vehiculo', '')}", 1)
        pdf.cell(64, 8, f"Placa: {placa_pdf if placa_pdf else 'N/A'}", 1, ln=True)
        pdf.cell(63, 8, f"VIN: {r.get('vin', '')}", 1)
        pdf.cell(63, 8, f"Precio del Vehiculo: ${r.get('precio_vehiculo', 0):,.2f}", 1)
        pdf.cell(64, 8, f"Enganche: ${r.get('enganche', 0):,.2f}", 1, ln=True)
        pdf.cell(63, 8, f"Cuota Mensual: ${r.get('cuota_est', 0):,.2f}", 1)
        pdf.cell(63, 8, f"LTV Ratio: {r.get('ltv_ratio', 0):.2f}%", 1)
        pdf.cell(64, 8, f"Plazo: {r.get('plazo_meses', 0)} meses", 1, ln=True)
        pdf.cell(63, 8, f"Aseguradora: {seg_emp_pdf if seg_emp_pdf else 'N/A'}", 1)
        pdf.cell(63, 8, f"Poliza N°: {seg_pol_pdf if seg_pol_pdf else 'N/A'}", 1)
        pdf.cell(64, 8, f"Venc. Poliza: {seg_vig_pdf if seg_vig_pdf else 'N/A'}", 1, ln=True)
    
        pdf.ln(3); pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 8, " 3. CUMPLIMIENTO (AML/CFT)", ln=True, fill=True)
        pdf.set_font("Arial", '', 9)
        pdf.cell(95, 8, f"Riesgo AML: {r['riesgo_aml']}", 1)
        pdf.cell(95, 8, f"Origen de Fondos (Enganche): {r['origen_fondos']}", 1, ln=True)
        chk_ofac = "SI" if r.get('check_sanciones') else "NO"
        chk_pep = "SI" if r.get('check_pep') else "NO"
        pdf.cell(95, 8, f"Verif. Sanciones (OFAC/ONU): {chk_ofac}", 1)
        pdf.cell(95, 8, f"Check PEP: {chk_pep}", 1, ln=True)
        if r.get('obs_comp'): pdf.multi_cell(0, 6, f"Observaciones Cumplimiento: {r['obs_comp']}", 1)
    
        pdf.ln(3); pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 8, " 4. ESTRUCTURA LEGAL Y GARANTIAS", ln=True, fill=True)
        pdf.set_font("Arial", '', 9)
        seg_txt = "SI" if r.get('seguro_vehiculo') else "NO"
        lien_txt = "SI" if r.get('registro_lien') else "NO"
        pdf.cell(63, 8, f"Seguro del Vehiculo: {seg_txt}", 1)
        pdf.cell(63, 8, f"Registro de Gravamen (Lien): {lien_txt}", 1)
        pdf.cell(64, 8, f"Venc. Seguro: {r.get('fecha_vencimiento_seguro', '')}", 1, ln=True)
        if r.get('obs_leg'): pdf.multi_cell(0, 6, f"Observaciones Legales: {r['obs_leg']}", 1)
    
        pdf.ln(3); pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 8, " 5. ANALISIS DE CAPACIDAD DE PAGO Y RIESGO", ln=True, fill=True)
        pdf.set_font("Arial", '', 9)
        str_txt = "SI (-15% Ingresos)" if r.get('estres_aplicado') else "NO"
        pdf.cell(63, 6, f"Ingreso Mensual: ${r.get('ingreso_mensual', 0):,.2f}", 1)
        pdf.cell(63, 6, f"Gastos Fijos Mens.: ${r.get('gastos_mensuales', 0):,.2f}", 1)
        pdf.cell(64, 6, f"Cuota del Credito: ${r.get('cuota_est', 0):,.2f}", 1, ln=True)
        pdf.cell(63, 6, f"DTI Ratio: {r.get('dti_ratio', 0):.2f}%", 1)
        pdf.cell(63, 6, f"Estabilidad Laboral: {r.get('estabilidad_laboral', 5.0):.1f}/10", 1)
        pdf.cell(64, 6, f"Escenario de Estres: {str_txt}", 1, ln=True)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(95, 8, f"Matriz Kaizen (Cualitativo): {r.get('rm_score', 0)}/10", 1)
        pdf.cell(95, 8, f"SCORE FINAL: {r.get('score_f', 0)} / 10", 1, ln=True)
        if r.get('obs_riesgo'): pdf.set_font("Arial", '', 9); pdf.multi_cell(0, 6, f"Observaciones Riesgo: {r['obs_riesgo']}", 1)
    
        pdf.ln(3); pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 8, " 6. CONDICIONES ESPECIALES", ln=True, fill=True)
        pdf.set_font("Arial", '', 9)
        cov_val = "null" if pd.isna(r.get('covenants')) else str(r.get('covenants', ''))
        pdf.multi_cell(0, 6, cov_val, 1)
    
        pdf.ln(12)
        pdf.cell(63, 10, "________________", align='C')
        pdf.cell(63, 10, "________________", align='C')
        pdf.cell(64, 10, "________________", ln=True, align='C')
        pdf.set_font("Arial", '', 8)
        pdf.cell(63, 5, "Firma Cumplimiento", align='C')
        pdf.cell(63, 5, "Firma Legal", align='C')
        pdf.cell(64, 5, "Firma Riesgo", align='C')
    
        if r['dictamen'] == 'APROBADO':
            pdf.ln(8); pdf.set_font("Arial", 'I', 9)
            pdf.cell(0, 5, f">>> Operacion certificada y aprobada en Comite por: {r.get('aprobado_por', '')} el dia {r.get('fecha_decision', '')} <<<", ln=True, align='C')
    
        return pdf.output(dest='S').encode('latin-1')
