import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io

from utils import page_header, paginate_dataframe, APP_ICONS
from database.daos_sqlserver import (
    ExpedienteCorporativoDAO,
    ExpedienteAutomotrizDAO,
    ClienteDAO,
    PlanPagoDAO,
    GestionCobranzaDAO
)

def show():
    page_header("portfolio", "Gestión de Cartera",
                "Análisis 360° de cartera, flujo de caja y exportación",
                "KFG Risk Architect · Cartera")
    hoy_c = datetime.now().date()
    hoy_cs = hoy_c.strftime("%Y-%m-%d")

    # Cargar todo mediante DAOs
    with st.spinner("Consolidando datos de cartera y flujo de caja..."):
        df_wf_all  = ExpedienteCorporativoDAO.get_all_as_df()
        df_au_all  = ExpedienteAutomotrizDAO.get_all_as_df()
        df_cli_c   = ClienteDAO.get_all_as_df()
        df_pp_c    = PlanPagoDAO.get_all_as_df()
        df_gest_c  = GestionCobranzaDAO.get_all_as_df()

    df_wf_ap = df_wf_all[df_wf_all['dictamen'] == 'APROBADO'].copy() if not df_wf_all.empty else pd.DataFrame()
    df_au_ap = df_au_all[df_au_all['dictamen'] == 'APROBADO'].copy() if not df_au_all.empty else pd.DataFrame()

    # ── KPIs de cartera ───────────────────────────
    total_corp_c  = df_wf_ap['monto'].sum() if not df_wf_ap.empty else 0
    total_auto_c  = df_au_ap['monto'].sum() if not df_au_ap.empty else 0
    total_cart    = total_corp_c + total_auto_c
    n_activos     = len(df_wf_ap) + len(df_au_ap)
    n_pend_all    = len(df_wf_all[df_wf_all['dictamen']=='PENDIENTE']) if not df_wf_all.empty else 0
    n_pend_all   += len(df_au_all[df_au_all['dictamen']=='PENDIENTE']) if not df_au_all.empty else 0
    n_rechaz      = len(df_wf_all[df_wf_all['dictamen']=='RECHAZADO']) if not df_wf_all.empty else 0
    n_rechaz     += len(df_au_all[df_au_all['dictamen']=='RECHAZADO']) if not df_au_all.empty else 0

    if not df_pp_c.empty:
        pp_venc_c  = df_pp_c[(df_pp_c['estado']=='PENDIENTE') & (df_pp_c['fecha_pago'] < hoy_cs)]
        pp_prox_c  = df_pp_c[(df_pp_c['estado']=='PENDIENTE') &
                              (df_pp_c['fecha_pago'] >= hoy_cs) &
                              (df_pp_c['fecha_pago'] <= (hoy_c+timedelta(days=30)).strftime("%Y-%m-%d"))]
        recaudado  = df_pp_c[df_pp_c['estado']=='PAGADO']['cuota'].sum()
        por_cobrar = df_pp_c[df_pp_c['estado']=='PENDIENTE']['cuota'].sum()
    else:
        pp_venc_c = pd.DataFrame(); pp_prox_c = pd.DataFrame()
        recaudado = por_cobrar = 0

    ck1, ck2, ck3, ck4, ck5 = st.columns(5)
    ck1.metric("Cartera Total", f"${total_cart:,.0f}")
    ck2.metric("Créditos Activos", n_activos)
    ck3.metric("Recaudado", f"${recaudado:,.0f}")
    ck4.metric("Por Cobrar", f"${por_cobrar:,.0f}")
    ck5.metric("Vencido", f"${pp_venc_c['cuota'].sum():,.0f}" if not pp_venc_c.empty else "$0")

    st.divider()

    cart_tab1, cart_tab2, cart_tab3, cart_tab4 = st.tabs(
        ["Analítica", "Vista 360° por Cliente", "Flujo de Caja", "Exportar"])

    # ────────────────── TAB 1: ANALÍTICA ────────────────
    with cart_tab1:
        ca1, ca2 = st.columns(2)

        with ca1:
            st.markdown("**Distribución de Cartera por Tipo**")
            dist_data = pd.DataFrame({
                'Tipo': ['Corporativo', 'Automotriz'],
                'Monto': [total_corp_c, total_auto_c]
            }).set_index('Tipo')
            if dist_data['Monto'].sum() > 0:
                st.bar_chart(dist_data)
            else:
                st.info("Sin cartera aprobada.")

        with ca2:
            st.markdown("**Expedientes por Estado**")
            est_data = pd.DataFrame({
                'Estado': ['Aprobado', 'Pendiente', 'Rechazado'],
                'Cantidad': [n_activos, n_pend_all, n_rechaz]
            }).set_index('Estado')
            st.bar_chart(est_data)

        st.divider()
        # Top 10 por exposición
        if not df_wf_ap.empty or not df_au_ap.empty:
            st.markdown("**Top 10 Clientes por Exposición**")
            top_corp = df_wf_ap[['cliente','monto','moneda']].copy() if not df_wf_ap.empty else pd.DataFrame(columns=['cliente','monto','moneda'])
            top_auto = df_au_ap[['cliente','monto','moneda']].copy() if not df_au_ap.empty else pd.DataFrame(columns=['cliente','monto','moneda'])
            top_corp['tipo'] = 'Corporativo'
            top_auto['tipo'] = 'Automotriz'
            top_all = pd.concat([top_corp, top_auto], ignore_index=True)
            top10 = top_all.groupby('cliente')['monto'].sum().sort_values(ascending=False).head(10).reset_index()
            top10.columns = ['Cliente', 'Exposición Total']
            top10['Exposición Total'] = top10['Exposición Total'].apply(lambda x: f"${x:,.2f}")
            top10.insert(0, '#', range(1, len(top10)+1))
            st.dataframe(top10, width='stretch', hide_index=True)

        st.divider()
        # Estado de cobranza
        if not df_wf_ap.empty or not df_au_ap.empty:
            st.markdown("**Cartera por Estado de Cobranza**")
            ec_wf = df_wf_ap['estado_cobranza'].value_counts() if 'estado_cobranza' in df_wf_ap.columns else pd.Series()
            ec_au = df_au_ap['estado_cobranza'].value_counts() if 'estado_cobranza' in df_au_ap.columns else pd.Series()
            ec_all = (ec_wf.add(ec_au, fill_value=0)).astype(int)
            if not ec_all.empty:
                st.bar_chart(ec_all)

    # ────────────── TAB 2: VISTA 360° ────────────────────
    with cart_tab2:
        busq_360 = st.text_input("🔍 Buscar cliente por nombre, C.I. o RIF", key="busq360")
        all_clients_names = []
        if not df_wf_ap.empty: all_clients_names += df_wf_ap['cliente'].tolist()
        if not df_au_ap.empty: all_clients_names += df_au_ap['cliente'].tolist()
        all_clients_names = sorted(set(all_clients_names))

        if busq_360:
            filtered_360 = [c for c in all_clients_names if busq_360.lower() in str(c).lower()]
        else:
            filtered_360 = all_clients_names

        if not filtered_360:
            st.info("No se encontraron clientes con créditos activos.")
        else:
            sel_client = st.selectbox("Seleccionar cliente", filtered_360, key="sel_360")
            if sel_client:
                # Créditos corporativos del cliente
                cred_corp = df_wf_all[df_wf_all['cliente'] == sel_client] if not df_wf_all.empty else pd.DataFrame()
                cred_auto = df_au_all[df_au_all['cliente'] == sel_client] if not df_au_all.empty else pd.DataFrame()
                # Info KYC si existe
                kyc_info = df_cli_c[df_cli_c['nombre'].str.lower() == str(sel_client).lower()] if not df_cli_c.empty else pd.DataFrame()

                st.markdown(f"### 👤 {sel_client}")

                if not kyc_info.empty:
                    ki = kyc_info.iloc[0]
                    inf1, inf2, inf3, inf4 = st.columns(4)
                    inf1.markdown(f"**Tipo:** {ki.get('tipo', '')}")
                    inf2.markdown(f"**C.I./RIF:** {ki.get('cedula_rif', '')}")
                    inf3.markdown(f"**Teléfono:** {ki.get('telefono', '')}")
                    inf4.markdown(f"**KYC:** {ki.get('kyc_status', '')}")

                st.divider()
                v3_t1, v3_t2, v3_t3 = st.tabs(["Créditos", "Pagos", "Gestiones"])

                with v3_t1:
                    if not cred_corp.empty:
                        st.markdown("**Créditos Corporativos**")
                        cols_c = ['id','fecha','monto','moneda','dictamen','tasa_aprobada','score_f']
                        show_c = [c for c in cols_c if c in cred_corp.columns]
                        st.dataframe(cred_corp[show_c].rename(columns={
                            'id':'ID','fecha':'Fecha','monto':'Monto','moneda':'Moneda',
                            'dictamen':'Estado','tasa_aprobada':'Tasa %','score_f':'Score'}),
                            width='stretch', hide_index=True)
                    if not cred_auto.empty:
                        st.markdown("**Créditos Automotrices**")
                        cols_a = ['id','fecha','monto','moneda','marca','modelo','anio','dictamen','tasa_aprobada','score_f']
                        show_a = [c for c in cols_a if c in cred_auto.columns]
                        st.dataframe(cred_auto[show_a].rename(columns={
                            'id':'ID','fecha':'Fecha','monto':'Monto','moneda':'Moneda',
                            'marca':'Marca','modelo':'Modelo','anio':'Año',
                            'dictamen':'Estado','tasa_aprobada':'Tasa %','score_f':'Score'}),
                            width='stretch', hide_index=True)
                    if cred_corp.empty and cred_auto.empty:
                        st.info("Sin créditos registrados.")

                with v3_t2:
                    ids_c = cred_corp['id'].tolist() if not cred_corp.empty else []
                    ids_a = cred_auto['id'].tolist() if not cred_auto.empty else []
                    if not df_pp_c.empty and (ids_c or ids_a):
                        pp_cli = df_pp_c[
                            ((df_pp_c['expediente_id'].isin(ids_c)) & (df_pp_c['tipo_expediente']=='corp')) |
                            ((df_pp_c['expediente_id'].isin(ids_a)) & (df_pp_c['tipo_expediente']=='auto'))
                        ]
                    else:
                        pp_cli = pd.DataFrame()

                    if pp_cli.empty:
                        st.info("Sin plan de pagos generado.")
                    else:
                        p_pag = pp_cli[pp_cli['estado']=='PAGADO']['cuota'].sum()
                        p_pen = pp_cli[pp_cli['estado']=='PENDIENTE']['cuota'].sum()
                        p_ven = pp_cli[(pp_cli['estado']=='PENDIENTE')&(pp_cli['fecha_pago']<hoy_cs)]['cuota'].sum()
                        pb1, pb2, pb3 = st.columns(3)
                        pb1.metric("Total Pagado", f"${p_pag:,.2f}")
                        pb2.metric("Por Pagar", f"${p_pen:,.2f}")
                        pb3.metric("Vencido", f"${p_ven:,.2f}")
                        cols_pp = ['periodo','fecha_pago','cuota','capital','interes','saldo','estado','tipo_expediente']
                        disp_pp = pp_cli[[c for c in cols_pp if c in pp_cli.columns]].copy()
                        disp_pp.columns = ['N°','Fecha','Cuota','Capital','Interés','Saldo','Estado','Tipo']
                        disp_pp_pag = paginate_dataframe(disp_pp, page_size=10, key_prefix="port_pp")
                        st.dataframe(
                            disp_pp_pag.style.format({'Cuota':'${:,.2f}','Capital':'${:,.2f}','Interés':'${:,.2f}','Saldo':'${:,.2f}'}),
                            width='stretch', hide_index=True)

                with v3_t3:
                    all_ids = [(i,'corp') for i in ids_c] + [(i,'auto') for i in ids_a]
                    if not df_gest_c.empty and all_ids:
                        gest_cli = df_gest_c[
                            df_gest_c.apply(lambda row: (row['expediente_id'], row['tipo_expediente']) in all_ids, axis=1)
                        ]
                    else:
                        gest_cli = pd.DataFrame()
                    if gest_cli.empty:
                        st.info("Sin gestiones de cobranza registradas.")
                    else:
                        cols_g = ['fecha','tipo_gestion','responsable','resultado','proxima_accion','obs']
                        show_g = [c for c in cols_g if c in gest_cli.columns]
                        gest_cli_pag = paginate_dataframe(gest_cli[show_g], page_size=10, key_prefix="port_gest")
                        st.dataframe(gest_cli_pag.rename(columns={
                            'fecha':'Fecha','tipo_gestion':'Gestión','responsable':'Responsable',
                            'resultado':'Resultado','proxima_accion':'Próx. Acción','obs':'Observaciones'}),
                            width='stretch', hide_index=True)

    # ────────────── TAB 3: FLUJO DE CAJA ─────────────────
    with cart_tab3:
        st.markdown("**Proyección de Cobros — Próximos 90 días**")
        if df_pp_c.empty:
            st.info("Sin planes de pago generados.")
        else:
            fecha_90 = (hoy_c + timedelta(days=90)).strftime("%Y-%m-%d")
            prox90 = df_pp_c[(df_pp_c['estado']=='PENDIENTE') &
                              (df_pp_c['fecha_pago'] >= hoy_cs) &
                              (df_pp_c['fecha_pago'] <= fecha_90)].copy()
            if prox90.empty:
                st.info("No hay cobros proyectados en los próximos 90 días.")
            else:
                prox90['mes'] = prox90['fecha_pago'].str[:7]
                flujo = prox90.groupby('mes')['cuota'].sum().reset_index()
                flujo.columns = ['Mes', 'Cobros Proyectados']
                flujo = flujo.set_index('Mes')
                st.bar_chart(flujo)
                st.caption(f"Total proyectado 90 días: **${prox90['cuota'].sum():,.2f}**")

            st.divider()
            st.markdown("**Vencidos — Detalle por período**")
            if not pp_venc_c.empty:
                venc_det = pp_venc_c.copy()
                venc_det['dias_atraso'] = venc_det['fecha_pago'].apply(
                    lambda d: (hoy_c - datetime.strptime(d, "%Y-%m-%d").date()).days)
                cols_v = ['expediente_id','tipo_expediente','periodo','fecha_pago','cuota','dias_atraso']
                show_v = [c for c in cols_v if c in venc_det.columns]
                venc_det_pag = paginate_dataframe(venc_det[show_v], page_size=10, key_prefix="port_venc")
                st.dataframe(venc_det_pag.rename(columns={
                    'expediente_id':'ID Exp.','tipo_expediente':'Tipo','periodo':'N°',
                    'fecha_pago':'Fecha','cuota':'Cuota','dias_atraso':'Días Atraso'}
                ).style.format({'Cuota':'${:,.2f}'}), width='stretch', hide_index=True)
            else:
                st.success("✅ No hay cuotas vencidas.")

    # ────────────── TAB 4: EXPORTAR ──────────────────────
    with cart_tab4:
        st.markdown("**Exportar Cartera a Excel**")
        st.markdown("Genera un archivo `.xlsx` con múltiples hojas: resumen ejecutivo, créditos corporativos, créditos automotrices, plan de pagos y gestiones de cobranza.")

        exp1, exp2 = st.columns(2)
        solo_aprobados = exp1.checkbox("Solo créditos aprobados", value=True)
        incluir_plan   = exp2.checkbox("Incluir plan de pagos", value=True)

        if st.button("📥 Generar Excel", type="primary"):
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                # Hoja Resumen
                resumen = pd.DataFrame({
                    'Concepto': ['Cartera Corporativa', 'Cartera Automotriz', 'Cartera Total',
                                 'Créditos Activos', 'Recaudado', 'Por Cobrar', 'Vencido'],
                    'Valor': [f"${total_corp_c:,.2f}", f"${total_auto_c:,.2f}",
                              f"${total_cart:,.2f}", n_activos,
                              f"${recaudado:,.2f}", f"${por_cobrar:,.2f}",
                              f"${pp_venc_c['cuota'].sum():,.2f}" if not pp_venc_c.empty else "$0.00"]
                })
                resumen.to_excel(writer, sheet_name='Resumen', index=False)

                # Créditos corporativos
                df_wf_exp = df_wf_ap if solo_aprobados else df_wf_all
                if not df_wf_exp.empty:
                    cols_wf = ['id','fecha','cliente','rif','monto','moneda','dictamen',
                               'tasa_aprobada','score_f','dscr','aprobado_por','fecha_decision',
                               'estado_cobranza']
                    df_wf_exp[[c for c in cols_wf if c in df_wf_exp.columns]].to_excel(
                        writer, sheet_name='Corporativo', index=False)

                # Créditos automotrices
                df_au_exp = df_au_ap if solo_aprobados else df_au_all
                if not df_au_exp.empty:
                    cols_au = ['id','fecha','cliente','cedula','monto','moneda','marca','modelo',
                               'anio','dictamen','tasa_aprobada','score_f','dti_ratio',
                               'aprobado_por','fecha_decision','estado_cobranza']
                    df_au_exp[[c for c in cols_au if c in df_au_exp.columns]].to_excel(
                        writer, sheet_name='Automotriz', index=False)

                # Plan de pagos
                if incluir_plan and not df_pp_c.empty:
                    df_pp_c.to_excel(writer, sheet_name='Plan de Pagos', index=False)

                # Gestiones de cobranza
                if not df_gest_c.empty:
                    df_gest_c.to_excel(writer, sheet_name='Gestiones Cobranza', index=False)

                # Clientes
                if not df_cli_c.empty:
                    cli_cols = ['id','fecha_registro','tipo','nombre','cedula_rif',
                                'telefono','email','actividad_economica','kyc_status']
                    df_cli_c[[c for c in cli_cols if c in df_cli_c.columns]].to_excel(
                        writer, sheet_name='Clientes', index=False)

            buf.seek(0)
            fecha_exp = datetime.now().strftime("%Y%m%d_%H%M")
            st.download_button(
                label="⬇️ Descargar Excel",
                data=buf,
                file_name=f"KFG_Cartera_{fecha_exp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
