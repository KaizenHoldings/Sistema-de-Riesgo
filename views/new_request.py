import streamlit as st
from datetime import datetime
import pandas as pd

from database.daos_sqlserver import ClienteDAO, ExpedienteCorporativoDAO, ExpedienteAutomotrizDAO
from utils import page_header

st.markdown("""
<style>
.kfg-card {
    background: #ffffff;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    margin-bottom: 24px;
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
</style>
""", unsafe_allow_html=True)
@st.dialog("🔍 Directorio de Clientes", width="large")
def modal_seleccionar_cliente():
    """Modal estilizado para buscar y seleccionar un cliente registrado."""

    st.markdown("""
    <div style="background:linear-gradient(135deg, #0B1D4E 0%, #1E40AF 100%);
                padding:20px 24px;border-radius:12px;margin-bottom:20px">
        <div style="color:white;font-size:1.1em;font-weight:700;margin-bottom:4px">
            Clientes Registrados
        </div>
        <div style="color:#CBD5E1;font-size:0.85em">
            Selecciona un cliente para autocompletar el formulario de solicitud
        </div>
    </div>
    """, unsafe_allow_html=True)

    df_cli = ClienteDAO.get_all_as_df()
    if df_cli.empty:
        st.markdown("""
        <div style="text-align:center;padding:40px 0">
            <div style="font-size:3em;margin-bottom:12px">📋</div>
            <div style="color:#64748B;font-size:1em;font-weight:600">No hay clientes registrados aún</div>
            <div style="color:#94A3B8;font-size:0.85em;margin-top:6px">
                Registra tu primer cliente desde la sección <strong>Clientes</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Buscador
    buscar = st.text_input("🔍 Buscar por nombre o C.I./RIF", placeholder="Ej: Kaizen, V-12345678...")
    
    df_filtrado = df_cli.copy()
    if buscar:
        df_filtrado = df_filtrado[
            df_filtrado['nombre'].str.contains(buscar, case=False, na=False) |
            df_filtrado['cedula_rif'].str.contains(buscar, case=False, na=False)
        ]

    if df_filtrado.empty:
        st.info(f"No se encontraron clientes que coincidan con **'{buscar}'**")
        return

    st.caption(f"Mostrando {len(df_filtrado)} cliente(s)")

    # Mostrar tarjetas de clientes
    for _, row in df_filtrado.head(20).iterrows():
        tipo_icon = "🏢" if row['tipo'] == "Jurídica" else "👤"
        kyc = row.get('kyc_status', 'N/A')
        
        # Color del badge KYC
        kyc_colors = {
            'Activo': ('#059669', '#ECFDF5'),
            'KYC Aprobado': ('#2563EB', '#EFF6FF'),
            'KYC Pendiente': ('#D97706', '#FFFBEB'),
            'Prospecto': ('#64748B', '#F8FAFC'),
        }
        color, bg = kyc_colors.get(kyc, ('#64748B', '#F8FAFC'))

        col_info, col_btn = st.columns([4, 1])
        with col_info:
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:14px;padding:10px 0;
                        border-bottom:1px solid #F1F5F9">
                <div style="font-size:1.6em">{tipo_icon}</div>
                <div style="flex:1">
                    <div style="font-weight:600;color:#0F172A;font-size:0.95em">{row['nombre']}</div>
                    <div style="color:#64748B;font-size:0.82em;margin-top:2px">
                        {row['cedula_rif']} · {row['tipo']}
                    </div>
                </div>
                <div style="padding:3px 10px;border-radius:20px;font-size:0.72em;
                            font-weight:600;color:{color};background:{bg}">
                    {kyc}
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col_btn:
            if st.button("Seleccionar", key=f"sel_cli_{row['id']}", width='stretch'):
                st.session_state['nr_nombre'] = row['nombre']
                st.session_state['nr_rif'] = row['cedula_rif']
                st.session_state['nr_cliente_id'] = row['id']
                
                # Actualizar directamente los estados de los widgets para forzar el autocompletado
                st.session_state['corp_nombre'] = row['nombre']
                st.session_state['corp_rif'] = row['cedula_rif']
                st.session_state['auto_nombre'] = row['nombre']
                st.session_state['auto_ci'] = row['cedula_rif']
                
                # st.session_state['nr_tipo'] = "Corporativo" if row['tipo'] == "Jurídica" else "Automotriz" # Removido para control manual
                st.rerun()


def show():
    page_header("onboarding", "Nueva Solicitud de Crédito",
                "Crea un nuevo expediente de crédito corporativo o automotriz",
                "KFG Risk Architect · Solicitudes")

    # Manejar mensaje de éxito/warning post-guardado
    if st.session_state.get('nr_success_msg'):
        st.success(st.session_state['nr_success_msg'])
        st.session_state['nr_success_msg'] = None
    if st.session_state.get('nr_warning_msg'):
        st.warning(st.session_state['nr_warning_msg'])
        st.session_state['nr_warning_msg'] = None

    # Valores por defecto desde el estado (provienen del modal de clientes)
    def_tipo = st.session_state.get('nr_tipo', "Corporativo")
    def_nombre = st.session_state.get('nr_nombre', "")
    def_rif = st.session_state.get('nr_rif', "")
    
    # Flag para bloquear edición si viene de búsqueda (Code Review Fix)
    is_selected = st.session_state.get('nr_cliente_id') is not None

    # Función unificada de limpieza de estado
    def clear_form_state():
        keys_to_clear = [
            'nr_nombre', 'nr_rif', 'nr_tipo', 'nr_cliente_id',
            'corp_nombre', 'corp_rif', 'corp_monto',
            'auto_nombre', 'auto_ci', 'auto_monto'
        ]


        for key in keys_to_clear:
           
            if(key == 'corp_monto' or key == 'auto_monto'):
                st.session_state[key] = 0.00
            else:
                st.session_state[key] = None

    # ── Fila superior: Tipo de crédito (izq) + Buscar cliente (der) ──
   # st.markdown("<div class='kfg-card'>", unsafe_allow_html=True)
    top_left, top_right = st.columns([3, 1])
    with top_left:
        idx_tipo = 0 if def_tipo == "Corporativo" else 1
        tipo_nuevo = st.radio("Tipo de Crédito", ["Corporativo", "Automotriz"], horizontal=True, index=idx_tipo, disabled=is_selected)
    with top_right:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("🔍 Buscar Cliente", width='stretch', disabled=is_selected):
            modal_seleccionar_cliente()

    # Indicador de cliente seleccionado
    if def_nombre:
        st.markdown(f"""
        <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:10px;
                    padding:12px 16px;margin-bottom:16px;display:flex;align-items:center;gap:10px">
            <div style="font-size:1.3em"></div>
            <div style="flex:1">
                <div style="font-weight:600;color:#1E40AF;font-size:0.9em">Cliente vinculado</div>
                <div style="color:#3B82F6;font-size:0.82em">{def_nombre} · {def_rif}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    if "Corporativo" in tipo_nuevo:
        nc = st.text_input("Cliente / Empresa", value=def_nombre, key="corp_nombre", disabled=is_selected)
        nr = st.text_input("RIF", value=def_rif, key="corp_rif", disabled=is_selected)
        nm = st.number_input("Monto Solicitado ($)", min_value=0.0, key="corp_monto")

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        c_cancel, c_submit, _ = st.columns([1, 1, 2])
        with c_cancel:
            if st.button("✖ Cancelar",on_click=clear_form_state, width='stretch', key="btn_cancel_corp"):
              print("Cancelar")
             # clear_form_state()
              st.rerun()
        with c_submit:
            if st.button("CREAR EXPEDIENTE", type="primary", width='stretch', key="btn_crear_corp"):
                if nc and nr:
                    # Resolución de ID Oportunista
                    cliente_id = st.session_state.get('nr_cliente_id')
                    if not cliente_id:
                        cliente_id = ClienteDAO.get_id_by_rif(nr)
                    
                    # Persistencia
                    ExpedienteCorporativoDAO.create(datetime.now().strftime("%Y-%m-%d"), nc, nr, nm, cliente_id)
                    
                    # Feedback Condicionado
                    if cliente_id:
                        st.session_state['nr_success_msg'] = f"✅ Expediente Corporativo creado para **{nc}**"
                    else:
                        st.session_state['nr_warning_msg'] = "Expediente creado exitosamente, pero no se encontró un cliente registrado con ese RIF. El expediente quedó sin vincular."
                    
                    # Limpieza unificada
                    clear_form_state()
                    st.rerun()
                else:
                    st.warning("El Nombre del Cliente y el RIF son obligatorios.")
    else:
        na = st.text_input("Nombre del Solicitante", value=def_nombre, key="auto_nombre", disabled=is_selected)
        nced = st.text_input("C.I. / Pasaporte", value=def_rif, key="auto_ci", disabled=is_selected)
        nm_a = st.number_input("Monto a Financiar ($)", min_value=0.0, step=1000.0, key="auto_monto")

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        c_cancel, c_submit, _ = st.columns([1, 1, 2])
        with c_cancel:
            if st.button("✖ Cancelar", on_click=clear_form_state, width='stretch', key="btn_cancel_auto"):
                #clear_form_state()
                st.rerun()
        with c_submit:
            if st.button("📝 CREAR EXPEDIENTE", type="primary", width='stretch', key="btn_crear_auto"):
                if na and nced:
                    # Resolución de ID Oportunista
                    cliente_id = st.session_state.get('nr_cliente_id')
                    if not cliente_id:
                        cliente_id = ClienteDAO.get_id_by_rif(nced)
                    
                    # Persistencia
                    ExpedienteAutomotrizDAO.create(datetime.now().strftime("%Y-%m-%d"), na, nced, nm_a, cliente_id)
                    
                    # Feedback Condicionado
                    if cliente_id:
                        st.session_state['nr_success_msg'] = f"✅ Expediente Automotriz creado para **{na}**"
                    else:
                        st.session_state['nr_warning_msg'] = "Expediente creado exitosamente, pero no se encontró un cliente registrado con ese RIF. El expediente quedó sin vincular."
                    
                    # Limpieza unificada
                    clear_form_state()
                    st.rerun()
                else:
                    st.warning("El Nombre del Solicitante y la C.I. son obligatorios.")
