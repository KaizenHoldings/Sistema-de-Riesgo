import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from utils import page_header, _dot_badge, paginate_dataframe, APP_ICONS
from database.daos_sqlserver import (
    PlanPagoDAO, ExpedienteCorporativoDAO, ExpedienteAutomotrizDAO,
    GestionCobranzaDAO, PagoRecibidoDAO
)

def show():
    page_header("collections", "Cobranzas & Aging Management",
                "Control de vencimientos, pagos y gestiones de cobranza",
                "KFG Risk Architect · Cobranzas")
    hoy = datetime.now().date()
    hoy_s = hoy.strftime("%Y-%m-%d")

    # Cargar datos a través de DAOs
    with st.spinner("Analizando vencimientos y gestiones de cobro..."):
        df_plan = PlanPagoDAO.get_all_as_df()
        df_corp_all = ExpedienteCorporativoDAO.get_all_as_df()
        df_auto_all = ExpedienteAutomotrizDAO.get_all_as_df()
        df_gest = GestionCobranzaDAO.get_all_as_df()

    df_corp_ap2 = df_corp_all[df_corp_all['dictamen'] == 'APROBADO'].copy() if not df_corp_all.empty else pd.DataFrame()
    df_auto_ap2 = df_auto_all[df_auto_all['dictamen'] == 'APROBADO'].copy() if not df_auto_all.empty else pd.DataFrame()

    # ── KPIs ─────────────────────────────────────────
    if not df_plan.empty:
        venc   = df_plan[(df_plan['estado'] == 'PENDIENTE') & (df_plan['fecha_pago'] < hoy_s)]
        prox30 = df_plan[(df_plan['estado'] == 'PENDIENTE') &
                         (df_plan['fecha_pago'] >= hoy_s) &
                         (df_plan['fecha_pago'] <= (hoy + timedelta(days=30)).strftime("%Y-%m-%d"))]
        pagadas = df_plan[df_plan['estado'] == 'PAGADO']
        n_venc_kpi = len(venc)
        monto_venc = venc['cuota'].sum()
        n_prox  = len(prox30)
        n_pagadas = len(pagadas)
    else:
        n_venc_kpi = monto_venc = n_prox = n_pagadas = 0

    ck1, ck2, ck3, ck4 = st.columns(4)
    ck1.metric("Cuotas Vencidas", n_venc_kpi,
               #delta=f"-${monto_venc:,.0f}" if monto_venc > 0 else None,
               delta_color="inverse",border=True)
    ck2.metric("Vencen en 30 días", n_prox,border=True)
    ck3.metric("Cuotas Pagadas", n_pagadas,border=True)
    total_activa = (df_corp_ap2['monto'].sum() if not df_corp_ap2.empty else 0) + \
                   (df_auto_ap2['monto'].sum() if not df_auto_ap2.empty else 0)
    ck4.metric("Cartera Activa Total", f"${total_activa:,.0f}",border=True)

    st.divider()

    # ── Aging Report ──────────────────────────────────
    st.markdown(f"### {APP_ICONS['cartera']} Reporte de Antigüedad de Deuda (Aging)", unsafe_allow_html=True)
    if not df_plan.empty and n_venc_kpi > 0:
        venc_df = venc.copy()
        venc_df['dias_atraso'] = venc_df['fecha_pago'].apply(
            lambda d: (hoy - datetime.strptime(d, "%Y-%m-%d").date()).days)
        aging_cfg = [
            ("1-30 días",  venc_df[(venc_df['dias_atraso'] >= 1)  & (venc_df['dias_atraso'] <= 30)],  "Bajo",     "#D1FAE5","#065F46","#10B981"),
            ("31-60 días", venc_df[(venc_df['dias_atraso'] >= 31) & (venc_df['dias_atraso'] <= 60)],  "Medio",    "#FEF3C7","#92400E","#F59E0B"),
            ("61-90 días", venc_df[(venc_df['dias_atraso'] >= 61) & (venc_df['dias_atraso'] <= 90)],  "Alto",     "#FFEDD5","#9A3412","#F97316"),
            ("> 90 días",  venc_df[venc_df['dias_atraso'] > 90],                                       "Crítico",  "#FEE2E2","#991B1B","#EF4444"),
        ]
        aging_html = """
        <table style="width:100%;border-collapse:collapse;font-size:0.88em;background:white;
                      border-radius:10px;overflow:hidden;border:1px solid #E2E8F0">
          <thead>
            <tr style="background:#F8FAFC">
              <th style="padding:10px 16px;text-align:left;color:#64748B;font-size:0.76em;
                         text-transform:uppercase;letter-spacing:0.06em;border-bottom:2px solid #E2E8F0">Bucket</th>
              <th style="padding:10px 16px;text-align:right;color:#64748B;font-size:0.76em;
                         text-transform:uppercase;letter-spacing:0.06em;border-bottom:2px solid #E2E8F0">N° Cuotas</th>
              <th style="padding:10px 16px;text-align:right;color:#64748B;font-size:0.76em;
                         text-transform:uppercase;letter-spacing:0.06em;border-bottom:2px solid #E2E8F0">Monto Total</th>
              <th style="padding:10px 16px;text-align:right;color:#64748B;font-size:0.76em;
                         text-transform:uppercase;letter-spacing:0.06em;border-bottom:2px solid #E2E8F0">Prom. Días Atraso</th>
              <th style="padding:10px 16px;text-align:center;color:#64748B;font-size:0.76em;
                         text-transform:uppercase;letter-spacing:0.06em;border-bottom:2px solid #E2E8F0">Nivel de Riesgo</th>
            </tr>
          </thead><tbody>"""
        for bucket, df_ag, nivel, bg, fg, dot in aging_cfg:
            avg_dias = int(df_ag['dias_atraso'].mean()) if not df_ag.empty else 0
            badge_html = _dot_badge(nivel, bg, fg, dot)
            aging_html += (
                f'<tr style="border-bottom:1px solid #F1F5F9">'
                f'<td style="padding:10px 16px;font-weight:600;color:#1E293B">{bucket}</td>'
                f'<td style="padding:10px 16px;text-align:right;color:#0B1D4E;font-weight:700">{len(df_ag)}</td>'
                f'<td style="padding:10px 16px;text-align:right;color:#0B1D4E;font-weight:700">${df_ag["cuota"].sum():,.2f}</td>'
                f'<td style="padding:10px 16px;text-align:right;color:#64748B">{avg_dias} días</td>'
                f'<td style="padding:10px 16px;text-align:center">{badge_html}</td>'
                f'</tr>')
        aging_html += "</tbody></table>"
        st.markdown(aging_html, unsafe_allow_html=True)
    else:
        st.success("✅ No hay cuotas vencidas en la cartera.")

    st.divider()

    # ── Panel por Crédito ─────────────────────────────
    tab_cob_corp, tab_cob_auto, tab_gest = st.tabs(
        ["Cartera Corporativa", "Cartera Automotriz", "Historial de Gestiones"])

    def _panel_cobranza(df_credits, tipo_exp, tipo_label):
        if df_credits.empty:
            st.info(f"No hay créditos {tipo_label} activos.")
            return
        df_pag = paginate_dataframe(df_credits, page_size=10, key_prefix=f"cob_{tipo_exp}")
        for _, cr in df_pag.iterrows():
            if not df_plan.empty:
                df_cuotas = df_plan[(df_plan['expediente_id'] == cr['id']) &
                                    (df_plan['tipo_expediente'] == tipo_exp)]
            else:
                df_cuotas = pd.DataFrame()
            
            cuotas_venc  = df_cuotas[(df_cuotas['estado'] == 'PENDIENTE') & (df_cuotas['fecha_pago'] < hoy_s)] if not df_cuotas.empty else pd.DataFrame()
            cuotas_prox  = df_cuotas[(df_cuotas['estado'] == 'PENDIENTE') & (df_cuotas['fecha_pago'] >= hoy_s)] if not df_cuotas.empty else pd.DataFrame()
            cuotas_pag   = df_cuotas[df_cuotas['estado'] == 'PAGADO'] if not df_cuotas.empty else pd.DataFrame()
            saldo_rest   = df_cuotas[df_cuotas['estado'] == 'PENDIENTE']['saldo'].min() if not df_cuotas.empty and not df_cuotas[df_cuotas['estado'] == 'PENDIENTE'].empty else 0.0
            estado_cob   = cr.get('estado_cobranza', 'Al día')
            if pd.isna(estado_cob) or not estado_cob:
                estado_cob = 'Al día'
                
            ESTADOS_COB  = {'Al día': ('#DCFCE7','#166534',''),
                            'Preventivo': ('#FEF9C3','#854D0E',''),
                            'Administrativo': ('#FFEDD5','#9A3412',''),
                            'Legal': ('#FEE2E2','#991B1B','')}
            bg_e, fg_e, ic_e = ESTADOS_COB.get(estado_cob, ('#F1F5F9','#475569','•'))
            label_cob = f"{ic_e} {estado_cob}"

            with st.expander(f"{cr['cliente'].upper()} — ${cr['monto']:,.0f} {cr.get('moneda', 'USD')}  ({label_cob})", expanded=len(cuotas_venc) > 0):
                col_i1, col_i2, col_i3, col_i4 = st.columns(4)
                col_i1.metric("Cuotas Vencidas", len(cuotas_venc),)
                col_i2.metric("Cuotas Pendientes", len(cuotas_prox))
                col_i3.metric("Cuotas Pagadas", len(cuotas_pag))
                col_i4.metric("Saldo Restante", f"${saldo_rest:,.2f}")

                # Covenants
                covenants_txt = cr.get('covenants', '')
                if pd.notna(covenants_txt) and str(covenants_txt).strip():
                    st.markdown(
                        f'<div style="background:#a9c1d3;border-left:4px solid #1E3A8A;'
                        f'border-radius:0 8px 8px 0;padding:10px 14px;margin:8px 0;font-size:0.86em">'
                        f'<strong style="color:#1E3A8A">📌 Covenants / Compromisos Financieros:</strong>'
                        f'<br><span style="color:#1E293B">{covenants_txt}</span></div>',
                        unsafe_allow_html=True)

                st_cob1, st_cob2, st_cob3 = st.tabs(["Cuotas", "Registrar Pago", "Nueva Gestión"])

                with st_cob1:
                    if df_cuotas.empty:
                        st.info("Sin plan de amortización generado.")
                    else:
                        cols_sh = ['periodo','fecha_pago','cuota','capital','interes','saldo','estado']
                        df_show = df_cuotas[[c for c in cols_sh if c in df_cuotas.columns]].copy()
                        df_show.columns = ['N°','Fecha','Cuota','Capital','Interés','Saldo','Estado']
                        st.dataframe(
                            df_show.style.format({'Cuota':'${:,.2f}','Capital':'${:,.2f}','Interés':'${:,.2f}','Saldo':'${:,.2f}'}),
                            use_container_width=True, hide_index=True)

                with st_cob2:
                    if df_cuotas.empty:
                        st.info("No hay cuotas.")
                    else:
                        pend_cuotas = df_cuotas[df_cuotas['estado'] == 'PENDIENTE'].sort_values('periodo')
                        if pend_cuotas.empty:
                            st.success("¡Todas las cuotas están pagadas!")
                        else:
                            opts = [f"Cuota {int(row['periodo'])} — {row['fecha_pago']} — ${row['cuota']:,.2f}"
                                    for _, row in pend_cuotas.iterrows()]
                            ids  = pend_cuotas['id'].tolist()
                            cuotas_list = pend_cuotas.to_dict('records')
                            sel_cuota = st.selectbox("Seleccionar cuota a registrar como pagada",
                                                      opts, key=f"sel_{tipo_exp}_{cr['id']}")
                            sel_idx = opts.index(sel_cuota)
                            fecha_pago_real = st.date_input("Fecha de recepción del pago",
                                                             value=hoy, key=f"fpag_{tipo_exp}_{cr['id']}")
                            referencia_pago = st.text_input("Referencia / N° de transferencia",
                                                             key=f"ref_{tipo_exp}_{cr['id']}")
                            if st.button("💾 Registrar Amortización", key=f"mpag_{tipo_exp}_{cr['id']}"):
                                monto_cuota = cuotas_list[sel_idx]['cuota']
                                PlanPagoDAO.mark_as_paid(ids[sel_idx])
                                PagoRecibidoDAO.create(
                                    cr['id'], tipo_exp, fecha_pago_real.strftime("%Y-%m-%d"),
                                    monto_cuota, referencia_pago
                                )
                                remaining_venc = df_cuotas[(df_cuotas['estado']=='PENDIENTE') &
                                                            (df_cuotas['fecha_pago'] < hoy_s) &
                                                            (df_cuotas['id'] != ids[sel_idx])]
                                new_ec = 'Al día' if remaining_venc.empty else estado_cob
                                if tipo_exp == 'corp':
                                    ExpedienteCorporativoDAO.update_estado_cobranza(cr['id'], new_ec)
                                else:
                                    ExpedienteAutomotrizDAO.update_estado_cobranza(cr['id'], new_ec)
                                st.success("Amortización registrada."); st.rerun()

                with st_cob3:
                    with st.form(f"gest_{tipo_exp}_{cr['id']}"):
                        gc1, gc2 = st.columns(2)
                        tipo_g = gc1.selectbox("Tipo de gestión",
                            ["Llamada telefónica", "WhatsApp/Mensaje", "Visita presencial",
                             "Carta formal", "Email", "Acuerdo de pago", "Entrega a Legal"])
                        resultado_g = gc2.selectbox("Resultado",
                            ["Sin respuesta", "Compromiso de pago", "Pago parcial recibido",
                             "Pago total recibido", "No localizado", "Rechazó pago", "En proceso legal"])
                        obs_g = st.text_area("Observaciones / Notas", key=f"obs_g_{tipo_exp}_{cr['id']}")
                        gc3, gc4 = st.columns(2)
                        prox_acc = gc3.text_input("Próxima acción")
                        fecha_prox = gc4.date_input("Fecha próxima acción", value=hoy + timedelta(days=7))
                        
                        idx_est = ["Al día","Preventivo","Administrativo","Legal"].index(estado_cob) if estado_cob in ["Al día","Preventivo","Administrativo","Legal"] else 0
                        new_estado_g = gc1.selectbox("Actualizar estado de cobranza",
                            ["Al día", "Preventivo", "Administrativo", "Legal"], index=idx_est)
                        
                        if st.form_submit_button("Guardar Gestión"):
                            GestionCobranzaDAO.create(
                                cr['id'], tipo_exp, hoy_s, tipo_g,
                                st.session_state.get('current_user', 'Admin'), resultado_g,
                                prox_acc, fecha_prox.strftime("%Y-%m-%d"), obs_g
                            )
                            if tipo_exp == 'corp':
                                ExpedienteCorporativoDAO.update_estado_cobranza(cr['id'], new_estado_g)
                            else:
                                ExpedienteAutomotrizDAO.update_estado_cobranza(cr['id'], new_estado_g)
                            st.success("Gestión registrada."); st.rerun()

    with tab_cob_corp:
        _panel_cobranza(df_corp_ap2, 'corp', 'corporativos')

    with tab_cob_auto:
        _panel_cobranza(df_auto_ap2, 'auto', 'automotrices')

    with tab_gest:
        st.markdown(f"### {APP_ICONS['reloj']} Historial Completo de Gestiones", unsafe_allow_html=True)
        if df_gest.empty:
            st.info("No hay gestiones registradas.")
        else:
            fg1, fg2, fg3 = st.columns(3)
            fil_tipo = fg1.selectbox("Filtrar por tipo", ["Todos"] + df_gest['tipo_expediente'].unique().tolist(), key="fg_tipo")
            fil_res  = fg2.selectbox("Filtrar por resultado", ["Todos"] + df_gest['resultado'].unique().tolist(), key="fg_res")
            fil_resp = fg3.selectbox("Filtrar por responsable", ["Todos"] + df_gest['responsable'].unique().tolist(), key="fg_resp")
            df_gf = df_gest.copy()
            if fil_tipo != "Todos": df_gf = df_gf[df_gf['tipo_expediente'] == fil_tipo]
            if fil_res  != "Todos": df_gf = df_gf[df_gf['resultado'] == fil_res]
            if fil_resp != "Todos": df_gf = df_gf[df_gf['responsable'] == fil_resp]
            
            show_cols = ['fecha', 'expediente_id', 'tipo_expediente', 'tipo_gestion',
                         'responsable', 'resultado', 'proxima_accion', 'fecha_proxima', 'obs']
            rename_map = {'fecha':'Fecha','expediente_id':'ID Exp.','tipo_expediente':'Tipo',
                          'tipo_gestion':'Gestión','responsable':'Responsable',
                          'resultado':'Resultado','proxima_accion':'Próx. Acción',
                          'fecha_proxima':'Fecha Próx.','obs':'Observaciones'}
            df_gf_pag = paginate_dataframe(df_gf, page_size=15, key_prefix="gestiones")
            st.dataframe(df_gf_pag[[c for c in show_cols if c in df_gf_pag.columns]].rename(columns=rename_map),
                         use_container_width=True, hide_index=True)
