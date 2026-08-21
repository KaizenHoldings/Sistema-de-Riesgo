import streamlit as st
import pandas as pd
from datetime import datetime
import json

from utils import page_header, kyc_badge, badge, DOCS_NATURAL, DOCS_JURIDICA, paginate_dataframe, APP_ICONS
from database.daos_sqlserver import ClienteDAO, ExpedienteCorporativoDAO, ExpedienteAutomotrizDAO
from services.storage_service import StorageService
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
/* Botón de descarga primario: texto blanco sobre el fondo oscuro.
   Las reglas globales solo alcanzan el <button> directo, no el <p> interno. */
[data-testid="stDownloadButton"] button[kind="primary"],
[data-testid="stDownloadButton"] button[kind="primary"] *,
[data-testid="stDownloadButton"] [data-testid="stBaseButton-primary"],
[data-testid="stDownloadButton"] [data-testid="stBaseButton-primary"] * {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)


@st.dialog("Detalles del Expediente", width="large")
def modal_detalle_expediente(exp, tipo):
    if tipo == 'corp':
        st.markdown(f"### Expediente Corporativo: {exp['cliente']}")
        st.write(f"**RIF:** {exp.get('rif', 'N/A')}")
        st.write(f"**Monto:** {exp.get('moneda', 'USD')} ${exp['monto']:,.2f}")
        st.markdown(f"**Status:** {badge(exp['dictamen'])}", unsafe_allow_html=True)
        if exp['dictamen'] == 'APROBADO':
            st.write(f"**Status Cobranza:** {exp.get('estado_cobranza') or 'Al día'}")
        st.write(f"**Descripción:** {exp.get('descripcion', 'N/A')}")

        c1, c2, c3 = st.columns(3)
        c1.metric("Score", exp.get('score_f', 'N/A'))
        c2.metric("DSCR", f"{exp.get('dscr', 0):.2f}x")
        c3.metric("LTV", f"{exp.get('ltv_ratio', 0):.2f}%")

        st.write("---")
        st.write(f"**Status Firmas:** Cumplimiento: {'✅' if exp.get('status_comp') else '⏳'} | Legal: {'✅' if exp.get('status_leg') else '⏳'} | Riesgo: {'✅' if exp.get('status_riesgo') else '⏳'}")

    else:
        st.markdown(f"### Expediente Automotriz: {exp['cliente']}")
        st.write(f"**Vehículo:** {exp.get('marca', 'N/A')} {exp.get('modelo', 'N/A')} {exp.get('anio', '')}")
        st.write(f"**Monto:** {exp.get('moneda', 'USD')} ${exp['monto']:,.2f}")
        st.markdown(f"**Status:** {badge(exp['dictamen'])}", unsafe_allow_html=True)
        if exp['dictamen'] == 'APROBADO':
            st.write(f"**Status Cobranza:** {exp.get('estado_cobranza') or 'Al día'}")
        st.write(f"**Descripción:** {exp.get('descripcion', 'N/A')}")

        c1, c2, c3 = st.columns(3)
        c1.metric("Score", exp.get('score_f', 'N/A'))
        c2.metric("DTI Ratio", f"{exp.get('dti_ratio', 0):.2f}%")
        c3.metric("LTV", f"{exp.get('ltv_ratio', 0):.2f}%")

        st.write("---")
        st.write(f"**Status Firmas:** Cumplimiento: {'✅' if exp.get('status_comp') else '⏳'} | Legal: {'✅' if exp.get('status_leg') else '⏳'} | Riesgo: {'✅' if exp.get('status_riesgo') else '⏳'}")

    if st.button("Cerrar", use_container_width=True):
        st.rerun()


def show():
    page_header("onboarding", "Directorio de Clientes & KYC",
                "Consulta de clientes, verificación KYC y gestión documental",
                "KFG Risk Architect · Clientes · Directorio")

    # Confirmación del alta cuando se llega redirigido desde Registrar Cliente
    if st.session_state.get('client_created_msg'):
        st.success(st.session_state['client_created_msg'])
        st.session_state['client_created_msg'] = None

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
            with st.expander(exp_label, expanded=(st.session_state.get('active_client_expander') == cli['id'])):
                tipo_ic = APP_ICONS['corporativo'] if cli['tipo'] == 'Jurídica' else "👤"
                st.markdown(f"### {tipo_ic} Perfil del Cliente", unsafe_allow_html=True)

                tab_kyc, tab_expedientes, tab_documentos = st.tabs(
                    ["Perfil y KYC", "Expedientes", "Repositorio Documental"])

                # ══ Pestaña 1: Perfil y KYC ═══════════════════════════
                with tab_kyc:
                    col_info, col_kyc = st.columns([1.6, 1])

                    with col_info:
                        st.markdown(f"""
                        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;
                                    font-size:0.9em;margin-bottom:12px">
                            <div><span style="color:#64748B">Teléfono</span><br>
                                 <strong>{cli['telefono'] or '—'}</strong></div>
                            <div><span style="color:#64748B">Email</span><br>
                                 <strong>{cli['email'] or '—'}</strong></div>
                            <div><span style="color:#64748B">Dirección</span><br>
                                 <strong>{cli['direccion'] or '—'}</strong></div>
                            <div><span style="color:#64748B">Actividad</span><br>
                                 <strong>{cli['actividad_economica'] or '—'}</strong></div>
                            {"<div><span style='color:#64748B'>👤 Representante</span><br><strong>" + str(cli['nombre_rep']) + " (" + str(cli['cedula_rep']) + ")</strong></div>" if cli['tipo']=='Jurídica' and cli['nombre_rep'] else ""}
                        </div>
                        """, unsafe_allow_html=True)

                        # Checklist de documentos
                        st.markdown("**Checklist de Documentos KYC**")
                        try:
                            docs = json.loads(cli['docs_json']) if cli['docs_json'] else {}
                        except Exception:
                            docs = {}

                        doc_msg_key = f"docmsg_{cli['id']}"
                        if st.session_state.get(doc_msg_key):
                            st.toast(st.session_state[doc_msg_key])
                            st.session_state[doc_msg_key] = None

                        docs_list = DOCS_NATURAL if cli['tipo']=='Natural' else DOCS_JURIDICA

                        # Versión por fila: al rotarla se limpia el uploader y el
                        # checkbox vuelve a tomar su valor desde la BD recargada.
                        def _fila_ver(i, _cid=cli['id']):
                            return st.session_state.get(f"updoc_ver_{_cid}_{i}", 0)

                        def _chk_key(i, _cid=cli['id']):
                            return f"doc_{_cid}_{i}_{_fila_ver(i)}"

                        docs_updated = {}
                        for idx, doc in enumerate(docs_list):
                            ver_doc_key = f"updoc_ver_{cli['id']}_{idx}"
                            if ver_doc_key not in st.session_state:
                                st.session_state[ver_doc_key] = 0

                            # Checkbox arriba y su uploader inmediatamente debajo
                            current_val = docs.get(doc, False)
                            nuevo_val = st.checkbox(doc, value=current_val, key=_chk_key(idx))
                            docs_updated[doc] = nuevo_val

                            replace_key = f"replace_mode_{cli['id']}_{doc}"
                            en_reemplazo = bool(st.session_state.get(replace_key))

                            # La marca de la BD no basta: el archivo debe existir en el
                            # repositorio. Si se marcó la casilla a mano sin subir nada,
                            # se sigue ofreciendo el uploader.
                            doc_file = None
                            if current_val:
                                try:
                                    doc_file = StorageService.get_document_file(
                                        cli['cedula_rif'], cli['nombre'], doc)
                                except Exception:
                                    doc_file = None

                            if current_val and doc_file and not en_reemplazo:
                                # Documento cargado y presente: indicador + descarga + reemplazo
                                c_ind, c_ver, c_rep = st.columns([2, 1, 1])

                                with c_ind:
                                    st.markdown(
                                        '<div style="color:#10B981; font-size: 0.85em; '
                                        'margin-bottom: 8px;">✅ Documento cargado</div>',
                                        unsafe_allow_html=True)

                                with c_ver:
                                    st.download_button(
                                        "Ver", data=doc_file[0], file_name=doc_file[1],
                                        key=f"dl_{cli['id']}_{idx}", type="primary",
                                        width='stretch')

                                with c_rep:
                                    if st.button("Reemplazar", key=f"rep_{cli['id']}_{idx}",
                                                 width='stretch'):
                                        st.session_state[replace_key] = True
                                        st.session_state['active_client_expander'] = cli['id']
                                        st.rerun()
                            else:
                                if en_reemplazo:
                                    c_lbl, c_can = st.columns([3, 1])
                                    with c_lbl:
                                        st.markdown(
                                            '<div style="color:#64748B; font-size: 0.85em; '
                                            'margin-bottom: 8px;">Suba el archivo que '
                                            'reemplazará al actual</div>',
                                            unsafe_allow_html=True)
                                    with c_can:
                                        if st.button("Cancelar", key=f"cancel_{cli['id']}_{idx}",
                                                     width='stretch'):
                                            st.session_state[replace_key] = False
                                            st.session_state['active_client_expander'] = cli['id']
                                            st.rerun()
                                elif current_val:
                                    # Marcado en la BD pero sin archivo en el repositorio
                                    st.markdown(
                                        '<div style="color:#B45309; font-size: 0.85em; '
                                        'margin-bottom: 8px;">Marcado sin archivo · '
                                        'adjunte el documento</div>',
                                        unsafe_allow_html=True)

                                archivo_doc = st.file_uploader(
                                    doc, accept_multiple_files=False,
                                    label_visibility="collapsed",
                                    key=f"updoc_{cli['id']}_{doc}_{st.session_state[ver_doc_key]}")

                                if archivo_doc is not None:
                                    try:
                                        res_doc = StorageService.save_single_document(
                                            archivo_doc, cli['cedula_rif'], cli['nombre'], doc)

                                        # Conserva el resto del checklist y marca este ítem
                                        docs_persist = {
                                            d: bool(st.session_state.get(_chk_key(i), docs.get(d, False)))
                                            for i, d in enumerate(docs_list)
                                        }
                                        docs_persist[doc] = True
                                        docs_updated[doc] = True

                                        if en_reemplazo and current_val:
                                            # El estado ya era True: solo se sustituye el archivo
                                            st.session_state[doc_msg_key] = (
                                                f"♻️ {res_doc['archivo']} reemplazado en "
                                                f"{res_doc['carpeta']}")
                                            st.session_state[replace_key] = False
                                        else:
                                            completados_p = sum(docs_persist.values())
                                            new_kyc_p = cli['kyc_status']
                                            if new_kyc_p == 'Prospecto' and completados_p > 0:
                                                new_kyc_p = 'KYC Pendiente'

                                            ClienteDAO.update_docs_and_status(
                                                cli['id'], json.dumps(docs_persist), new_kyc_p)

                                            st.session_state[doc_msg_key] = (
                                                f"✅ {res_doc['archivo']} guardado en "
                                                f"{res_doc['carpeta']}")

                                        get_sidebar_metrics.clear()

                                        # Sale del modo reemplazo y limpia el uploader
                                        st.session_state[replace_key] = False
                                        st.session_state[ver_doc_key] += 1
                                        st.session_state['active_client_expander'] = cli['id']
                                        st.rerun()
                                    except NotImplementedError as e:
                                        st.warning(str(e))
                                    except ValueError as e:
                                        st.warning(str(e))
                                    except Exception as e:
                                        st.error(f"Error al guardar {doc}: {e}")

                        completados = sum(docs_updated.values())
                        total_docs  = len(docs_list)
                        pct = int(completados / total_docs * 100) if total_docs > 0 else 0

                        st.markdown(f"""
                        <div style="margin-top: 15px; margin-bottom: 15px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                                <span style="font-size: 0.85em; font-weight: 600; color: #475569;">Progreso KYC</span>
                                <span style="font-size: 0.85em; font-weight: 700; color: #1E293B;">{completados}/{total_docs} ({pct}%)</span>
                            </div>
                            <div style="width: 100%; background-color: #E2E8F0; border-radius: 10px; height: 10px; overflow: hidden;">
                                <div style="width: {pct}%; background-color: #10B981; height: 100%; border-radius: 10px; transition: width 0.4s ease;"></div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                        if st.button("Guardar", key=f"save_docs_{cli['id']}"):
                            new_kyc = cli['kyc_status']
                            if new_kyc == 'Prospecto' and completados > 0:
                                new_kyc = 'KYC Pendiente'
                            ClienteDAO.update_docs_and_status(cli['id'], json.dumps(docs_updated), new_kyc)
                            st.session_state['active_client_expander'] = cli['id']
                            st.success("Documentos guardados."); st.rerun()

                    with col_kyc:
                        st.markdown("**Estado KYC**")
                        st.markdown(kyc_badge(cli['kyc_status']), unsafe_allow_html=True)
                        st.markdown(f"<small style='color:#94A3B8'>Registrado: {cli['fecha_registro']}</small>",
                                    unsafe_allow_html=True)

                        kyc_aprob = cli.get('kyc_aprobado_por')
                        if kyc_aprob and pd.notna(kyc_aprob):
                            st.markdown(
                                f"<small style='color:#059669'>Aprobado por <strong>"
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
                                st.session_state['active_client_expander'] = cli['id']
                                st.success("KYC Aprobado."); st.rerun()
                        elif cli['kyc_status'] == 'KYC Aprobado':
                            if st.button("🔄 Marcar como Activo", key=f"activo_{cli['id']}",
                                         width='stretch'):
                                ClienteDAO.update_kyc_status(cli['id'], 'Activo')
                                st.session_state['active_client_expander'] = cli['id']
                                st.rerun()

                        if st.button("📝 Guardar Observaciones", key=f"save_obs_{cli['id']}",
                                     width='stretch'):
                            ClienteDAO.update_kyc_observations(cli['id'], obs_kyc_new)
                            st.session_state['active_client_expander'] = cli['id']
                            st.success("Observaciones actualizadas."); st.rerun()

                # ══ Pestaña 2: Expedientes vinculados ═════════════════
                with tab_expedientes:
                    st.markdown("**📁 Expedientes Vinculados**")
                    # Match by name as fallback since id linking is not explicitly enforced yet
                    exp_corp = df_corp[df_corp['cliente'] == cli['nombre']] if not df_corp.empty else pd.DataFrame()
                    exp_auto = df_auto[df_auto['cliente'] == cli['nombre']] if not df_auto.empty else pd.DataFrame()

                    total_vinc = len(exp_corp) + len(exp_auto)
                    if total_vinc > 0:
                        if not exp_corp.empty:
                            for _, ec in exp_corp.iterrows():
                                e1, e2 = st.columns([3, 1])
                                e1.markdown(
                                    f"{APP_ICONS['corporativo']} {ec['cliente']} — ${ec['monto']:,.0f} "
                                    f"{badge(ec['dictamen'])}", unsafe_allow_html=True)
                                if e2.button("Ver", key=f"v_corp_{ec['id']}"):
                                    modal_detalle_expediente(ec, 'corp')
                        if not exp_auto.empty:
                            for _, ea in exp_auto.iterrows():
                                a1, a2 = st.columns([3, 1])
                                a1.markdown(
                                    f"{APP_ICONS['automotriz']} {ea['cliente']} {ea['marca']} {ea['modelo']} — "
                                    f"${ea['monto']:,.0f} {badge(ea['dictamen'])}", unsafe_allow_html=True)
                                if a2.button("Ver", key=f"v_auto_{ea['id']}"):
                                    modal_detalle_expediente(ea, 'auto')
                    else:
                        st.caption("Sin expedientes vinculados aún.")

                # ══ Pestaña 3: Repositorio documental ═════════════════
                with tab_documentos:
                    upl_msg_key = f"upl_msg_{cli['id']}"
                    if st.session_state.get(upl_msg_key):
                        st.success(st.session_state[upl_msg_key])
                        st.session_state[upl_msg_key] = None

                    st.markdown(f"""
                    <div class="kfg-card" style="padding:14px 18px;margin-bottom:12px">
                        <div style="display:flex;align-items:center;gap:12px">
                            <div style="width:32px;height:32px;background:linear-gradient(135deg,#0B1D4E,#1E3A8A);
                                        border-radius:8px;display:flex;align-items:center;
                                        justify-content:center;flex-shrink:0">{APP_ICONS['onboarding']}</div>
                            <div>
                                <div style="color:#0B1D4E;font-weight:700;font-size:0.95em">Repositorio Documental</div>
                                <div style="color:#64748B;font-size:0.82em">
                                    Destino: <strong>clients/{cli['cedula_rif']} {cli['nombre']}</strong>
                                    &nbsp;·&nbsp; Proveedor: <strong>{StorageService.get_provider()}</strong>
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    with st.container(border=True):
                        ver_key = f"upl_ver_{cli['id']}"
                        if ver_key not in st.session_state:
                            st.session_state[ver_key] = 0

                        archivos = st.file_uploader(
                            "Cargar documentos del cliente",
                            accept_multiple_files=True,
                            key=f"upl_{cli['id']}_{st.session_state[ver_key]}")

                        if st.button("Subir Archivos", key=f"btn_upl_{cli['id']}", width='stretch'):
                            if not archivos:
                                st.warning("Seleccione al menos un archivo antes de subir.")
                            else:
                                try:
                                    res = StorageService.save_client_documents(
                                        archivos, cli['cedula_rif'], cli['nombre'])
                                    n_ok = len(res['guardados'])

                                    if res['errores']:
                                        detalle = "; ".join(f"{n} ({m})" for n, m in res['errores'])
                                        st.error(f"No se pudieron guardar: {detalle}")

                                    if n_ok:
                                        msg = f"✅ {n_ok} archivo(s) guardado(s) en {res['carpeta']}"
                                        st.success(msg)
                                        st.session_state[upl_msg_key] = msg
                                        # Rota la key del uploader para limpiar la selección
                                        st.session_state[ver_key] += 1
                                        st.session_state['active_client_expander'] = cli['id']
                                        st.rerun()
                                except NotImplementedError as e:
                                    st.warning(str(e))
                                except ValueError as e:
                                    st.warning(str(e))
                                except Exception as e:
                                    st.error(f"Error al guardar los documentos: {e}")

                    # ── Archivos ya cargados ──────────────────────────────
                    archivos_cargados = StorageService.list_client_documents(
                        cli['cedula_rif'], cli['nombre'])

                    if archivos_cargados:
                        st.markdown("**Archivos Cargados**")
                        for i_f, nombre_archivo in enumerate(archivos_cargados):
                            col1, col2 = st.columns([3, 1])

                            with col1:
                                st.markdown(
                                    f"<div style='color:#334155; font-size:0.88em; "
                                    f"padding-top:8px;'>{nombre_archivo}</div>",
                                    unsafe_allow_html=True)

                            with col2:
                                data_f = StorageService.get_file_bytes(
                                    cli['cedula_rif'], cli['nombre'], nombre_archivo)
                                if data_f is not None:
                                    st.download_button(
                                        "Descargar", data=data_f, file_name=nombre_archivo,
                                        key=f"dlrep_{cli['id']}_{i_f}", type="primary",
                                        width='stretch')
                                else:
                                    st.caption("No disponible")
    else:
        st.info("No hay clientes registrados. Use la sección **Registrar Cliente** del menú lateral para comenzar.")
