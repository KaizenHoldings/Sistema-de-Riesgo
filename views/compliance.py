import streamlit as st
import pandas as pd
from utils import page_header, section_divider, paginate_dataframe, APP_ICONS
from database.daos_sqlserver import ExpedienteCorporativoDAO, ExpedienteAutomotrizDAO, ClienteDAO

@st.dialog("Confirmar Certificación")
def modal_certificar_comp(r, tipo, data):
    st.markdown(f"### ¿Confirmar certificación para **{r['cliente']}**?")
    st.write("Al certificar, usted confirma que ha realizado la debida diligencia AML/CFT.")
    
    if st.button("Confirmar Firma y Certificar", type="primary", width='stretch'):
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
        df_corp_raw = ExpedienteCorporativoDAO.get_all_as_df()
        df_auto_raw = ExpedienteAutomotrizDAO.get_all_as_df()

        # Filtrar pendientes ANTES de declarar las pestañas
        df_c = df_corp_raw[(df_corp_raw['status_comp'] == 0) & (df_corp_raw['dictamen'] == 'PENDIENTE')] if not df_corp_raw.empty else pd.DataFrame()
        df_ca = df_auto_raw[(df_auto_raw['status_comp'] == 0) & (df_auto_raw['dictamen'] == 'PENDIENTE')] if not df_auto_raw.empty else pd.DataFrame()

        count_corp = len(df_c)
        count_auto = len(df_ca)

    # ── Títulos dinámicos con Negrita y Asterisco ──
    label_corp = f"* **Créditos Corporativos ({count_corp})**" if count_corp > 0 else "Créditos Corporativos"
    label_auto = f"* **Créditos Automotrices ({count_auto})**" if count_auto > 0 else "Créditos Automotrices"

    tab_corp, tab_auto = st.tabs([label_corp, label_auto])

    # ── Sección: Corporativos ──
    with tab_corp:
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
        if df_ca.empty:
            st.info("No hay expedientes automotrices pendientes de Cumplimiento.")
        else:
            df_ca_pag = paginate_dataframe(df_ca, page_size=10, key_prefix="comp_auto")
            for _, r in df_ca_pag.iterrows():
                with st.expander(f"🚗 {r['cliente']} | {r['marca']} {r['modelo']} | ${r['monto']:,.2f}"):
                    st.markdown(f"#### {APP_ICONS['automotriz']} Detalle de Certificación", unsafe_allow_html=True)
                    st.markdown("**Datos Laborales del Solicitante:**")
                    a1, a2, a3 = st.columns(3)
                    
                    # Prevenir valores nulos de la BBDD y precargar de cliente si está vinculado
                    cli = ClienteDAO.get_by_id(r.get('cliente_id'))
                    
                    val_ocu = str(r['ocupacion']) if pd.notna(r['ocupacion']) and str(r['ocupacion']).strip() else ""
                    if not val_ocu and cli:
                        val_ocu = cli.get('actividad_economica', '')
                        
                    val_emp = str(r['empleador']) if pd.notna(r['empleador']) and str(r['empleador']).strip() else ""
                    
                    val_tel = str(r['telefono']) if pd.notna(r['telefono']) and str(r['telefono']).strip() else ""
                    if not val_tel and cli:
                        val_tel = cli.get('telefono', '')
                    
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
