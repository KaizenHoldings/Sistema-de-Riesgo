import streamlit as st
import pandas as pd
from utils import page_header, section_divider, paginate_dataframe, APP_ICONS
from database.daos_sqlserver import ExpedienteCorporativoDAO, ExpedienteAutomotrizDAO

@st.dialog("Confirmar Certificación")
def modal_certificar_comp(r, tipo, data):
    st.markdown(f"### ¿Confirmar certificación para **{r['cliente']}**?")
    st.write("Al certificar, usted confirma que ha realizado la debida diligencia AML/CFT.")
    
    if st.button("Confirmar Firma y Certificar", type="primary", use_container_width=True):
        with st.spinner("Registrando certificación..."):
            if tipo == 'corp':
                ExpedienteCorporativoDAO.update_compliance(
                    exp_id=r['id'],
                    riesgo_aml=data['aml'],
                    origen_fondos=data['ori'],
                    obs=data['obs'],
                    check_pep=data['pep'],
                    check_sanciones=data['sanciones']
                )
            else:
                ExpedienteAutomotrizDAO.update_compliance(
                    exp_id=r['id'],
                    ocupacion=data['ocu'],
                    empleador=data['emp'],
                    telefono=data['tel'],
                    riesgo_aml=data['aml'],
                    origen_fondos=data['ori'],
                    check_pep=data['pep'],
                    check_sanciones=data['sanciones'],
                    obs=data['obs']
                )
            st.success("✅ Certificación registrada exitosamente.")
            st.rerun()

def show():
    page_header("compliance", "Cumplimiento & AML/CFT",
                "Revisión de expedientes pendientes de certificación",
                "KFG Risk Architect · Cumplimiento")
                
    # ── Carga de datos aislada (Consumiendo DAOs) ──
    with st.spinner("Cargando expedientes para revisión..."):
        df_corp = ExpedienteCorporativoDAO.get_all_as_df()
        df_auto = ExpedienteAutomotrizDAO.get_all_as_df()

    tab_corp, tab_auto = st.tabs(["Créditos Corporativos", "Créditos Automotrices"])

    # ── Sección: Corporativos ──
    with tab_corp:
        if not df_corp.empty:
            df_c = df_corp[(df_corp['status_comp'] == 0) & (df_corp['dictamen'] == 'PENDIENTE')]
        else:
            df_c = pd.DataFrame()

        if df_c.empty:
            st.info("No hay expedientes corporativos pendientes de Cumplimiento.")
        else:
            df_c_pag = paginate_dataframe(df_c, page_size=10, key_prefix="comp_corp")
            for _, r in df_c_pag.iterrows():
                with st.expander(f"{r['cliente'].upper()} | RIF: {r['rif']} | ${r['monto']:,.2f}"):
                    st.markdown(f"#### {APP_ICONS['corporativo']} Detalle de Certificación", unsafe_allow_html=True)
                    aml = st.selectbox("Nivel de Riesgo AML", ["Bajo", "Medio", "Alto"], key=f"c_aml_{r['id']}")
                    ori = st.text_input("Origen de Fondos", key=f"c_ori_{r['id']}")
                    
                    st.markdown("**Control Reputacional (Gatekeeper):**")
                    chk_sanciones = st.checkbox("✅ Verificación en Listas de Sanciones (OFAC/ONU)", key=f"c_ofac_{r['id']}")
                    chk_pep = st.checkbox("✅ Declaración de No PEP (Persona Expuesta Políticamente)", key=f"c_pep_{r['id']}")
                    obs = st.text_area("Observaciones AML/CFT", key=f"c_obs_{r['id']}")
                    
                    if st.button("Certificar Cumplimiento", key=f"c_btn_{r['id']}", disabled=not chk_sanciones):
                        data_comp = {
                            'aml': aml, 'ori': ori, 'obs': obs, 
                            'pep': chk_pep, 'sanciones': chk_sanciones
                        }
                        modal_certificar_comp(r, 'corp', data_comp)
                        
                    if not chk_sanciones:
                        st.caption("⚠️ Debe verificar las listas de sanciones para habilitar la firma.")

    # ── Sección: Automotrices ──
    with tab_auto:
        if not df_auto.empty:
            df_ca = df_auto[(df_auto['status_comp'] == 0) & (df_auto['dictamen'] == 'PENDIENTE')]
        else:
            df_ca = pd.DataFrame()

        if df_ca.empty:
            st.info("No hay expedientes automotrices pendientes de Cumplimiento.")
        else:
            df_ca_pag = paginate_dataframe(df_ca, page_size=10, key_prefix="comp_auto")
            for _, r in df_ca_pag.iterrows():
                with st.expander(f"🚗 {r['cliente']} | {r['marca']} {r['modelo']} | ${r['monto']:,.2f}"):
                    st.markdown(f"#### {APP_ICONS['automotriz']} Detalle de Certificación", unsafe_allow_html=True)
                    st.markdown("**Datos Laborales del Solicitante:**")
                    a1, a2, a3 = st.columns(3)
                    
                    # Prevenir valores nulos de la BBDD
                    val_ocu = "" if pd.isna(r['ocupacion']) else str(r['ocupacion'])
                    val_emp = "" if pd.isna(r['empleador']) else str(r['empleador'])
                    val_tel = "" if pd.isna(r['telefono']) else str(r['telefono'])
                    
                    ocu = a1.text_input("Ocupación", value=val_ocu, key=f"ca_ocu_{r['id']}")
                    emp = a2.text_input("Empleador", value=val_emp, key=f"ca_emp_{r['id']}")
                    tel = a3.text_input("Teléfono", value=val_tel, key=f"ca_tel_{r['id']}")
                    
                    st.markdown("**Análisis AML/CFT:**")
                    aml_a = st.selectbox("Nivel de Riesgo AML", ["Bajo", "Medio", "Alto"], key=f"ca_aml_{r['id']}")
                    ori_a = st.text_input("Origen de Fondos (Enganche / Inicial)", key=f"ca_ori_{r['id']}")
                    chk_san_a = st.checkbox("✅ Verificación en Listas de Sanciones (OFAC/ONU)", key=f"ca_ofac_{r['id']}")
                    chk_pep_a = st.checkbox("✅ Declaración de No PEP", key=f"ca_pep_{r['id']}")
                    obs_a = st.text_area("Observaciones AML/CFT", key=f"ca_obs_{r['id']}")
                    
                    if st.button("Certificar Cumplimiento", key=f"ca_btn_{r['id']}", disabled=not chk_san_a):
                        data_ca = {
                            'ocu': ocu, 'emp': emp, 'tel': tel,
                            'aml': aml_a, 'ori': ori_a, 'obs': obs_a,
                            'pep': chk_pep_a, 'sanciones': chk_san_a
                        }
                        modal_certificar_comp(r, 'auto', data_ca)
                        
                    if not chk_san_a:
                        st.caption("⚠️ Debe verificar las listas de sanciones para habilitar la firma.")
