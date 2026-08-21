import streamlit as st
from datetime import datetime, date
import json

from utils import page_header, APP_ICONS, DOCS_NATURAL, DOCS_JURIDICA
from database.daos_sqlserver import ClienteDAO
from services.metrics_service import get_sidebar_metrics

st.markdown("""
<style>
.kfg-card {
    background: #ffffff;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    margin-bottom: 24px;
    font-family: 'Inter', sans-serif;
}
.kfg-btn-primary {
    background: #1E40AF;
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 0.5rem 1rem;
}
.kfg-btn-primary:hover {
    background: #2D5BFF;
}
/* Contraste estricto de inputs: evita texto blanco sobre blanco */
.stTextInput input, .stTextArea textarea, .stDateInput input, .stNumberInput input {
    color: #111827 !important;
    -webkit-text-fill-color: #111827 !important;
}
</style>
""", unsafe_allow_html=True)


def show():
    page_header("onboarding", "Registrar Nuevo Cliente",
                "Alta de personas naturales y jurídicas con checklist KYC inicial",
                "KFG Risk Architect · Clientes · Registro")

    # Mensaje de éxito persistido tras el rerun que limpia el formulario
    if st.session_state.get('client_created_msg'):
        st.success(st.session_state['client_created_msg'])
        st.session_state['client_created_msg'] = None

    st.markdown(f"""
    <div class="kfg-card">
        <div style="display:flex;align-items:center;gap:14px">
            <div style="width:38px;height:38px;background:linear-gradient(135deg,#0B1D4E,#1E3A8A);
                        border-radius:8px;display:flex;align-items:center;justify-content:center;
                        flex-shrink:0">{APP_ICONS['onboarding']}</div>
            <div>
                <div style="color:#0B1D4E;font-weight:700;font-size:1.02em">Datos del Cliente</div>
                <div style="color:#64748B;font-size:0.85em">
                    El cliente se crea con estado <strong>Prospecto</strong> y su checklist
                    documental vacío. La verificación KYC se completa en
                    <strong>Directorio Clientes</strong>.
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        with st.form("form_nuevo_cliente", clear_on_submit=True):
            tipo_cli = st.radio("Tipo de Cliente", ["Natural", "Jurídica"],
                                horizontal=True, key="nc_tipo")
            st.markdown("**Datos Principales**")
            na1, na2 = st.columns(2)
            nc_nom  = na1.text_input("Nombre Completo / Razón Social")
            nc_rif  = na2.text_input("C.I. / RIF")
            na3, na4 = st.columns(2)
            nc_tel  = na3.text_input("Teléfono")
            nc_email= na4.text_input("Correo Electrónico")
            nc_dir  = st.text_input("Dirección")
            nc_act  = st.text_input("Actividad Económica")

            if tipo_cli == "Natural":
                nb1, nb2 = st.columns(2)
                nc_fnac = nb1.date_input("Fecha de Nacimiento", key="nc_fnac")
                nc_nac  = nb2.text_input("Nacionalidad", value="Venezolana")
                nc_rep = nc_crep = nc_carg = ""
            else:
                st.markdown("**Representante Legal**")
                nb1, nb2, nb3 = st.columns(3)
                nc_rep  = nb1.text_input("Nombre del Representante")
                nc_crep = nb2.text_input("C.I. del Representante")
                nc_carg = nb3.text_input("Cargo")
                nc_fnac = date.today()
                nc_nac  = ""

            if st.form_submit_button("REGISTRAR CLIENTE", width='stretch', key="submit_button"):
                if nc_nom and nc_rif:
                    docs_init = json.dumps(
                        {d: False for d in (DOCS_NATURAL if tipo_cli=='Natural' else DOCS_JURIDICA)}
                    )
                    ClienteDAO.create(
                        fecha_registro=datetime.now().strftime("%Y-%m-%d"),
                        tipo=tipo_cli, nombre=nc_nom, cedula_rif=nc_rif,
                        fecha_nacimiento=str(nc_fnac) if tipo_cli=='Natural' else '',
                        nacionalidad=nc_nac, telefono=nc_tel, email=nc_email,
                        direccion=nc_dir, actividad_economica=nc_act,
                        nombre_rep=nc_rep, cedula_rep=nc_crep, cargo_rep=nc_carg,
                        docs_json=docs_init
                    )
                    msg = f"✅ Cliente **{nc_nom}** registrado exitosamente."

                    # 1. Confirmación inmediata, antes de que el rerun limpie el formulario
                    st.success(msg)

                    # 2. Estado de sesión del último cliente creado
                    st.session_state['client_created_msg'] = msg
                    st.session_state['last_client_name'] = nc_nom
                    st.session_state['last_client_rif'] = nc_rif
                    st.session_state['last_client_tipo'] = tipo_cli

                    # 3. Invalidación incondicional de la caché de indicadores del sidebar
                    get_sidebar_metrics.clear()

                    # 4. Redirección al directorio (route.py atiende este flag)
                    st.session_state['go_to_clientes'] = True

                    st.rerun()
                else:
                    st.warning("Nombre y C.I./RIF son obligatorios.")
