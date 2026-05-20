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

import math
@st.dialog("🔍 Directorio de Clientes", width="large")
def modal_seleccionar_cliente():
    """Modal estilizado para buscar y seleccionar un cliente registrado."""
    
    if 'modal_page' not in st.session_state:
        st.session_state['modal_page'] = 1
    if 'last_search' not in st.session_state:
        st.session_state['last_search'] = ""

    st.markdown("""
    <div style="background:linear-gradient(135deg, #0B1D4E 0%, #1E40AF 100%);
                padding:20px 24px;border-radius:12px;margin-bottom:20px">
        <div style="color:white;font-size:1.1em;font-weight:700;margin-bottom:4px">
            Clientes Registrados
        </div>
        <div style="color:#CBD5E1;font-size:0.85em">
            Selecciona un cliente para iniciar la solicitud de crédito
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

    # Buscador y Botón de Nuevo Cliente
    st.markdown("<div style='margin-bottom:8px;font-weight:600;color:#0B1D4E;font-size:0.95em'>Buscar Cliente Registrado</div>", unsafe_allow_html=True)
    col_search, col_btn = st.columns([3, 1])
    with col_search:
        buscar = st.text_input("Buscador", placeholder="Ej: Kaizen, V-12345678...", label_visibility="collapsed")
    with col_btn:
        if st.button("➕ Nuevo Cliente", use_container_width=True, type="primary"):
            st.session_state['go_to_clientes'] = True
            st.rerun()
            
    # Reiniciar paginación si cambia la búsqueda
    if buscar != st.session_state['last_search']:
        st.session_state['modal_page'] = 1
        st.session_state['last_search'] = buscar
    
    df_filtrado = df_cli.copy()
    if buscar:
        df_filtrado = df_filtrado[
            df_filtrado['nombre'].str.contains(buscar, case=False, na=False) |
            df_filtrado['cedula_rif'].str.contains(buscar, case=False, na=False)
        ]

    if df_filtrado.empty:
        st.info(f"No se encontraron clientes que coincidan con **'{buscar}'**")
        return

    # Paginación
    ITEMS_PER_PAGE = 5
    total_items = len(df_filtrado)
    total_pages = math.ceil(total_items / ITEMS_PER_PAGE)
    
    if st.session_state['modal_page'] > total_pages and total_pages > 0:
        st.session_state['modal_page'] = total_pages
        
    current_page = st.session_state['modal_page']
    start_idx = (current_page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    
    df_page = df_filtrado.iloc[start_idx:end_idx]

    st.caption(f"Mostrando {start_idx + 1} - {min(end_idx, total_items)} de {total_items} cliente(s)")

    # Mostrar tarjetas de clientes
    for _, row in df_page.iterrows():
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
            if st.button("Seleccionar", key=f"sel_cli_{row['id']}", use_container_width=True):
                st.session_state['nr_nombre'] = row['nombre']
                st.session_state['nr_rif'] = row['cedula_rif']
                st.session_state['nr_cliente_id'] = row['id']
                st.rerun()

    # Controles de Paginación
    if total_pages > 1:
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
        with col_p1:
            if current_page > 1:
                if st.button("⬅ Anterior", use_container_width=True):
                    st.session_state['modal_page'] -= 1
                    st.rerun()
        with col_p2:
            st.markdown(f"<div style='text-align:center; padding-top:8px; color:#64748B; font-size:0.9em; font-weight:600;'>Página {current_page} de {total_pages}</div>", unsafe_allow_html=True)
        with col_p3:
            if current_page < total_pages:
                if st.button("Siguiente ➡", use_container_width=True):
                    st.session_state['modal_page'] += 1
                    st.rerun()


def show():
    page_header("onboarding", "Nueva Solicitud de Crédito",
                "Crea un nuevo expediente de crédito corporativo o automotriz para un cliente registrado.",
                "KFG Risk Architect · Solicitudes")

    # Manejar mensaje de éxito/warning post-guardado
    if st.session_state.get('nr_success_msg'):
        st.success(st.session_state['nr_success_msg'])
        st.session_state['nr_success_msg'] = None
    if st.session_state.get('nr_warning_msg'):
        st.warning(st.session_state['nr_warning_msg'])
        st.session_state['nr_warning_msg'] = None

    # Función unificada y segura de limpieza de estado
    def clear_form_state():
        keys_to_clear = ['nr_nombre', 'nr_rif', 'nr_tipo', 'nr_cliente_id', 'nr_monto', 'nr_desc']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]

    # Limpiar estado si se solicitó en un submit previo
    if st.session_state.get('do_clear_form'):
        clear_form_state()
        st.session_state['do_clear_form'] = False

    cliente_id = st.session_state.get('nr_cliente_id')
    def_tipo = st.session_state.get('nr_tipo', "Corporativo")
    def_nombre = st.session_state.get('nr_nombre', "")
    def_rif = st.session_state.get('nr_rif', "")

    if not cliente_id:
        # PASO 1: Selección de Cliente
        st.info("Para iniciar una solicitud, debes seleccionar un cliente registrado en el sistema.")
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        
        # Guardar el tipo seleccionado en memoria para preservarlo
        idx_tipo = 0 if def_tipo == "Corporativo" else 1
        tipo_nuevo = st.radio("Selecciona el Tipo de Crédito", ["Corporativo", "Automotriz"], index=idx_tipo, horizontal=True)
        st.session_state['nr_tipo'] = tipo_nuevo
        
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍 Buscar Cliente Existente", type="primary", use_container_width=True):
                modal_seleccionar_cliente()
        with col2:
            if st.button("➕ Crear Nuevo Cliente", use_container_width=True):
                st.session_state['go_to_clientes'] = True
                st.rerun()
    else:
        # PASO 2: Ingreso de Monto y Confirmación
        col_resumen, col_acciones = st.columns([1.5, 1])
        
        with col_resumen:
            st.markdown(f"""
            <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:12px;
                        padding:24px;margin-bottom:24px;display:flex;align-items:center;gap:18px">
                <div style="font-size:3em">👤</div>
                <div style="flex:1">
                    <div style="color:#1E40AF;font-size:0.85em;font-weight:700;text-transform:uppercase;letter-spacing:0.05em">
                        Cliente Seleccionado · Crédito {def_tipo}
                    </div>
                    <div style="color:#0F172A;font-size:1.4em;font-weight:800;margin-top:2px">{def_nombre}</div>
                    <div style="color:#64748B;font-size:1em;margin-top:2px">{def_rif}</div>
                </div>
                <div style="color:#10B981; font-weight:800; font-size:1.1em; background:#D1FAE5; padding:6px 16px; border-radius:8px">
                    {def_tipo}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_acciones:
            monto = st.number_input("Monto a Financiar ($)", min_value=0.0, step=1000.0, key="nr_monto", format="%.2f")
            descripcion = st.text_area("Descripción / Notas de la Solicitud (Opcional)", placeholder="Escribe el propósito de la solicitud...", key="nr_desc", height=80)
            
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            
            if st.button("📝 CREAR EXPEDIENTE", type="primary", use_container_width=True):
                if monto > 0:
                    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                    if def_tipo == "Corporativo":
                        ExpedienteCorporativoDAO.create(fecha_hoy, def_nombre, def_rif, monto, cliente_id, descripcion)
                        st.session_state['nr_success_msg'] = f"✅ Expediente Corporativo creado para **{def_nombre}** por ${monto:,.2f}"
                    else:
                        ExpedienteAutomotrizDAO.create(fecha_hoy, def_nombre, def_rif, monto, cliente_id, descripcion)
                        st.session_state['nr_success_msg'] = f"✅ Expediente Automotriz creado para **{def_nombre}** por ${monto:,.2f}"
                    
                    st.session_state['do_clear_form'] = True
                    st.rerun()
                else:
                    st.warning("El monto solicitado debe ser mayor a 0 para crear el expediente.")
                    
            st.button("✖ Cambiar Cliente / Cancelar", on_click=clear_form_state, use_container_width=True)
