import streamlit as st
from utils import page_header
from database.daos_sqlserver import ConfigParametroDAO

def show():
    page_header("parameters", "Risk Engine Configuration",
                "Pesos de calificación, fórmulas de scoring y política de pricing",
                "KFG Risk Architect · Configuración")
                
    tab_cfg_corp, tab_cfg_auto = st.tabs(["🏢 Crédito Corporativo", "🚗 Crédito Automotriz"])

    with tab_cfg_corp:
        st.subheader("Fórmulas — Crédito Corporativo")
        st.latex(r"S_{base} = \frac{(Liq \cdot W_{liq}) + (Solv \cdot W_{sol}) + (Cob \cdot W_{cob})}{W_{liq}+W_{sol}+W_{cob}}")
        st.latex(r"S_{final} = \min\left(S_{base} \cdot \left(1 + \frac{KC}{10} \cdot \%Boost\right), 10\right)")
        st.latex(r"Tasa = Tasa_{base} + (10 - S_{final}) \times Factor_{riesgo}")
        st.divider()
        with st.form("cfg_corp_form"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Pesos de Calificación**")
                w_liq = st.slider("Peso Liquidez", 0.0, 3.0, float(st.session_state.get('w_liq', 1.0)))
                w_sol = st.slider("Peso Solvencia", 0.0, 3.0, float(st.session_state.get('w_sol', 1.0)))
                w_cob = st.slider("Peso Cobertura", 0.0, 3.0, float(st.session_state.get('w_cob', 1.0)))
                kc_b = st.number_input("% Boost Máx. Kaizen", 0, 100, int(st.session_state.get('kc_boost_max', 20)))
            with col2:
                st.markdown("**Pricing**")
                t_base_cfg = st.number_input("Tasa Base (%)", 0.0, 50.0, float(st.session_state.get('tasa_base', 12.0)), 0.5)
                f_riesgo_cfg = st.number_input("Factor de Riesgo", 0.0, 10.0, float(st.session_state.get('factor_riesgo', 0.5)), 0.1)
            if st.form_submit_button("Guardar Política Corporativa"):
                for k, v in [('w_liq', w_liq), ('w_sol', w_sol), ('w_cob', w_cob),
                             ('kc_boost_max', kc_b), ('tasa_base', t_base_cfg), ('factor_riesgo', f_riesgo_cfg)]:
                    ConfigParametroDAO.update_param(k, v)
                st.session_state.update({'w_liq': w_liq, 'w_sol': w_sol, 'w_cob': w_cob,
                                         'kc_boost_max': kc_b, 'tasa_base': t_base_cfg, 'factor_riesgo': f_riesgo_cfg})
                ConfigParametroDAO.get_all_as_dict.clear()
                st.success("Parámetros corporativos actualizados.")
                st.rerun()

    with tab_cfg_auto:
        st.subheader("Fórmulas — Crédito Automotriz")
        st.latex(r"S_{base} = \frac{(Cap \cdot W_{cap}) + (LTV \cdot W_{ltv}) + (Est \cdot W_{est})}{W_{cap}+W_{ltv}+W_{est}}")
        st.latex(r"S_{final} = \min\left(S_{base} \cdot \left(1 + \frac{KC}{10} \cdot \%Boost\right), 10\right)")
        st.latex(r"Tasa = Tasa_{base} + (10 - S_{final}) \times Factor_{riesgo}")
        st.info("**Cap**: Score de Capacidad de Pago (basado en DTI) | **LTV**: Score Loan-to-Value del vehículo | **Est**: Estabilidad Laboral (cualitativo)")
        st.divider()
        with st.form("cfg_auto_form"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Pesos de Calificación**")
                w_cap = st.slider("Peso Capacidad de Pago", 0.0, 3.0, float(st.session_state.get('w_cap', 1.0)))
                w_ltv_a = st.slider("Peso LTV Vehículo", 0.0, 3.0, float(st.session_state.get('w_ltv_auto', 1.0)))
                w_est_a = st.slider("Peso Estabilidad Laboral", 0.0, 3.0, float(st.session_state.get('w_est', 1.0)))
                kc_b_a = st.number_input("% Boost Máx. Kaizen Automotriz", 0, 100, int(st.session_state.get('kc_boost_max_auto', 20)))
            with col2:
                st.markdown("**Pricing**")
                t_base_a_cfg = st.number_input("Tasa Base Automotriz (%)", 0.0, 50.0, float(st.session_state.get('tasa_base_auto', 10.0)), 0.5)
                f_riesgo_a_cfg = st.number_input("Factor de Riesgo Automotriz", 0.0, 10.0, float(st.session_state.get('factor_riesgo_auto', 1.5)), 0.1)
            if st.form_submit_button("Guardar Política Automotriz"):
                for k, v in [('w_cap', w_cap), ('w_ltv_auto', w_ltv_a), ('w_est', w_est_a),
                             ('kc_boost_max_auto', kc_b_a), ('tasa_base_auto', t_base_a_cfg),
                             ('factor_riesgo_auto', f_riesgo_a_cfg)]:
                    ConfigParametroDAO.update_param(k, v)
                st.session_state.update({'w_cap': w_cap, 'w_ltv_auto': w_ltv_a, 'w_est': w_est_a,
                                         'kc_boost_max_auto': kc_b_a, 'tasa_base_auto': t_base_a_cfg,
                                         'factor_riesgo_auto': f_riesgo_a_cfg})
                ConfigParametroDAO.get_all_as_dict.clear()
                st.success("Parámetros automotrices actualizados.")
                st.rerun()
