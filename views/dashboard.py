import streamlit as st
import pandas as pd
from datetime import datetime, date
from database.daos_sqlserver import ExpedienteCorporativoDAO, ExpedienteAutomotrizDAO
from utils import APP_ICONS
from services.auth_service import AuthService

@st.cache_data(ttl=60)
def _load_dashboard_data():
    df_corp = ExpedienteCorporativoDAO.get_all_as_df()
    df_auto = ExpedienteAutomotrizDAO.get_all_as_df()
    return df_corp, df_auto

def show():
    # Nota: Nombramos a la función 'show()' en lugar de 'render()' para mantener
    # la compatibilidad directa con el enrutador route.py que configuramos previamente.
    
    role = AuthService.get_current_role()
    current_user = st.session_state.get('current_user', 'Usuario')

    # ── Carga de Datos mediante Capa DAO ──
    with st.spinner("Cargando dashboard..."):
        df_corp, df_auto = _load_dashboard_data()

        # Helpers para calcular alertas basados en los DataFrames cargados
        def _p(df, col): 
            if df.empty: return 0
            return len(df[(df[col] == 0) & (df['dictamen'] == 'PENDIENTE')])

        n_comp  = _p(df_corp, 'status_comp')  + _p(df_auto, 'status_comp')
        n_leg   = _p(df_corp, 'status_leg')   + _p(df_auto, 'status_leg')
        n_ries  = _p(df_corp, 'status_riesgo')+ _p(df_auto, 'status_riesgo')
        
        listos_c = df_corp[(df_corp['status_comp']==1)&(df_corp['status_leg']==1)&(df_corp['status_riesgo']==1)&(df_corp['dictamen']=='PENDIENTE')] if not df_corp.empty else pd.DataFrame()
        listos_a = df_auto[(df_auto['status_comp']==1)&(df_auto['status_leg']==1)&(df_auto['status_riesgo']==1)&(df_auto['dictamen']=='PENDIENTE')] if not df_auto.empty else pd.DataFrame()
        n_comite = len(listos_c) + len(listos_a)

    # ── Construcción de la Interfaz Visual ──
    hora = datetime.now().hour
    saludo = "Buenos días" if hora < 12 else "Buenas tardes" if hora < 19 else "Buenas noches"
    nombre = current_user.split('@')[0].replace('.', ' ').title()
    meses_es = ["enero","febrero","marzo","abril","mayo","junio",
                "julio","agosto","septiembre","octubre","noviembre","diciembre"]
    fecha_fmt = f"{datetime.now().day} de {meses_es[datetime.now().month-1]} de {datetime.now().year}"
    
    # Banner Principal de Bienvenida
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#0B1D4E 0%,#1E3A8A 60%,#2563EB 100%);
                border-radius:16px;padding:26px 32px;margin-bottom:24px;color:white;
                box-shadow:0 8px 32px rgba(11,29,78,0.22);position:relative;overflow:hidden">
        <div style="position:absolute;right:-20px;top:-20px;width:160px;height:160px;
                    background:rgba(255,255,255,0.04);border-radius:50%"></div>
        <div style="position:absolute;right:60px;bottom:-40px;width:100px;height:100px;
                    background:rgba(255,255,255,0.03);border-radius:50%"></div>
        <div style="position:relative">
            <div style="font-size:0.75em;font-weight:600;letter-spacing:0.1em;
                        text-transform:uppercase;color:rgba(255,255,255,0.6);margin-bottom:6px">
                KFG Risk Architect v32.0
            </div>
            <h2 style="border:none!important;margin:0;font-size:1.6em;font-weight:800;letter-spacing:-0.02em">
                <span style="color:rgba(255,255,255,0.90);">{saludo}, {nombre} 👋</span>
            </h2>
            <p style="color:rgba(255,255,255,0.70);margin:6px 0 0;font-size:0.88em">
                {fecha_fmt} &nbsp;·&nbsp; Rol: <strong style="color:rgba(255,255,255,0.95)">{role}</strong>
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Bloque de KPIs
    total_exp = len(df_corp) + len(df_auto)
    total_ap = 0
    total_pend = 0
    cartera = 0

    if not df_corp.empty:
        total_ap += len(df_corp[df_corp['dictamen']=='APROBADO'])
        total_pend += len(df_corp[df_corp['dictamen']=='PENDIENTE'])
        cartera += df_corp[df_corp['dictamen']=='APROBADO']['monto'].sum()
    
    if not df_auto.empty:
        total_ap += len(df_auto[df_auto['dictamen']=='APROBADO'])
        total_pend += len(df_auto[df_auto['dictamen']=='PENDIENTE'])
        cartera += df_auto[df_auto['dictamen']=='APROBADO']['monto'].sum()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Expedientes", f"{total_exp:,}",border=True)
    k2.metric("En Proceso", f"{total_pend:,}",border=True)
    k3.metric("Aprobados", f"{total_ap:,}",border=True)
    k4.metric("Valor Total Cartera", f"${cartera:,.0f}",border=True)

    st.markdown("---")

    # Sección Principal dividida en dos columnas
    left, right = st.columns([1, 1])
    
    
    st.markdown(f"### {APP_ICONS['campana']} Alertas Operativas", unsafe_allow_html=True)
    alerts = []
    # Definición de alertas (bg, border, dot_color, icon, label)
    if n_comp  > 0: alerts.append((APP_ICONS['compliance'].replace('white', '#3B82F6'), f"{n_comp} expediente(s) pendiente(s) en Cumplimiento", "#EFF6FF","#3B82F6"))
    if n_leg   > 0: alerts.append((APP_ICONS['legal'].replace('white', '#8B5CF6'), f"{n_leg} expediente(s) pendiente(s) en Legal", "#F5F3FF","#8B5CF6"))
    if n_ries  > 0: alerts.append((APP_ICONS['risk'].replace('white', '#F59E0B'), f"{n_ries} expediente(s) pendiente(s) en Riesgo", "#FFFBEB","#F59E0B"))
    if n_comite> 0: alerts.append((APP_ICONS['comite'].replace('white', '#10B981'), f"{n_comite} expediente(s) listos para Comité", "#F0FDF4","#10B981"))
    
    hoy = date.today()
    # Verificación de vencimientos (Garantías - Corp)
    if not df_corp.empty and 'fecha_vencimiento_garantia' in df_corp.columns:
        for _, r in df_corp[df_corp['fecha_vencimiento_garantia'].notna()].iterrows():
            try:
                fv_str = r['fecha_vencimiento_garantia']
                if fv_str and str(fv_str).strip():
                    fv = date.fromisoformat(str(fv_str).strip())
                    dias = (fv - hoy).days
                    if 0 <= dias < 90:
                        alerts.append((APP_ICONS['alerta'].replace('currentColor', '#F97316'), f"Garantía de {r['cliente']} vence en {dias} días", "#FFF7ED","#F97316"))
            except Exception: pass

        # Verificación de vencimientos (Seguros - Auto)
        if not df_auto.empty and 'fecha_vencimiento_seguro' in df_auto.columns:
            for _, r in df_auto[df_auto['fecha_vencimiento_seguro'].notna()].iterrows():
                try:
                    fv_str = r['fecha_vencimiento_seguro']
                    if fv_str and str(fv_str).strip():
                        fv = date.fromisoformat(str(fv_str).strip())
                        dias = (fv - hoy).days
                        if 0 <= dias < 30:
                            alerts.append((APP_ICONS['automotriz'].replace('currentColor', '#F97316'), f"Seguro de {r['cliente']} vence en {dias} días", "#FFF7ED","#F97316"))
                except Exception: pass
    
        
        if alerts:
            for ic, msg, bg, border in alerts:
                st.markdown(
                    f'<div style="background:{bg};border-left:3px solid {border};'
                    f'border-radius:0 8px 8px 0;padding:9px 14px;margin:5px 0;'
                    f'font-size:0.87em;color:#1E293B;display:flex;align-items:center;gap:8px">'
                    f'<span style="font-size:1em">{ic}</span> {msg}</div>',
                    unsafe_allow_html=True)
        else:
            st.success("✅ Sin alertas activas. Todo al día.")

    st.markdown("---")
    st.markdown(f"### {APP_ICONS['reloj'].replace('currentColor', '#183177')} Actividad Reciente", unsafe_allow_html=True)
    frames = []
    if not df_corp.empty:
        tmp = df_corp[['fecha','cliente','monto','dictamen']].copy()
        tmp.insert(0,'Tipo','Corporativo')
        frames.append(tmp)
    if not df_auto.empty:
        tmp = df_auto[['fecha','cliente','monto','dictamen']].copy()
        tmp.insert(0,'Tipo','Automotriz')
        frames.append(tmp)
    if frames:
        recent = pd.concat(frames).sort_values('fecha', ascending=False).head(8)
        recent.columns = ['Tipo','Fecha','Cliente','Monto','Estado']
        recent['Monto'] = recent['Monto'].apply(lambda x: f"${float(x):,.0f}")
        st.dataframe(recent, use_container_width=True, hide_index=True)
    else:
        st.info("Sin actividad registrada aún.")
    
    st.markdown("---")

    # Bloque de Resumen de Cartera
    st.markdown(f"### {APP_ICONS['cartera']} Resumen de Cartera", unsafe_allow_html=True)
    s1, s2 = st.columns(2)
    with s1:
        st.markdown("**Corporativo**")
        if not df_corp.empty:
            resumen_c = df_corp['dictamen'].value_counts().reset_index()
            resumen_c.columns = ['Estado','Expedientes']
            st.dataframe(resumen_c, use_container_width=True, hide_index=True)
        else:
            st.info("Sin expedientes corporativos.")
    with s2:
        st.markdown("**Automotriz**")
        if not df_auto.empty:
            resumen_a = df_auto['dictamen'].value_counts().reset_index()
            resumen_a.columns = ['Estado','Expedientes']
            st.dataframe(resumen_a, use_container_width=True, hide_index=True)
        else:
            st.info("Sin expedientes automotrices.")
