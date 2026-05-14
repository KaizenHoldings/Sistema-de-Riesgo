import streamlit as st
import pandas as pd
from utils import page_header, section_divider, paginate_dataframe, APP_ICONS
from database.daos_sqlserver import ExpedienteCorporativoDAO, ExpedienteAutomotrizDAO, ConfigParametroDAO

@st.dialog("Confirmar Análisis de Riesgo")
def modal_firmar_riesgo(r, tipo, data):
    st.markdown(f"### ¿Confirmar firma de riesgo para **{r['cliente']}**?")
    st.write("Se registrarán los indicadores financieros y el score calculado para la evaluación final.")
    st.info(f"**Score:** {data['score']} / 10  \n**Tasa Sugerida:** {data['tasa']}%")
    
    if st.button("Confirmar Firma de Riesgo", type="primary", use_container_width=True):
        with st.spinner("Registrando análisis de riesgo y scoring..."):
            if tipo == 'corp':
                ExpedienteCorporativoDAO.update_riesgo(
                    exp_id=r['id'],
                    score_f=data['score'],
                    rm_score=data['rm_score'],
                    ac=data['ac'], pc=data['pc'], eb=data['eb'], gf=data['gf'], pt=data['pt'], pa=data['pa'],
                    obs_riesgo=data['obs'],
                    cuota_est=data['cuota'],
                    ing_mensuales=data['ing'],
                    moneda=data['mon'],
                    estres_aplicado=data['estres'],
                    dscr=data['dscr'],
                    margen_ebitda=data['margen'],
                    tasa_sugerida=data['tasa'],
                    covenants=data['cov']
                )
            else:
                ExpedienteAutomotrizDAO.update_riesgo(
                    exp_id=r['id'],
                    score_f=data['score'],
                    rm_score=data['rm_score'],
                    ingreso_mensual=data['ing'],
                    gastos_mensuales=data['gastos'],
                    cuota_est=data['cuota'],
                    dti_ratio=data['dti'],
                    estabilidad_laboral=data['estabilidad'],
                    estres_aplicado=data['estres'],
                    tasa_sugerida=data['tasa'],
                    moneda=data['mon'],
                    obs_riesgo=data['obs'],
                    covenants=data['cov']
                )
            st.success("✅ Análisis de Riesgo registrado.")
            st.rerun()

def show():
    page_header("risk", "Análisis de Riesgo & Scoring",
                "Modelos cuantitativos de calificación crediticia",
                "KFG Risk Architect · Riesgo")
                
    # Inicializar parámetros de riesgo en session_state si no existen
    if 'w_liq' not in st.session_state:
        params = ConfigParametroDAO.get_all_as_dict()
        for k, v in params.items():
            if k not in st.session_state:
                try: st.session_state[k] = float(v)
                except ValueError: st.session_state[k] = v
                
    with st.spinner("Cargando expedientes y modelos de scoring..."):
        df_corp = ExpedienteCorporativoDAO.get_all_as_df()
        df_auto = ExpedienteAutomotrizDAO.get_all_as_df()

    tab_corp, tab_auto = st.tabs(["Créditos Corporativos", "Créditos Automotrices"])

    with tab_corp:
        if not df_corp.empty:
            df_r = df_corp[(df_corp['status_riesgo'] == 0) & (df_corp['dictamen'] == 'PENDIENTE')]
        else:
            df_r = pd.DataFrame()

        if df_r.empty:
            st.info("No hay expedientes corporativos pendientes en Riesgo.")
        else:
            df_r_pag = paginate_dataframe(df_r, page_size=10, key_prefix="risk_corp")
            for _, r in df_r_pag.iterrows():
                with st.expander(f"{r['cliente'].upper()} | RIF: {r['rif'].upper()} | ${r['monto']:,.2f}"):
                    st.markdown(f"#### {APP_ICONS['corporativo']} Análisis de Riesgo Financiero", unsafe_allow_html=True)
                    st.markdown("**1. Flujo de Caja (Capacidad de Pago)**")
                    cf1, cf2, cf3 = st.columns(3)
                    mon = cf1.selectbox("Moneda", ["USD", "Bs."], key=f"r_mon_{r['id']}")
                    ing_m = cf2.number_input("Ingresos Mensuales", min_value=0.0, key=f"r_ingm_{r['id']}")
                    cuota_est = cf3.number_input("Cuota Mensual del Crédito", min_value=0.0, key=f"r_cuota_{r['id']}")

                    st.markdown("**2. Balance Anualizado**")
                    c1, c2, c3 = st.columns(3)
                    ac = c1.number_input("Act. Corrientes", value=float(r['ac'] if pd.notna(r['ac']) else 0), key=f"r_ac_{r['id']}")
                    pc = c1.number_input("Pas. Corrientes", value=max(float(r['pc'] if pd.notna(r['pc']) else 1), 1.0), key=f"r_pc_{r['id']}")
                    eb = c2.number_input("EBITDA", value=float(r['eb'] if pd.notna(r['eb']) else 0), key=f"r_eb_{r['id']}")
                    gf = c2.number_input("Gastos Financieros", value=max(float(r['gf'] if pd.notna(r['gf']) else 1), 1.0), key=f"r_gf_{r['id']}")
                    pt = c3.number_input("Pasivos Totales", value=float(r['pt'] if pd.notna(r['pt']) else 0), key=f"r_pt_{r['id']}")
                    pa = c3.number_input("Patrimonio", value=max(float(r['pa'] if pd.notna(r['pa']) else 1), 1.0), key=f"r_pa_{r['id']}")

                    estres = st.toggle("🚨 Aplicar Escenario de Estrés (-20% EBITDA)", key=f"r_estres_{r['id']}")
                    eb_calc = eb * 0.8 if estres else eb

                    denom_dscr = gf + (cuota_est * 12)
                    dscr = (eb_calc / denom_dscr) if denom_dscr > 0 else 0
                    margen_ebitda = (eb_calc / (ing_m * 12) * 100) if ing_m > 0 else 0

                    sw = st.session_state.get('w_liq', 1.0) + st.session_state.get('w_sol', 1.0) + st.session_state.get('w_cob', 1.0)
                    pc_s = max(pc, 0.001); pa_s = max(pa, 0.001); gf_s = max(gf, 0.001)
                    
                    s_base = (((min(ac / pc_s * 5, 10)) * st.session_state.get('w_liq', 1.0)) +
                              ((max(10 - pt / pa_s * 2.5, 0)) * st.session_state.get('w_sol', 1.0)) +
                              ((min(eb_calc / gf_s * 2, 10)) * st.session_state.get('w_cob', 1.0))) / max(sw, 0.1)
                              
                    kc_m = st.slider("Matriz Kaizen Institucional (Cualitativo)", 0.0, 10.0, float(r['rm_score'] if pd.notna(r['rm_score']) else 0), key=f"r_kc_{r['id']}")
                    final = round(min(s_base * (1 + (kc_m / 10 * st.session_state.get('kc_boost_max', 20) / 100)), 10.0), 2)

                    t_base = st.session_state.get('tasa_base', 12.0)
                    f_riesgo = st.session_state.get('factor_riesgo', 2.0)
                    t_sugerida = round(t_base + ((10 - final) * f_riesgo), 2)

                    st.markdown(f"<div style='background:#a9c1d3; padding:12px; border-radius:8px; margin-bottom:15px; color:#0B1D4E'>{APP_ICONS['cartera']} <strong>Métricas de Riesgo y Precio</strong></div>", unsafe_allow_html=True)
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("DSCR", f"{dscr:.2f}x")
                    m2.metric("Margen EBITDA", f"{margen_ebitda:.2f}%")
                    m3.metric("Score Final", f"{final} / 10")
                    m4.metric("Tasa Sugerida", f"{t_sugerida}%")

                    cov = st.text_area("Covenants (Condiciones Especiales Post-Cierre)", key=f"r_cov_{r['id']}")
                    obs_r = st.text_area("Observaciones Financieras", key=f"r_obs_{r['id']}")
                    if st.button("Firmar Riesgo", key=f"r_f_{r['id']}"):
                        data_r = {
                            'score': final, 'rm_score': kc_m,
                            'ac': ac, 'pc': pc, 'eb': eb, 'gf': gf, 'pt': pt, 'pa': pa,
                            'obs': obs_r, 'cuota': cuota_est, 'ing': ing_m,
                            'mon': mon, 'estres': estres, 'dscr': dscr,
                            'margen': margen_ebitda, 'tasa': t_sugerida, 'cov': cov
                        }
                        modal_firmar_riesgo(r, 'corp', data_r)

    with tab_auto:
        if not df_auto.empty:
            df_ra = df_auto[(df_auto['status_riesgo'] == 0) & (df_auto['dictamen'] == 'PENDIENTE')]
        else:
            df_ra = pd.DataFrame()

        if df_ra.empty:
            st.info("No hay expedientes automotrices pendientes en Riesgo.")
        else:
            df_ra_pag = paginate_dataframe(df_ra, page_size=10, key_prefix="risk_auto")
            for _, r in df_ra_pag.iterrows():
                with st.expander(f"🚗 {r['cliente']} | {r['marca']} {r['modelo']} | ${r['monto']:,.2f}"):
                    st.markdown(f"#### {APP_ICONS['automotriz']} Evaluación de Capacidad de Pago", unsafe_allow_html=True)
                    st.markdown("**Resumen del Crédito:**")
                    ri1, ri2, ri3, ri4 = st.columns(4)
                    ri1.metric("Monto Financiado", f"${r['monto']:,.2f}")
                    ri2.metric("Plazo", f"{r.get('plazo_meses',0)} meses")
                    ri3.metric("LTV del Vehículo", f"{r.get('ltv_ratio',0):.2f}%")
                    ri4.metric("Vehículo", f"{r.get('marca','')} {r.get('modelo','')}")

                    if r.get('ltv_ratio',0) == 0:
                        st.warning("⚠️ LTV en 0%. Asegúrese de que Legal haya completado los datos del vehículo.")

                    st.markdown("**1. Capacidad de Pago Personal:**")
                    pa1, pa2, pa3 = st.columns(3)
                    mon_a = pa1.selectbox("Moneda", ["USD", "Bs."], key=f"ra_mon_{r['id']}")
                    ing_a = pa2.number_input("Ingreso Mensual Neto", min_value=0.0, value=float(r.get('ingreso_mensual',0) if pd.notna(r.get('ingreso_mensual')) else 0), key=f"ra_ing_{r['id']}")
                    gast_a = pa3.number_input("Gastos Fijos Mensuales (excl. cuota)", min_value=0.0, value=float(r.get('gastos_mensuales',0) if pd.notna(r.get('gastos_mensuales')) else 0), key=f"ra_gast_{r['id']}")
                    cuota_a = st.number_input("Cuota Mensual Estimada del Crédito", min_value=0.0, value=float(r.get('cuota_est',0) if pd.notna(r.get('cuota_est')) else 0), key=f"ra_cuota_{r['id']}")

                    estres_a = st.toggle("🚨 Aplicar Escenario de Estrés (-15% Ingresos)", key=f"ra_estres_{r['id']}")
                    ing_calc = ing_a * 0.85 if estres_a else ing_a

                    ingreso_libre = max(ing_calc - gast_a, 0)
                    dti_a = (cuota_a / max(ing_calc, 0.001)) * 100

                    score_cap = min(max((ingreso_libre - cuota_a) / max(ing_calc, 0.001) * 10, 0), 10)
                    score_ltv_a = max(10 - (float(r.get('ltv_ratio',0) if pd.notna(r.get('ltv_ratio')) else 0) / 10), 0)
                    est_laboral = st.slider("Estabilidad Laboral / Antigüedad (Cualitativo)", 0.0, 10.0, float(r.get('estabilidad_laboral',0) if pd.notna(r.get('estabilidad_laboral')) else 0), key=f"ra_est_{r['id']}")

                    w_cap = st.session_state.get('w_cap', 1.0)
                    w_ltv_a = st.session_state.get('w_ltv_auto', 1.0)
                    w_est_a = st.session_state.get('w_est', 1.0)
                    sw_a = w_cap + w_ltv_a + w_est_a
                    s_base_a = ((score_cap * w_cap) + (score_ltv_a * w_ltv_a) + (est_laboral * w_est_a)) / max(sw_a, 0.1)

                    kc_auto = st.slider("Matriz Kaizen Institucional (Cualitativo)", 0.0, 10.0, float(r.get('rm_score',0) if pd.notna(r.get('rm_score')) else 0), key=f"ra_kc_{r['id']}")
                    boost_auto = st.session_state.get('kc_boost_max_auto', 20.0)
                    final_a = round(min(s_base_a * (1 + (kc_auto / 10 * boost_auto / 100)), 10.0), 2)

                    t_base_a = st.session_state.get('tasa_base_auto', 10.0)
                    f_riesgo_a = st.session_state.get('factor_riesgo_auto', 1.5)
                    t_sug_a = round(t_base_a + ((10 - final_a) * f_riesgo_a), 2)

                    pti = (cuota_a / max(ing_calc, 0.001)) * 100
                    if pti < 30:
                        pti_color = "#10B981"; pti_label = "🟢 Aceptable"
                    elif pti <= 40:
                        pti_color = "#F59E0B"; pti_label = "🟡 Ajustado"
                    else:
                        pti_color = "#EF4444"; pti_label = "🔴 Alto"

                    st.markdown(f"<div style='background:#a9c1d3; padding:12px; border-radius:8px; margin-bottom:15px; color:#0B1D4E'>{APP_ICONS['cartera']} <strong>Métricas de Riesgo y Precio</strong></div>", unsafe_allow_html=True)
                    ma1, ma2, ma3, ma4, ma5, ma6 = st.columns(6)
                    ma1.metric("Ingreso Libre", f"${ingreso_libre:,.2f}")
                    dti_delta = "✓ OK" if dti_a < 35 else "⚠ ALTO"
                    dti_color = "normal" if dti_a < 35 else "inverse"
                    ma2.metric("DTI Ratio", f"{dti_a:.2f}%", delta=dti_delta, delta_color=dti_color)
                    ma3.metric("Score Capacidad", f"{score_cap:.2f}/10")
                    ma4.metric("Score Final", f"{final_a}/10")
                    ma5.metric("Tasa Sugerida", f"{t_sug_a}%")
                    ma6.metric("PTI Ratio", f"{pti:.1f}%")

                    st.markdown(
                        f'<div style="background:#F8FAFC;border-left:4px solid {pti_color};'
                        f'border-radius:0 8px 8px 0;padding:8px 14px;margin:6px 0;font-size:0.87em">'
                        f'<strong>PTI (Payment-to-Income):</strong> {pti:.1f}% &nbsp;—&nbsp; {pti_label}'
                        f'&nbsp;&nbsp;<span style="color:#94A3B8;font-size:0.85em">'
                        f'(Verde &lt;30% · Amarillo 30-40% · Rojo &gt;40%)</span></div>',
                        unsafe_allow_html=True)

                    if dti_a > 40:
                        st.error("🚨 DTI superior al 40%. Riesgo elevado de sobreendeudamiento.")
                    elif dti_a > 30:
                        st.warning("⚠️ DTI entre 30-40%. Capacidad de pago ajustada.")

                    cov_a = st.text_area("Condiciones Especiales Post-Cierre", key=f"ra_cov_{r['id']}")
                    obs_ra = st.text_area("Observaciones de Riesgo", key=f"ra_obs_{r['id']}")
                    if st.button("Firmar Riesgo", key=f"ra_f_{r['id']}"):
                        data_ra = {
                            'score': final_a, 'rm_score': kc_auto,
                            'ing': ing_a, 'gastos': gast_a, 'cuota': cuota_a,
                            'dti': dti_a, 'estabilidad': est_laboral, 'estres': estres_a,
                            'tasa': t_sug_a, 'mon': mon_a, 'obs': obs_ra, 'cov': cov_a
                        }
                        modal_firmar_riesgo(r, 'auto', data_ra)

