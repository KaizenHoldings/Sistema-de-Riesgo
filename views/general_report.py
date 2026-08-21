import streamlit as st
import pandas as pd
from datetime import datetime

from utils import page_header, badge, sig_badge, paginate_dataframe, APP_ICONS
from database.daos_sqlserver import ExpedienteCorporativoDAO, ExpedienteAutomotrizDAO
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
/* Botón de descarga primario: texto blanco sobre el fondo oscuro. */
[data-testid="stDownloadButton"] button[kind="primary"],
[data-testid="stDownloadButton"] button[kind="primary"] *,
[data-testid="stDownloadButton"] [data-testid="stBaseButton-primary"],
[data-testid="stDownloadButton"] [data-testid="stBaseButton-primary"] * {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)

# Etapas a las que puede devolverse un expediente para corrección
ETAPAS_DEVOLUCION = ["Comercial", "Cumplimiento", "Legal", "Riesgo"]

# Opciones del filtro de dictamen
OPCIONES_DICTAMEN = ["Todos", "PENDIENTE", "APROBADO", "RECHAZADO", "REVISIÓN"]


def _dao(tipo):
    """DAO correspondiente al tipo de expediente."""
    return ExpedienteCorporativoDAO if tipo == 'corp' else ExpedienteAutomotrizDAO


# ══ Modales administrativos ═══════════════════════════════════════════
@st.dialog("Rechazar Expediente")
def modal_rechazar_expediente(r, tipo):
    st.error(f"### Rechazo definitivo de **{r['cliente']}**")
    st.write("El expediente quedará marcado como RECHAZADO, con su usuario y fecha registrados.")

    motivo = st.text_area("Motivo final del rechazo (obligatorio)",
                          key=f"rep_motivo_{tipo}_{r['id']}", height=110)

    if st.button("Confirmar Rechazo Definitivo", type="primary", width='stretch'):
        if not motivo.strip():
            st.warning("Debe indicar el motivo del rechazo.")
        else:
            with st.spinner("Registrando rechazo..."):
                _dao(tipo).rechazar_expediente(
                    exp_id=r['id'], obs=motivo.strip(),
                    usuario=st.session_state.get('current_user', 'Admin'),
                    fecha=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            get_sidebar_metrics.clear()
            st.success(f"Expediente de {r['cliente']} rechazado.")
            st.rerun()


@st.dialog("Devolver para Corrección")
def modal_devolver_expediente(r, tipo):
    st.warning(f"### Devolver **{r['cliente']}** para corrección")
    st.write("El expediente pasará a estado de revisión de la etapa seleccionada.")

    etapa = st.selectbox("Etapa destino", ETAPAS_DEVOLUCION,
                         key=f"rep_etapa_{tipo}_{r['id']}")
    obs = st.text_area("Observaciones (obligatorio)",
                       key=f"rep_obs_{tipo}_{r['id']}", height=110)

    if st.button("Confirmar Devolución", type="primary", width='stretch'):
        if not obs.strip():
            st.warning("Debe indicar las observaciones de la devolución.")
        else:
            with st.spinner("Registrando devolución..."):
                _dao(tipo).devolver_expediente(
                    exp_id=r['id'], etapa_destino=etapa, observaciones=obs.strip(),
                    usuario=st.session_state.get('current_user', 'Admin'),
                    fecha=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            get_sidebar_metrics.clear()
            st.success(f"Expediente devuelto a {etapa}.")
            st.rerun()


# ══ Filtrado ══════════════════════════════════════════════════════════
def _aplicar_filtros(df, f_dictamen, chk_comp, chk_leg, chk_riesgo):
    """Filtra por dictamen y por las firmas marcadas como requeridas."""
    if df.empty:
        return df

    d = df.copy()

    if f_dictamen == "REVISIÓN":
        # Los estados de revisión se guardan como 'REVISION-{etapa}'
        d = d[d['dictamen'].astype(str).str.upper().str.startswith("REVISI")]
    elif f_dictamen != "Todos":
        d = d[d['dictamen'] == f_dictamen]

    # Cada checkbox marcado exige que esa firma esté completa
    for col, exigida in (('status_comp', chk_comp),
                         ('status_leg', chk_leg),
                         ('status_riesgo', chk_riesgo)):
        if exigida:
            d = d[d[col] == 1]

    return d


# ══ Render de un expediente ═══════════════════════════════════════════
def _render_expediente(r, tipo):
    """Expander que actúa como .kfg-card para un expediente."""
    doc = r.get('rif') if tipo == 'corp' else r.get('cedula')
    doc = str(doc).upper() if pd.notna(doc) else ''

    titulo = f"{r['cliente']}  ·  {r.get('moneda', 'USD')} {r['monto']:,.2f}  ·  {r['dictamen']}"

    with st.expander(titulo):
        st.markdown(
            f"<div class='kfg-card' style='padding:14px 18px;margin-bottom:12px'>"
            f"<strong style='color:#0B1D4E'>{r['cliente']}</strong> &nbsp; | &nbsp; "
            f"<span style='color:#64748B;font-size:0.9em'>{doc}</span> &nbsp; "
            f"{badge(r['dictamen'])}<br>"
            f"<span style='color:#64748B;font-size:0.85em'>"
            f"{r.get('moneda', 'USD')} {r['monto']:,.2f} &nbsp;·&nbsp; "
            f"Creado: {r.get('fecha', '')}</span>"
            f"</div>",
            unsafe_allow_html=True)

        # ── Firmas ──
        st.markdown("**Estado de Firmas**")
        f1, f2, f3 = st.columns(3)
        f1.markdown(f"Cumplimiento &nbsp; {sig_badge(r['status_comp'])}", unsafe_allow_html=True)
        f2.markdown(f"Legal &nbsp; {sig_badge(r['status_leg'])}", unsafe_allow_html=True)
        f3.markdown(f"Riesgo &nbsp; {sig_badge(r['status_riesgo'])}", unsafe_allow_html=True)

        # ── Métricas financieras ──
        st.markdown("**Métricas Financieras**")
        m1, m2, m3 = st.columns(3)
        m1.metric("Score", r.get('score_f', 'N/A'))
        if tipo == 'corp':
            m2.metric("DSCR", f"{r.get('dscr', 0):.2f}x")
        else:
            m2.metric("DTI Ratio", f"{r.get('dti_ratio', 0):.2f}%")
        m3.metric("LTV", f"{r.get('ltv_ratio', 0):.2f}%")

        if tipo == 'auto':
            st.markdown(
                f"<span style='font-size:0.85em;color:#64748B'>{APP_ICONS['automotriz']} "
                f"{r.get('marca','')} {r.get('modelo','')} {r.get('anio','')}</span>",
                unsafe_allow_html=True)

        # ── Observaciones activas ──
        devuelto = r.get('devuelto_a')
        obs_dec = r.get('obs_decision')
        en_revision = str(r['dictamen']).upper().startswith("REVISI")

        if en_revision and devuelto and pd.notna(devuelto) and str(devuelto).strip():
            st.markdown(
                f"<div style='background:#FEF3C7;border:1px solid #FDE68A;border-radius:8px;"
                f"padding:10px 14px;margin-top:10px'>"
                f"<span style='color:#B45309;font-size:0.85em;font-weight:700'>"
                f"↩️ Devuelto a {devuelto}</span><br>"
                f"<span style='color:#92400E;font-size:0.83em'>{obs_dec or ''}</span></div>",
                unsafe_allow_html=True)
        elif r['dictamen'] == 'RECHAZADO' and obs_dec and pd.notna(obs_dec) and str(obs_dec).strip():
            st.markdown(
                f"<div style='background:#FEE2E2;border:1px solid #FECACA;border-radius:8px;"
                f"padding:10px 14px;margin-top:10px'>"
                f"<span style='color:#B91C1C;font-size:0.85em;font-weight:700'>"
                f"Motivo del rechazo</span><br>"
                f"<span style='color:#991B1B;font-size:0.83em'>{obs_dec}</span></div>",
                unsafe_allow_html=True)

        if r.get('aprobado_por') and pd.notna(r.get('aprobado_por')) and str(r.get('aprobado_por')).strip():
            st.caption(f"Última decisión por **{r['aprobado_por']}** "
                       f"el {r.get('fecha_decision', 'N/A')}")

        # ── Acciones administrativas ──
        st.markdown("---")
        b1, b2, _ = st.columns([1, 1, 2])
        if b1.button("❌ Rechazar", key=f"rep_rj_{tipo}_{r['id']}", width='stretch'):
            modal_rechazar_expediente(r, tipo)
        if b2.button("↩️ Devolver", key=f"rep_dv_{tipo}_{r['id']}", width='stretch'):
            modal_devolver_expediente(r, tipo)


def _panel(df, tipo, key_prefix, f_dictamen, chk_comp, chk_leg, chk_riesgo):
    """Filtra, pagina y renderiza los expedientes de una pestaña."""
    df_vis = _aplicar_filtros(df, f_dictamen, chk_comp, chk_leg, chk_riesgo)

    if df_vis.empty:
        st.info("No hay expedientes que cumplan los filtros seleccionados.")
        return

    st.caption(f"Mostrando {len(df_vis)} de {len(df)} expedientes")
    df_pag = paginate_dataframe(df_vis, page_size=10, key_prefix=key_prefix)
    for _, r in df_pag.iterrows():
        _render_expediente(r, tipo)


# ══ Vista ═════════════════════════════════════════════════════════════
def show():
    page_header("dashboard", "Reporte General de Expedientes",
                "Panel centralizado de trazabilidad, estatus y firmas")

    with st.spinner("Cargando expedientes..."):
        df_corp = ExpedienteCorporativoDAO.get_all_as_df()
        df_auto = ExpedienteAutomotrizDAO.get_all_as_df()

    if df_corp.empty and df_auto.empty:
        st.info("No hay expedientes registrados.")
        return

    # ── Filtros unificados ────────────────────────────────
    st.markdown("**Filtros**")
    c_dict, c_comp, c_leg, c_ries = st.columns([2, 1, 1, 1])

    f_dictamen = c_dict.selectbox("Dictamen", OPCIONES_DICTAMEN, key="rep_f_dictamen")
    chk_comp = c_comp.checkbox("Cumplimiento firmado", key="rep_chk_comp")
    chk_leg = c_leg.checkbox("Legal firmado", key="rep_chk_leg")
    chk_riesgo = c_ries.checkbox("Riesgo firmado", key="rep_chk_ries")

    st.markdown("---")

    tab_corp, tab_auto = st.tabs(["Créditos Corporativos", "Créditos Automotrices"])

    with tab_corp:
        if df_corp.empty:
            st.info("No hay expedientes corporativos.")
        else:
            _panel(df_corp, 'corp', "rep_corp", f_dictamen, chk_comp, chk_leg, chk_riesgo)

    with tab_auto:
        if df_auto.empty:
            st.info("No hay expedientes automotrices.")
        else:
            _panel(df_auto, 'auto', "rep_auto", f_dictamen, chk_comp, chk_leg, chk_riesgo)
