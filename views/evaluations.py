import streamlit as st
import pandas as pd
import json
from datetime import datetime
from utils import page_header, section_divider, badge, paginate_controls, APP_ICONS
from database.daos_sqlserver import ExpedienteCorporativoDAO, ExpedienteAutomotrizDAO
from services.risk_service import AmortizationService
from services.document_service import DocumentReportService
from services.metrics_service import get_sidebar_metrics

def sig_badge(val):
    return "✅" if val else "⏳"

@st.dialog("Confirmar Aprobación")
def modal_aprobar(r, tipo, tasa, plazo):
    st.markdown(f"### ¿Confirmar aprobación para **{r['cliente']}**?")
    st.write(f"Se procederá a registrar la decisión final y generar el plan de amortización.")
    st.info(f"**Monto:** {r['moneda']} {r['monto']:,.2f}  \n**Tasa:** {tasa}%  \n**Plazo:** {plazo} meses")
    
    if st.button("Confirmar Firma y Proceder", type="primary", width='stretch'):
        with st.spinner("Registrando decisión y generando plan de amortización..."):
            fh = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if tipo == 'corp':
                ExpedienteCorporativoDAO.update_dictamen(
                    exp_id=r['id'], dictamen='APROBADO',
                    aprobado_por=st.session_state.get('current_user', 'Admin'),
                    fecha=fh, tasa=tasa, plazo=plazo
                )
                AmortizationService.generar(r['id'], 'corp', float(r['monto']), float(tasa), int(plazo), fh)
            else:
                ExpedienteAutomotrizDAO.update_dictamen(
                    exp_id=r['id'], dictamen='APROBADO',
                    aprobado_por=st.session_state.get('current_user', 'Admin'),
                    fecha=fh, tasa=tasa
                )
                # El plazo en auto viene del expediente original si no se cambia, 
                # pero aquí usamos el valor pasado
                AmortizationService.generar(r['id'], 'auto', float(r['monto']), float(tasa), int(plazo), fh)
        
        st.success("Expediente Aprobado Exitosamente")
        get_sidebar_metrics.clear()
        st.rerun()

@st.dialog("Confirmar Rechazo")
def modal_rechazar(r, tipo):
    st.error(f"### ¿Está seguro de RECHAZAR a {r['cliente']}?")
    st.write("Esta acción es irreversible y el expediente quedará marcado como rechazado.")
    
    if st.button("Confirmar Rechazo Definitivo", type="primary", width='stretch'):
        with st.spinner("Procesando rechazo..."):
            fh = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if tipo == 'corp':
                ExpedienteCorporativoDAO.update_dictamen(
                    exp_id=r['id'], dictamen='RECHAZADO',
                    aprobado_por=st.session_state.get('current_user', 'Admin'),
                    fecha=fh
                )
            else:
                ExpedienteAutomotrizDAO.update_dictamen(
                    exp_id=r['id'], dictamen='RECHAZADO',
                    aprobado_por=st.session_state.get('current_user', 'Admin'),
                    fecha=fh
                )
        st.success("Expediente Rechazado")
        get_sidebar_metrics.clear()
        st.rerun()

# Etapas a las que esta vista puede devolver un expediente
ETAPAS_DEVOLUCION = ["Comercial", "Cumplimiento", "Legal", "Riesgo"]


@st.dialog("Devolver Expediente")
def modal_devolver_expediente(r, tipo):
    """Devuelve el expediente a una etapa previa con justificacion obligatoria."""
    st.warning(f"### Devolver **{r['cliente']}** para correccion")
    st.write(f"Monto: **{r.get('moneda', 'USD')} {r['monto']:,.2f}** "
             f"&nbsp;·&nbsp; Creado: {r.get('fecha', '')}")

    etapa = st.selectbox("Etapa destino", ETAPAS_DEVOLUCION,
                         key=f"dev_etapa_com_{tipo}_{r['id']}")
    obs = st.text_area("Justificacion de la devolucion (obligatoria)",
                       key=f"dev_obs_com_{tipo}_{r['id']}", height=110)

    if st.button("Confirmar Devolucion", type="primary", width='stretch'):
        if not obs.strip():
            st.warning("Debe indicar la justificacion de la devolucion.")
        else:
            dao = ExpedienteCorporativoDAO if tipo == 'corp' else ExpedienteAutomotrizDAO
            with st.spinner("Registrando devolucion..."):
                dao.devolver_expediente(
                    exp_id=r['id'], etapa_destino=etapa, observaciones=obs.strip(),
                    usuario=st.session_state.get('current_user', 'Admin'),
                    fecha=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            get_sidebar_metrics.clear()
            st.success(f"Expediente devuelto a {etapa}.")
            st.rerun()


def _render_card_corp(r):
    """Tarjeta de un expediente corporativo (info, acciones, plan de pagos)."""
    with st.container(border=True):
        c1, c2 = st.columns([2, 1])
        sc = sig_badge(r['status_comp'])
        sl = sig_badge(r['status_leg'])
        sr = sig_badge(r['status_riesgo'])

        # Columna 1: Info y Aprobador
        with c1:
            desc_val = r.get('descripcion', '')
            desc_text = desc_val if desc_val and str(desc_val).strip().lower() != 'nan' and str(desc_val).strip() else 'Sin descripción'
            desc_html = f"<span style='font-size:0.85em;color:#334155;font-style:italic;'><strong>Descripción:</strong> {desc_text}</span><br>"
            st.markdown(
                f"**{r['cliente']}** &nbsp; {badge(r['dictamen'])} &nbsp; "
                f"<span style='color:#64748B;font-size:0.85em'>{r['moneda']} {r['monto']:,.2f}</span><br>"
                f"<span style='font-size:0.83em;color:#64748B'>Creado: {r.get('fecha', '')}</span><br>"
                f"{desc_html}"
                f"<span style='font-size:0.83em;color:#475569'>"
                f"Firmas: C:{sc} L:{sl} R:{sr} &nbsp;|&nbsp; "
                f"Score: <strong>{r.get('score_f', 'N/A')}</strong> &nbsp;|&nbsp; "
                f"DSCR: <strong>{r.get('dscr', 0):.2f}x</strong></span>",
                unsafe_allow_html=True)

            if r['dictamen'] == 'APROBADO':
                st.caption(f"✅ **Aprobado por:** {r.get('aprobado_por', 'N/A')} &nbsp; | &nbsp;  **Fecha:** {r.get('fecha_decision', 'N/A')}")
            elif r['dictamen'] == 'RECHAZADO':
                st.caption(f"❌ **Rechazado por:** {r.get('aprobado_por', 'N/A')} &nbsp; | &nbsp; **Fecha:** {r.get('fecha_decision', 'N/A')}")

        # Columna 2: Acciones
        with c2:
            listo = (r['status_comp'] == 1 and r['status_leg'] == 1 and r['status_riesgo'] == 1)

            if r['dictamen'] == 'PENDIENTE':
                ic1, ic2 = st.columns(2)
                t_ap = ic1.number_input("Tasa %", value=float(r.get('tasa_sugerida', 12)), key=f"c_tap_{r['id']}")
                plazo_c_ap = ic2.number_input("Meses", min_value=1, value=int(r.get('plazo_meses', 36)), key=f"c_plz_{r['id']}")

                btn_col1, btn_col2, btn_col3 = st.columns(3)
                if btn_col1.button("✅ Aprobar", key=f"c_ap_{r['id']}", disabled=not listo, width='stretch'):
                    modal_aprobar(r, 'corp', t_ap, plazo_c_ap)
                if btn_col2.button("❌ Rechazar", key=f"c_rj_{r['id']}", width='stretch'):
                    modal_rechazar(r, 'corp')
                if btn_col3.button("↩️ Devolver", key=f"c_dev_{r['id']}", width='stretch'):
                    modal_devolver_expediente(r, 'corp')
            else:
                act_col1, act_col2 = st.columns([3, 1])
                pdf_key = f"pdf_corp_{r['id']}"
                if pdf_key not in st.session_state:
                    if act_col1.button("📄 Generar Acta", key=f"c_gen_pdf_{r['id']}", width='stretch'):
                        with st.spinner("Generando PDF..."):
                            try:
                                st.session_state[pdf_key] = DocumentReportService.generar_pdf_corporativo(r)
                                st.rerun()
                            except Exception as e:
                                st.error("Error PDF")
                else:
                    act_col1.download_button("📥 Descargar Acta", st.session_state[pdf_key], f"Acta_{r['cliente']}.pdf", "application/pdf", key=f"c_pdf_{r['id']}", width='stretch')

                if act_col2.button("🗑️", key=f"c_del_{r['id']}", width='stretch'):
                    ExpedienteCorporativoDAO.delete(r['id'])
                    st.rerun()

        if r['dictamen'] == 'APROBADO':
            with st.expander(f"Plan de Amortización — {r['cliente'].upper()}"):
                from database.daos_sqlserver import PlanPagoDAO
                df_pp = pd.DataFrame(PlanPagoDAO.get_by_expediente(r['id'], 'corp'))
                if df_pp.empty:
                    if st.button("Generar Plan", key=f"c_gen_{r['id']}"):
                        AmortizationService.generar(r['id'], 'corp', float(r['monto']), float(r.get('tasa_aprobada', 12)), int(r.get('plazo_meses', 36) if pd.notna(r.get('plazo_meses')) else 36), r.get('fecha_decision'))
                        st.rerun()
                else:
                    pp1, pp2, pp3 = st.columns(3)
                    pp1.metric("Total Cuotas", len(df_pp))
                    pp2.metric("Cuota Mensual", f"${df_pp['cuota'].iloc[0]:,.2f}")
                    pp3.metric("Total a Pagar", f"${df_pp['cuota'].sum():,.2f}")
                    df_show = df_pp[['periodo', 'fecha_pago', 'cuota', 'capital', 'interes', 'saldo']].copy()
                    df_show.columns = ['N°', 'Fecha', 'Cuota', 'Capital', 'Interés', 'Saldo']
                    st.dataframe(df_show.style.format({'Cuota': '${:,.2f}', 'Capital': '${:,.2f}', 'Interés': '${:,.2f}', 'Saldo': '${:,.2f}'}), width='stretch', hide_index=True)


def _render_card_auto(r):
    """Tarjeta de un expediente automotriz (info, acciones, plan de pagos)."""
    with st.container(border=True):
        ca1, ca2 = st.columns([2, 1])
        sc_a = sig_badge(r['status_comp'])
        sl_a = sig_badge(r['status_leg'])
        sr_a = sig_badge(r['status_riesgo'])

        # Columna 1: Info y Aprobador
        with ca1:
            desc_val_a = r.get('descripcion', '')
            desc_text_a = desc_val_a if desc_val_a and str(desc_val_a).strip().lower() != 'nan' and str(desc_val_a).strip() else 'Sin descripción'
            desc_html_a = f"<span style='font-size:0.85em;color:#334155;font-style:italic;'><strong>Descripción:</strong> {desc_text_a}</span><br>"
            rif_str = str(r.get('cedula', '')).upper() if pd.notna(r.get('cedula')) else ''
            ca1.markdown(
                f"**{r['cliente']}** &nbsp; | RIF: {rif_str} &nbsp; {badge(r['dictamen'])} &nbsp; "
                f"<span style='color:#64748B;font-size:0.85em'>{r['moneda']} {r['monto']:,.2f}</span><br>"
                f"<span style='font-size:0.83em;color:#64748B'> Creado: {r.get('fecha', '')}</span><br>"
                f"{desc_html_a}"
                f"<span style='font-size:0.83em;color:#64748B'>"
                f"{APP_ICONS['automotriz']} {r.get('marca','')} {r.get('modelo','')} {r.get('anio','')}</span><br>"
                f"<span style='font-size:0.83em;color:#475569'>"
                f"Firmas: C:{sc_a} L:{sl_a} R:{sr_a} &nbsp;|&nbsp; "
                f"Score: <strong>{r.get('score_f', 'N/A')}</strong> &nbsp;|&nbsp; "
                f"DTI: <strong>{r.get('dti_ratio', 0):.2f}%</strong></span>",
                unsafe_allow_html=True)

            if r['dictamen'] == 'APROBADO':
                st.caption(f"✅ **Aprobado por:** {r.get('aprobado_por', 'N/A')} &nbsp; | &nbsp;  **Fecha:** {r.get('fecha_decision', 'N/A')}")
            elif r['dictamen'] == 'RECHAZADO':
                st.caption(f"❌ **Rechazado por:** {r.get('aprobado_por', 'N/A')} &nbsp; | &nbsp;  **Fecha:** {r.get('fecha_decision', 'N/A')}")

        # Columna 2: Acciones
        with ca2:
            listo_a = (r['status_comp'] == 1 and r['status_leg'] == 1 and r['status_riesgo'] == 1)

            if r['dictamen'] == 'PENDIENTE':
                iac1, iac2 = st.columns(2)
                t_ap_a = iac1.number_input("Tasa %", value=float(r.get('tasa_sugerida', 12)), key=f"ca_tap_{r['id']}")
                # En auto el plazo suele ser fijo o viene del expediente, pero lo mostramos
                p_auto_val = int(r.get('plazo_meses', 48))
                iac2.number_input("Meses", value=p_auto_val, key=f"ca_plz_show_{r['id']}", disabled=True)

                abtn_col1, abtn_col2, abtn_col3 = st.columns(3)
                if abtn_col1.button("✅ Aprobar", key=f"ca_ap_{r['id']}", disabled=not listo_a, width='stretch'):
                    p_auto = int(r.get('plazo_meses', 48))
                    modal_aprobar(r, 'auto', t_ap_a, p_auto)
                if abtn_col2.button("❌ Rechazar", key=f"ca_rj_{r['id']}", width='stretch'):
                    modal_rechazar(r, 'auto')
                if abtn_col3.button("↩️ Devolver", key=f"ca_dev_{r['id']}", width='stretch'):
                    modal_devolver_expediente(r, 'auto')
            else:
                act_col1_a, act_col2_a = st.columns([3, 1])
                pdf_key_a = f"pdf_auto_{r['id']}"
                if pdf_key_a not in st.session_state:
                    if act_col1_a.button("📄 Generar Acta", key=f"ca_gen_pdf_{r['id']}", width='stretch'):
                        with st.spinner("Generando PDF..."):
                            try:
                                st.session_state[pdf_key_a] = DocumentReportService.generar_pdf_auto(r)
                                st.rerun()
                            except Exception as e:
                                st.error("Error PDF")
                else:
                    act_col1_a.download_button("📥 Descargar Acta", st.session_state[pdf_key_a], f"Acta_{r['cliente']}.pdf", "application/pdf", key=f"ca_pdf_{r['id']}", width='stretch')

                if act_col2_a.button("🗑️", key=f"ca_del_{r['id']}", width='stretch'):
                    ExpedienteAutomotrizDAO.delete(r['id'])
                    st.rerun()

        if r['dictamen'] == 'APROBADO':
            rif_str = str(r.get('cedula', '')).upper() if pd.notna(r.get('cedula')) else ''
            with st.expander(f"Plan de Amortización — {r['cliente']} | RIF: {rif_str} | {r.get('marca','')} {r.get('modelo','')}"):
                from database.daos_sqlserver import PlanPagoDAO
                df_pp = pd.DataFrame(PlanPagoDAO.get_by_expediente(r['id'], 'auto'))
                if df_pp.empty:
                    if st.button("Generar Plan", key=f"ca_gen_{r['id']}"):
                        AmortizationService.generar(r['id'], 'auto', float(r['monto']), float(r.get('tasa_aprobada', 12)), int(r.get('plazo_meses', 48) if pd.notna(r.get('plazo_meses')) else 48), r.get('fecha_decision'))
                        st.rerun()
                else:
                    ap1, ap2, ap3, ap4 = st.columns(4)
                    ap1.metric("Plazo", f"{len(df_pp)} meses")
                    ap2.metric("Cuota Mensual", f"${df_pp['cuota'].iloc[0]:,.2f}")
                    ap3.metric("Total Intereses", f"${df_pp['interes'].sum():,.2f}")
                    ap4.metric("Total a Pagar", f"${df_pp['cuota'].sum():,.2f}")
                    df_show = df_pp[['periodo', 'fecha_pago', 'cuota', 'capital', 'interes', 'saldo']].copy()
                    df_show.columns = ['N°', 'Fecha', 'Cuota', 'Capital', 'Interés', 'Saldo']
                    st.dataframe(df_show.style.format({'Cuota': '${:,.2f}', 'Capital': '${:,.2f}', 'Interés': '${:,.2f}', 'Saldo': '${:,.2f}'}), width='stretch', hide_index=True)


def _render_lista_corp(dictamen, cliente, firmas_completas, key_prefix, page_size=10):
    """Cuenta, pagina y renderiza los expedientes corporativos de una sub-pestana."""
    total = ExpedienteCorporativoDAO.count(
        dictamen=dictamen, cliente=cliente, firmas_completas=firmas_completas)
    if total == 0:
        st.info("No hay expedientes con los filtros seleccionados.")
        return
    page = paginate_controls(total, page_size=page_size, key_prefix=key_prefix)
    df_page = ExpedienteCorporativoDAO.get_paginated(
        page=page, page_size=page_size, dictamen=dictamen, cliente=cliente,
        firmas_completas=firmas_completas)
    for _, r in df_page.iterrows():
        _render_card_corp(r)


def _render_lista_auto(dictamen, cliente, firmas_completas, key_prefix, page_size=10):
    """Cuenta, pagina y renderiza los expedientes automotrices de una sub-pestana."""
    total = ExpedienteAutomotrizDAO.count(
        dictamen=dictamen, cliente=cliente, firmas_completas=firmas_completas)
    if total == 0:
        st.info("No hay expedientes con los filtros seleccionados.")
        return
    page = paginate_controls(total, page_size=page_size, key_prefix=key_prefix)
    df_page = ExpedienteAutomotrizDAO.get_paginated(
        page=page, page_size=page_size, dictamen=dictamen, cliente=cliente,
        firmas_completas=firmas_completas)
    for _, r in df_page.iterrows():
        _render_card_auto(r)


def show():
    page_header("comite", "Credit Committee & BI Decision Center",
                "Panel de aprobaciones y Business Intelligence de cartera",
                "KFG Risk Architect · Comité")

    with st.spinner("Cargando indicadores de cartera y expedientes listos..."):
        df_corp = ExpedienteCorporativoDAO.get_all_as_df()  # solo para KPIs y listas de filtros
        df_auto = ExpedienteAutomotrizDAO.get_all_as_df()   # solo para KPIs y listas de filtros
    
    if df_corp.empty:
        df_corp_ap = pd.DataFrame()
        total_corp = 0
        pend_corp = 0
    else:
        df_corp_ap = df_corp[df_corp['dictamen'] == 'APROBADO']
        total_corp = df_corp_ap['monto'].sum() if not df_corp_ap.empty else 0
        pend_corp = len(df_corp[df_corp['dictamen'] == 'PENDIENTE'])

    if df_auto.empty:
        df_auto_ap = pd.DataFrame()
        total_auto_ap = 0
        pend_auto = 0
    else:
        df_auto_ap = df_auto[df_auto['dictamen'] == 'APROBADO']
        total_auto_ap = df_auto_ap['monto'].sum() if not df_auto_ap.empty else 0
        pend_auto = len(df_auto[df_auto['dictamen'] == 'PENDIENTE'])
        
    pendientes = pend_corp + pend_auto

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Cartera Corporativa Aprobada", f"${total_corp:,.2f}")
    k2.metric("Cartera Automotriz Aprobada", f"${total_auto_ap:,.2f}")
    k3.metric("Cartera Total Aprobada", f"${total_corp + total_auto_ap:,.2f}")
    k4.metric("Expedientes Pendientes", pendientes)
    bi1, bi2 = st.columns(2)
    with bi1:
        if not df_corp_ap.empty:
            st.write("**Distribución Colateral Corporativo**")
            gar_data = {}
            for _, row in df_corp_ap.iterrows():
                try: gs = json.loads(row['garantias_json']) if pd.notna(row['garantias_json']) and row['garantias_json'] else []
                except Exception: gs = []
                if gs:
                    p_type = gs[0].get('tipo', 'Otro')
                    gar_data[p_type] = gar_data.get(p_type, 0) + row['monto']
            if gar_data:
                df_chart = pd.DataFrame(list(gar_data.items()), columns=['Tipo', 'Monto']).set_index('Tipo')
                st.bar_chart(df_chart)
            else:
                st.info("Sin garantías registradas.")
        else:
            st.info("Sin cartera corporativa aprobada.")
            
    with bi2:
        if not df_auto_ap.empty and 'tipo_vehiculo' in df_auto_ap.columns:
            st.write("**Distribución Automotriz por Tipo de Vehículo**")
            tipo_data = df_auto_ap.groupby('tipo_vehiculo')['monto'].sum()
            if not tipo_data.empty:
                st.bar_chart(tipo_data)
        else:
            st.info("Sin cartera automotriz aprobada.")

    st.markdown("---")

    # ── Cálculo de expedientes LISTOS para Comité (3 firmas) ──
    listos_c = df_corp[(df_corp['status_comp']==1)&(df_corp['status_leg']==1)&(df_corp['status_riesgo']==1)&(df_corp['dictamen']=='PENDIENTE')] if not df_corp.empty else pd.DataFrame()
    listos_a = df_auto[(df_auto['status_comp']==1)&(df_auto['status_leg']==1)&(df_auto['status_riesgo']==1)&(df_auto['dictamen']=='PENDIENTE')] if not df_auto.empty else pd.DataFrame()
    
    count_corp_listos = len(listos_c)
    count_auto_listos = len(listos_a)

    label_corp = f"* **Créditos Corporativos ({count_corp_listos})**" if count_corp_listos > 0 else "Créditos Corporativos"
    label_auto = f"* **Créditos Automotrices ({count_auto_listos})**" if count_auto_listos > 0 else "Créditos Automotrices"

    tab_corp, tab_auto = st.tabs([label_corp, label_auto])

    # Panel Corporativo
    with tab_corp:
        if df_corp.empty:
            st.info("No hay expedientes corporativos.")
        else:
            # Filtros por sección
            fc1, fc2 = st.columns([1, 2])
            f_corp = fc1.selectbox("Status:", ["Todos", "PENDIENTE", "APROBADO", "RECHAZADO"], key="f_eval_corp")
            empresas_corp = ["Todas"] + sorted(df_corp['cliente'].dropna().unique().tolist())
            f_emp_corp = fc2.selectbox("Empresa / Cliente:", empresas_corp, key="f_emp_corp")

            # Paginación REAL: count + get_paginated con filtros enviados al SQL
            PAGE_SIZE = 10
            d_corp = f_corp if f_corp != "Todos" else None
            e_corp = f_emp_corp if f_emp_corp != "Todas" else None
            # Sub-pestanas por estado de firmas
            sub_listos_c, sub_incompletos_c = st.tabs(
                ["Listos (3 Firmas)", "Firmas Incompletas"])

            with sub_listos_c:
                _render_lista_corp(d_corp, e_corp, True, "eval_corp_listos", PAGE_SIZE)

            with sub_incompletos_c:
                _render_lista_corp(d_corp, e_corp, False, "eval_corp_incompletos", PAGE_SIZE)

    # Panel Automotriz
    with tab_auto:
        if df_auto.empty:
            st.info("No hay expedientes automotrices.")
        else:
            # Filtros por sección
            fa1, fa2 = st.columns([1, 2])
            f_auto = fa1.selectbox("Status:", ["Todos", "PENDIENTE", "APROBADO", "RECHAZADO"], key="f_eval_auto")
            clientes_auto = ["Todos"] + sorted(df_auto['cliente'].dropna().unique().tolist())
            f_cli_auto = fa2.selectbox("Empresa / Cliente:", clientes_auto, key="f_cli_auto")

            # Paginación REAL
            PAGE_SIZE = 10
            d_auto = f_auto if f_auto != "Todos" else None
            e_auto = f_cli_auto if f_cli_auto != "Todos" else None
            # Sub-pestanas por estado de firmas
            sub_listos_a, sub_incompletos_a = st.tabs(
                ["Listos (3 Firmas)", "Firmas Incompletas"])

            with sub_listos_a:
                _render_lista_auto(d_auto, e_auto, True, "eval_auto_listos", PAGE_SIZE)

            with sub_incompletos_a:
                _render_lista_auto(d_auto, e_auto, False, "eval_auto_incompletos", PAGE_SIZE)
