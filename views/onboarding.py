import streamlit as st
import pandas as pd
from datetime import datetime, date
import json

from utils import page_header, kyc_badge, badge, DOCS_NATURAL, DOCS_JURIDICA, paginate_dataframe, APP_ICONS
from database.daos_sqlserver import ClienteDAO, ExpedienteCorporativoDAO, ExpedienteAutomotrizDAO

def show():
    page_header("onboarding", "Client Onboarding & KYC Progress",
                "Registro de clientes, verificación KYC y gestión documental",
                "KFG Risk Architect · Clientes")
    
    # Cargar datos usando DAOs
    df_cli = ClienteDAO.get_all_as_df()
    df_corp = ExpedienteCorporativoDAO.get_all_as_df()
    df_auto = ExpedienteAutomotrizDAO.get_all_as_df()
    role = st.session_state.get('role', 'Analista')

    # ── KPIs de clientes ──────────────────────
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Clientes", len(df_cli))
    if not df_cli.empty:
        k2.metric("Prospectos", len(df_cli[df_cli['kyc_status']=='Prospecto']))
        k3.metric("KYC Aprobado", len(df_cli[df_cli['kyc_status']=='KYC Aprobado']))
        k4.metric("Activos", len(df_cli[df_cli['kyc_status']=='Activo']))
    else:
        k2.metric("Prospectos", 0); k3.metric("KYC Aprobado", 0); k4.metric("Activos", 0)

    st.markdown("---")

    if st.session_state.get('client_created_msg'):
        st.success(st.session_state['client_created_msg'])
        st.session_state['client_created_msg'] = None

    # ── Registrar nuevo cliente ───────────────
    with st.expander("Registrar Nuevo Cliente", expanded=False):
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
                    st.session_state['client_created_msg'] = f"✅ Cliente **{nc_nom}** registrado exitosamente."
                    st.rerun()
                else:
                    st.warning("Nombre y C.I./RIF son obligatorios.")

    st.markdown("---")

    # ── Filtros ───────────────────────────────
    if not df_cli.empty:
        f1, f2, f3 = st.columns([2, 1, 1])
        buscar   = f1.text_input("🔍 Buscar por nombre o C.I./RIF", key="cli_buscar")
        fil_tipo = f2.selectbox("Tipo", ["Todos","Natural","Jurídica"], key="cli_tipo")
        fil_kyc  = f3.selectbox("Estado KYC", ["Todos","Prospecto","KYC Pendiente",
                                                "KYC Aprobado","Activo"], key="cli_kyc")
        df_vis = df_cli.copy()
        if buscar:
            df_vis = df_vis[df_vis['nombre'].str.contains(buscar, case=False, na=False) |
                            df_vis['cedula_rif'].str.contains(buscar, case=False, na=False)]
        if fil_tipo != "Todos":
            df_vis = df_vis[df_vis['tipo'] == fil_tipo]
        if fil_kyc != "Todos":
            df_vis = df_vis[df_vis['kyc_status'] == fil_kyc]

        st.caption(f"Mostrando {len(df_vis)} de {len(df_cli)} clientes")
        st.markdown("---")

        # ── Tarjetas de clientes ──────────────
        df_pag = paginate_dataframe(df_vis, page_size=10, key_prefix="cli_list")
        for _, cli in df_pag.iterrows():
            tipo_em = "🏢" if cli['tipo'] == 'Jurídica' else "👤"
            exp_label = (f"{tipo_em} {cli['nombre']}  ·  {cli['cedula_rif']}  ·  "
                         f"{cli['kyc_status']}  ·  {cli['tipo']}")
            with st.expander(exp_label):
                tipo_ic = APP_ICONS['corporativo'] if cli['tipo'] == 'Jurídica' else "👤"
                st.markdown(f"### {tipo_ic} Perfil del Cliente", unsafe_allow_html=True)
                col_info, col_kyc = st.columns([1.6, 1])

                with col_info:
                    st.markdown(f"""
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;
                                font-size:0.9em;margin-bottom:12px">
                        <div><span style="color:#64748B">📞 Teléfono</span><br>
                             <strong>{cli['telefono'] or '—'}</strong></div>
                        <div><span style="color:#64748B">📧 Email</span><br>
                             <strong>{cli['email'] or '—'}</strong></div>
                        <div><span style="color:#64748B">📍 Dirección</span><br>
                             <strong>{cli['direccion'] or '—'}</strong></div>
                        <div><span style="color:#64748B">💼 Actividad</span><br>
                             <strong>{cli['actividad_economica'] or '—'}</strong></div>
                        {"<div><span style='color:#64748B'>👤 Representante</span><br><strong>" + str(cli['nombre_rep']) + " (" + str(cli['cedula_rep']) + ")</strong></div>" if cli['tipo']=='Jurídica' and cli['nombre_rep'] else ""}
                    </div>
                    """, unsafe_allow_html=True)

                    # Checklist de documentos
                    st.markdown("**📂 Checklist de Documentos KYC**")
                    try:
                        docs = json.loads(cli['docs_json']) if cli['docs_json'] else {}
                    except Exception:
                        docs = {}

                    docs_list = DOCS_NATURAL if cli['tipo']=='Natural' else DOCS_JURIDICA
                    docs_updated = {}
                    for doc in docs_list:
                        current_val = docs.get(doc, False)
                        nuevo_val = st.checkbox(doc, value=current_val,
                                                 key=f"doc_{cli['id']}_{docs_list.index(doc)}")
                        docs_updated[doc] = nuevo_val

                    completados = sum(docs_updated.values())
                    total_docs  = len(docs_list)
                    pct = int(completados / total_docs * 100) if total_docs else 0
                    st.progress(pct / 100,
                                text=f"Documentos: {completados}/{total_docs} ({pct}%)")

                    if st.button("Guardar", key=f"save_docs_{cli['id']}"):
                        new_kyc = cli['kyc_status']
                        if new_kyc == 'Prospecto' and completados > 0:
                            new_kyc = 'KYC Pendiente'
                        ClienteDAO.update_docs_and_status(cli['id'], json.dumps(docs_updated), new_kyc)
                        st.success("Documentos guardados."); st.rerun()

                with col_kyc:
                    st.markdown("**Estado KYC**")
                    st.markdown(kyc_badge(cli['kyc_status']), unsafe_allow_html=True)
                    st.markdown(f"<small style='color:#94A3B8'>Registrado: {cli['fecha_registro']}</small>",
                                unsafe_allow_html=True)

                    kyc_aprob = cli.get('kyc_aprobado_por')
                    if kyc_aprob and pd.notna(kyc_aprob):
                        st.markdown(
                            f"<small style='color:#059669'>✅ Aprobado por <strong>"
                            f"{kyc_aprob}</strong> el {cli.get('kyc_fecha', '')}</small>",
                            unsafe_allow_html=True)

                    st.markdown("---")
                    obs_kyc_val = str(cli['obs_kyc']) if pd.notna(cli['obs_kyc']) else ""
                    obs_kyc_new = st.text_area("Observaciones KYC", value=obs_kyc_val,
                                                key=f"obs_kyc_{cli['id']}", height=80)

                    can_approve = role in ('Compliance','Superadmin')
                    if can_approve and cli['kyc_status'] in ('Prospecto','KYC Pendiente'):
                        if st.button("✅ Aprobar KYC", key=f"aprov_kyc_{cli['id']}",
                                     width='stretch'):
                            ClienteDAO.update_kyc_approval(
                                cli['id'], obs_kyc_new, st.session_state.get('current_user', 'Admin'),
                                datetime.now().strftime("%Y-%m-%d")
                            )
                            st.success("KYC Aprobado."); st.rerun()
                    elif cli['kyc_status'] == 'KYC Aprobado':
                        if st.button("🔄 Marcar como Activo", key=f"activo_{cli['id']}",
                                     width='stretch'):
                            ClienteDAO.update_kyc_status(cli['id'], 'Activo')
                            st.rerun()

                    if st.button("📝 Guardar Observaciones", key=f"save_obs_{cli['id']}",
                                 width='stretch'):
                        ClienteDAO.update_kyc_observations(cli['id'], obs_kyc_new)
                        st.success("Observaciones actualizadas."); st.rerun()

                    st.markdown("---")
                    # Expedientes vinculados
                    st.markdown("**📁 Expedientes Vinculados**")
                    # Match by name as fallback since id linking is not explicitly enforced yet
                    exp_corp = df_corp[df_corp['cliente'] == cli['nombre']] if not df_corp.empty else pd.DataFrame()
                    exp_auto = df_auto[df_auto['cliente'] == cli['nombre']] if not df_auto.empty else pd.DataFrame()
                    
                    total_vinc = len(exp_corp) + len(exp_auto)
                    if total_vinc > 0:
                        if not exp_corp.empty:
                            for _, ec in exp_corp.iterrows():
                                st.markdown(
                                    f"{APP_ICONS['corporativo']} {ec['cliente']} — ${ec['monto']:,.0f} "
                                    f"{badge(ec['dictamen'])}", unsafe_allow_html=True)
                        if not exp_auto.empty:
                            for _, ea in exp_auto.iterrows():
                                st.markdown(
                                    f"{APP_ICONS['automotriz']} {ea['cliente']} {ea['marca']} {ea['modelo']} — "
                                    f"${ea['monto']:,.0f} {badge(ea['dictamen'])}", unsafe_allow_html=True)
                    else:
                        st.caption("Sin expedientes vinculados aún.")
    else:
        st.info("No hay clientes registrados. Use el formulario de arriba para comenzar.")
