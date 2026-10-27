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

    @staticmethod
    def _limpiar(txt):
        if not txt:
            return ""
        reemplazos = {
            '\u2014': '-', '\u2013': '-', '\u201c': '"', '\u201d': '"',
            '\u2018': "'", '\u2019': "'", '\u2022': '*', '\u00ba': 'o', '\u00aa': 'a',
            '\u2026': '...'
        }
        res = str(txt)
        for k, v in reemplazos.items():
            res = res.replace(k, v)
        try:
            res.encode('latin-1')
            return res
        except UnicodeEncodeError:
            return res.encode('ascii', 'replace').decode('ascii')

    @staticmethod
    def generar_contrato_corporativo(r):
        limpiar = DocumentReportService._limpiar
        pdf = KFG_PDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "KAIZEN FINANCIAL GROUP", ln=True, align='C')
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 7, "CONTRATO DE LINEA DE CREDITO Y FINANCIAMIENTO CORPORATIVO", ln=True, align='C')
        pdf.set_font("Arial", 'I', 9)
        pdf.cell(0, 5, f"Expediente Nro: CORP-{r.get('id', 'S/N')} | Fecha: {r.get('fecha', '')}", ln=True, align='C')
        pdf.ln(4)

        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 7, " 1. IDENTIFICACION DE LAS PARTES", ln=True, fill=True)
        pdf.set_font("Arial", '', 9)
        cliente = limpiar(r.get('cliente', ''))
        rif = limpiar(r.get('rif', ''))
        descripcion = limpiar(r.get('descripcion', ''))
        pdf.multi_cell(0, 5, f"Entre KAIZEN FINANCIAL GROUP, en adelante 'LA ACREEDORA', por una parte; y por la otra parte el solicitante identificado a continuacion, en adelante 'LA PARTE DEUDORA':\nRazon Social / Nombre: {cliente}\nRegistro de Informacion Fiscal (RIF): {rif}\nDestino u Objeto Declarado: {descripcion or 'Capital de trabajo y financiamiento corporativo.'}")
        pdf.ln(3)

        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 7, " 2. CONDICIONES FINANCIERAS Y MONTO OTORGADO", ln=True, fill=True)
        pdf.set_font("Arial", '', 9)
        monto = float(r.get('monto') or 0)
        moneda = limpiar(r.get('moneda') or 'USD')
        plazo = int(r.get('plazo_meses') or 36)
        tasa = float(r.get('tasa_aprobada') or r.get('tasa_sugerida') or 0)
        pdf.cell(95, 6, f"Monto Financiado: {monto:,.2f} {moneda}", 1)
        pdf.cell(95, 6, f"Plazo Acordado: {plazo} meses", 1, ln=True)
        pdf.cell(95, 6, f"Tasa de Interes Pactada: {tasa:.2f}% anual", 1)
        pdf.cell(95, 6, "Forma de Pago: Cuotas periodicas mensuales", 1, ln=True)
        pdf.ln(3)

        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 7, " 3. GARANTIAS Y COLATERALES CONSTITUIDOS", ln=True, fill=True)
        pdf.set_font("Arial", '', 9)
        v_garantia = float(r.get('v_garantia') or 0)
        ltv = float(r.get('ltv_ratio') or 0)
        venc_g = limpiar(r.get('fecha_vencimiento_garantia') or 'A termino de la obligacion')
        custodia = "SI (Originales en resguardo)" if r.get('custodia_fisica') else "NO"
        pdf.cell(95, 6, f"Valor de Garantia / Colateral: ${v_garantia:,.2f}", 1)
        pdf.cell(95, 6, f"Ratio Cobertura LTV: {ltv:.2f}%", 1, ln=True)
        pdf.cell(95, 6, f"Vencimiento de Garantia: {venc_g}", 1)
        pdf.cell(95, 6, f"Custodia Fisica de Documentos: {custodia}", 1, ln=True)

        try:
            gs = json.loads(r.get('garantias_json', '[]')) if r.get('garantias_json') else []
        except (json.JSONDecodeError, TypeError):
            gs = []
        if gs:
            pdf.set_font("Arial", 'B', 8)
            pdf.cell(0, 5, "Detalle especifico de bienes y colaterales:", ln=True)
            pdf.set_font("Arial", '', 8)
            for g in gs:
                desc = limpiar(g.get('descripcion') or g.get('desc') or '')
                val = float(g.get('valor') or 0)
                pdf.cell(0, 5, f" - {desc} (Valoracion: ${val:,.2f})", ln=True)
        if r.get('obs_leg'):
            pdf.set_font("Arial", 'I', 8)
            pdf.multi_cell(0, 4, f"Observaciones Juridicas: {limpiar(r['obs_leg'])}")
        pdf.ln(3)

        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 7, " 4. DECLARACIONES Y CLAUSULAS VINCULANTES", ln=True, fill=True)
        pdf.set_font("Arial", '', 8)
        pdf.multi_cell(0, 4, "PRIMERA: LA PARTE DEUDORA se compromete al cumplimiento irrestricto de las amortizaciones pactadas en las fechas convenidas. SEGUNDA: Los bienes y derechos dados en garantia quedan afectados expresamente a la presente obligacion crediticia hasta su total finiquito y cancelacion. TERCERA: LA PARTE DEUDORA declara bajo fe de juramento que los fondos recibidos seran destinados exclusivamente al objeto indicado y que su origen y actividad economica se encuentran apegados a la ley vigente. CUARTA: Ambas partes fijan como domicilio legal y exclusivo la jurisdiccion pactada en este instrumento.")
        pdf.ln(6)

        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 7, " 5. CONFORMIDAD Y SUSCRIPCION DE LAS PARTES", ln=True, fill=True)
        pdf.ln(12)

        # Seccion formal de firmas
        pdf.set_font("Arial", '', 9)
        pdf.cell(95, 6, "________________________________________", align='C')
        pdf.cell(95, 6, "________________________________________", ln=True, align='C')
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(95, 5, "POR LA PARTE DEUDORA (CLIENTE)", align='C')
        pdf.cell(95, 5, "POR KAIZEN FINANCIAL GROUP", ln=True, align='C')
        pdf.set_font("Arial", '', 8)
        pdf.cell(95, 4, f"Nombre / Repr.: {cliente[:45]}", align='C')
        pdf.cell(95, 4, "Apoderado / Representante Legal", ln=True, align='C')
        pdf.cell(95, 4, f"RIF / C.I.: {rif}", align='C')
        pdf.cell(95, 4, "Kaizen Financial Group", ln=True, align='C')
        pdf.cell(95, 4, "Firma y Sello Comercial", align='C')
        pdf.cell(95, 4, "Firma Autorizada", ln=True, align='C')
        pdf.ln(6)
        pdf.cell(95, 5, "Huella Dactilar / Sello:", align='C')
        pdf.cell(95, 5, "Fecha de Suscripcion: _____/_____/________", ln=True, align='C')
        pdf.cell(95, 8, "[                        ]", align='C')
        pdf.cell(95, 8, "", ln=True, align='C')

        return pdf.output(dest='S').encode('latin-1')

    @staticmethod
    def generar_contrato_auto(r):
        limpiar = DocumentReportService._limpiar
        pdf = KFG_PDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "KAIZEN FINANCIAL GROUP", ln=True, align='C')
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 7, "CONTRATO DE FINANCIAMIENTO AUTOMOTRIZ CON RESERVA DE DOMINIO", ln=True, align='C')
        pdf.set_font("Arial", 'I', 9)
        pdf.cell(0, 5, f"Expediente Nro: AUTO-{r.get('id', 'S/N')} | Fecha: {r.get('fecha', '')}", ln=True, align='C')
        pdf.ln(4)

        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 7, " 1. IDENTIFICACION DE LAS PARTES", ln=True, fill=True)
        pdf.set_font("Arial", '', 9)
        cliente = limpiar(r.get('cliente', ''))
        cedula = limpiar(r.get('cedula', ''))
        ocupacion = limpiar(r.get('ocupacion', ''))
        empleador = limpiar(r.get('empleador', ''))
        telefono = limpiar(r.get('telefono', ''))
        pdf.multi_cell(0, 5, f"Entre KAIZEN FINANCIAL GROUP, en adelante 'LA ACREEDORA'; y por la otra parte el comprador y solicitante individualizado a continuacion, en adelante 'EL PRESTATARIO':\nNombre y Apellido: {cliente}\nCedula de Identidad / RIF: {cedula}\nOcupacion: {ocupacion or 'N/A'} | Empleador: {empleador or 'N/A'}\nTelefono de Contacto: {telefono or 'N/A'}")
        pdf.ln(3)

        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 7, " 2. CONDICIONES FINANCIERAS Y VEHICULO OBJETO DEL CREDITO", ln=True, fill=True)
        pdf.set_font("Arial", '', 9)
        marca = limpiar(r.get('marca', ''))
        modelo = limpiar(r.get('modelo', ''))
        anio = r.get('anio', '')
        vin = limpiar(r.get('vin', ''))
        placa = limpiar(r.get('vehiculo_placa', '')) or 'EN TRAMITE'
        tipo_v = limpiar(r.get('tipo_vehiculo', 'Nuevo'))
        precio = float(r.get('precio_vehiculo') or 0)
        enganche = float(r.get('enganche') or 0)
        monto = float(r.get('monto') or (precio - enganche))
        plazo = int(r.get('plazo_meses') or 36)
        moneda = limpiar(r.get('moneda') or 'USD')

        pdf.cell(95, 6, f"Vehiculo: {marca} {modelo} ({anio})", 1)
        pdf.cell(95, 6, f"Condicion: {tipo_v} | Placa: {placa}", 1, ln=True)
        pdf.cell(95, 6, f"Serial Carroceria / VIN: {vin}", 1)
        pdf.cell(95, 6, f"Precio del Vehiculo: ${precio:,.2f} {moneda}", 1, ln=True)
        pdf.cell(95, 6, f"Inicial / Enganche: ${enganche:,.2f} {moneda}", 1)
        pdf.cell(95, 6, f"Monto Financiado: ${monto:,.2f} {moneda}", 1, ln=True)
        pdf.cell(95, 6, f"Plazo Otorgado: {plazo} meses", 1)
        cuota = float(r.get('cuota_est') or 0)
        pdf.cell(95, 6, f"Cuota Mensual Estimada: ${cuota:,.2f}", 1, ln=True)
        pdf.ln(3)

        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 7, " 3. GRAVAMEN PRENDARIO, POLIZA DE SEGURO Y COBERTURA", ln=True, fill=True)
        pdf.set_font("Arial", '', 9)
        seg_emp = limpiar(r.get('seguro_empresa') or 'A designar')
        seg_pol = limpiar(r.get('seguro_poliza') or 'Pendiente emision')
        seg_vig = limpiar(r.get('seguro_vigencia') or r.get('fecha_vencimiento_seguro') or 'Anual renovable')
        lien_txt = "CONSTITUIDO a favor de KAIZEN FINANCIAL GROUP" if r.get('registro_lien') else "EN TRAMITE DE REGISTRO"
        seg_txt = "VERIFICADO Y VIGENTE" if r.get('seguro_vehiculo') else "OBLIGATORIO PREVIO A ENTREGA"
        ltv = float(r.get('ltv_ratio') or 0)

        pdf.cell(95, 6, f"Aseguradora: {seg_emp}", 1)
        pdf.cell(95, 6, f"Poliza Nro: {seg_pol}", 1, ln=True)
        pdf.cell(95, 6, f"Vigencia del Seguro: {seg_vig}", 1)
        pdf.cell(95, 6, f"Ratio LTV: {ltv:.2f}%", 1, ln=True)
        pdf.cell(95, 6, f"Estatus Cobertura: {seg_txt}", 1)
        pdf.cell(95, 6, f"Gravamen (Lien): {lien_txt}", 1, ln=True)
        if r.get('obs_leg'):
            pdf.set_font("Arial", 'I', 8)
            pdf.multi_cell(0, 4, f"Observaciones Juridicas: {limpiar(r['obs_leg'])}")
        pdf.ln(3)

        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 7, " 4. CLAUSULAS CONTRACTUALES Y OBLIGACIONES", ln=True, fill=True)
        pdf.set_font("Arial", '', 8)
        pdf.multi_cell(0, 4, "PRIMERA: EL PRESTATARIO se obliga a pagar las cuotas mensuales en las fechas estipuladas. SEGUNDA: El vehiculo queda sujeto a RESERVA DE DOMINIO y GRAVAMEN PRENDARIO a favor de LA ACREEDORA hasta la extincion total de la deuda. TERCERA: EL PRESTATARIO mantendra vigente e ininterrumpida la poliza de seguro a todo riesgo con endoso preferente a favor de LA ACREEDORA. CUARTA: EL PRESTATARIO declara que los fondos aportados y su ingreso provienen de actividades licitas.")
        pdf.ln(6)

        pdf.set_font("Arial", 'B', 10)
        pdf.cell(0, 7, " 5. CONFORMIDAD Y SUSCRIPCION DE LAS PARTES", ln=True, fill=True)
        pdf.ln(12)

        # Seccion de firmas
        pdf.set_font("Arial", '', 9)
        pdf.cell(95, 6, "________________________________________", align='C')
        pdf.cell(95, 6, "________________________________________", ln=True, align='C')
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(95, 5, "POR EL PRESTATARIO (CLIENTE)", align='C')
        pdf.cell(95, 5, "POR KAIZEN FINANCIAL GROUP", ln=True, align='C')
        pdf.set_font("Arial", '', 8)
        pdf.cell(95, 4, f"Nombre: {cliente[:45]}", align='C')
        pdf.cell(95, 4, "Representante Legal / Apoderado", ln=True, align='C')
        pdf.cell(95, 4, f"C.I. / R.I.F.: {cedula}", align='C')
        pdf.cell(95, 4, "Kaizen Financial Group", ln=True, align='C')
        pdf.cell(95, 4, "Firma del Titular", align='C')
        pdf.cell(95, 4, "Firma Autorizada", ln=True, align='C')
        pdf.ln(6)
        pdf.cell(95, 5, "Huella Dactilar:", align='C')
        pdf.cell(95, 5, "Fecha de Suscripcion: _____/_____/________", ln=True, align='C')
        pdf.cell(95, 8, "[                        ]", align='C')
        pdf.cell(95, 8, "", ln=True, align='C')

        return pdf.output(dest='S').encode('latin-1')

