import streamlit as st
import pandas as pd
import json
from datetime import datetime, date, timedelta
from utils import page_header, section_divider, paginate_dataframe, APP_ICONS
from database.daos_sqlserver import ExpedienteCorporativoDAO, ExpedienteAutomotrizDAO

@st.dialog("Confirmar Revisión Legal")
def modal_firmar_legal(r, tipo, data):
    st.markdown(f"### ¿Confirmar revisión legal para **{r['cliente']}**?")
    st.write("Se registrarán los colaterales y la validación de documentación para este expediente.")
    
    if st.button("Confirmar Firma Legal", type="primary", use_container_width=True):
        with st.spinner("Registrando colaterales y validación legal..."):
            if tipo == 'corp':
                ExpedienteCorporativoDAO.update_legal(
                    exp_id=r['id'],
                    garantias_json=data['garantias_json'],
                    v_garantia=data['v_garantia'],
                    ltv_ratio=data['ltv_ratio'],
                    fecha_vencimiento_garantia=data['fecha_vencimiento_garantia'],
                    custodia_fisica=data['custodia_fisica'],
                    obs_leg=data['obs_leg']
                )
            else:
                ExpedienteAutomotrizDAO.update_legal(
                    exp_id=r['id'],
                    marca=data['marca'],
                    modelo=data['modelo'],
                    anio=data['anio'],
                    vin=data['vin'],
                    precio_vehiculo=data['precio_vehiculo'],
                    tipo_vehiculo=data['tipo_vehiculo'],
                    enganche=data['enganche'],
                    plazo_meses=data['plazo_meses'],
                    ltv_ratio=data['ltv_ratio'],
                    seguro_vehiculo=data['seguro_vehiculo'],
                    registro_lien=data['registro_lien'],
                    fecha_vencimiento_seguro=data['fecha_vencimiento_seguro'],
                    obs_leg=data['obs_leg'],
                    vehiculo_placa=data['vehiculo_placa'],
                    seguro_empresa=data['seguro_empresa'],
                    seguro_poliza=data['seguro_poliza'],
                    seguro_vigencia=data['seguro_vigencia']
                )
            st.success("✅ Revisión Legal registrada.")
            st.rerun()

def show():
    page_header("legal", "Legal & Gestión de Colateral",
                "Gestión de garantías y revisión de documentación legal",
                "KFG Risk Architect · Legal")
                
    with st.spinner("Cargando expedientes y garantías..."):
        df_corp = ExpedienteCorporativoDAO.get_all_as_df()
        df_auto = ExpedienteAutomotrizDAO.get_all_as_df()

    tab_corp, tab_auto = st.tabs(["Créditos Corporativos", "Créditos Automotrices"])

    with tab_corp:
        if not df_corp.empty:
            df_l = df_corp[(df_corp['status_leg'] == 0) & (df_corp['dictamen'] == 'PENDIENTE')]
        else:
            df_l = pd.DataFrame()

        if df_l.empty:
            st.info("No hay expedientes corporativos pendientes en Legal.")
        else:
            df_l_pag = paginate_dataframe(df_l, page_size=10, key_prefix="leg_corp")
            for _, r in df_l_pag.iterrows():
                with st.expander(f"{r['cliente'].upper()} | RIF: {r['rif'].upper()} | ${r['monto']:,.2f}"):
                    st.markdown(f"#### {APP_ICONS['corporativo']} Revisión de Documentación Legal", unsafe_allow_html=True)
                    if f"g_list_{r['id']}" not in st.session_state:
                        try: 
                            st.session_state[f"g_list_{r['id']}"] = json.loads(r['garantias_json']) if pd.notna(r['garantias_json']) and r['garantias_json'] else []
                        except Exception: 
                            st.session_state[f"g_list_{r['id']}"] = []

                    c1, c2, c3 = st.columns([2, 3, 2])
                    tg = c1.selectbox("Tipo", ["Hipoteca", "Prenda", "Fianza", "Pagaré", "Póliza"], key=f"l_tg_{r['id']}")
                    dg = c2.text_input("Descripción", key=f"l_dg_{r['id']}")
                    vg = c3.number_input("Valor", min_value=0.0, key=f"l_vg_{r['id']}")
                    if st.button("➕ Añadir Colateral", key=f"l_add_{r['id']}"):
                        st.session_state[f"g_list_{r['id']}"].append({"tipo": tg, "desc": dg, "valor": vg})
                        st.rerun()

                    if st.session_state[f"g_list_{r['id']}"]:
                        st.table(pd.DataFrame(st.session_state[f"g_list_{r['id']}"]))
                        v_tot = sum(x['valor'] for x in st.session_state[f"g_list_{r['id']}"])
                        ltv = (v_tot / r['monto'] * 100) if r['monto'] > 0 else 0
                        
                        c_date, c_cust = st.columns(2)
                        fv = c_date.date_input("Vencimiento Garantía Principal", key=f"l_fv_{r['id']}")
                        if fv < date.today() + timedelta(days=90):
                            c_date.error("⚠️ Alerta: La garantía vence en menos de 90 días.")
                        cust = c_cust.checkbox("Custodia Física Confirmada", key=f"l_cust_{r['id']}")
                        obs_l = st.text_area("Observaciones Legales", key=f"l_obs_{r['id']}")
                        
                        if st.button("Firmar Legal", key=f"l_f_{r['id']}"):
                            data_l = {
                                'garantias_json': json.dumps(st.session_state[f"g_list_{r['id']}"]),
                                'v_garantia': v_tot,
                                'ltv_ratio': ltv,
                                'fecha_vencimiento_garantia': fv.strftime("%Y-%m-%d"),
                                'custodia_fisica': cust,
                                'obs_leg': obs_l
                            }
                            modal_firmar_legal(r, 'corp', data_l)

    with tab_auto:
        if not df_auto.empty:
            df_la = df_auto[(df_auto['status_leg'] == 0) & (df_auto['dictamen'] == 'PENDIENTE')]
        else:
            df_la = pd.DataFrame()

        if df_la.empty:
            st.info("No hay expedientes automotrices pendientes en Legal.")
        else:
            df_la_pag = paginate_dataframe(df_la, page_size=10, key_prefix="leg_auto")
            for _, r in df_la_pag.iterrows():
                with st.expander(f"🚗 {r['cliente']} | {r['marca']} {r['modelo']} | ${r['monto']:,.2f}"):
                    st.markdown(f"#### {APP_ICONS['automotriz']} Análisis de Garantía Automotriz", unsafe_allow_html=True)
                    st.markdown("**Datos del Vehículo:**")
                    v1, v2, v3 = st.columns(3)
                    marca = v1.text_input("Marca", value=str(r['marca'] if pd.notna(r['marca']) else ''), key=f"la_marca_{r['id']}")
                    modelo_v = v2.text_input("Modelo", value=str(r['modelo'] if pd.notna(r['modelo']) else ''), key=f"la_mod_{r['id']}")
                    anio_actual = datetime.now().year
                    anio_val = int(r['anio']) if pd.notna(r['anio']) and r['anio'] else anio_actual
                    anio_v = v3.number_input("Año", value=anio_val, min_value=1990, max_value=anio_actual + 1, key=f"la_anio_{r['id']}")
                    
                    v4, v5, v6 = st.columns(3)
                    vin_v = v4.text_input("VIN / Serial", value=str(r['vin'] if pd.notna(r['vin']) else ''), key=f"la_vin_{r['id']}")
                    precio_v = v5.number_input("Precio del Vehículo", value=float(r['precio_vehiculo'] if pd.notna(r['precio_vehiculo']) else 0.0), min_value=0.0, key=f"la_precio_{r['id']}")
                    tipo_v = v6.selectbox("Tipo", ["Nuevo", "Usado"], key=f"la_tipo_{r['id']}")

                    eng_col, plazo_col = st.columns(2)
                    enganche_v = eng_col.number_input("Enganche / Inicial", value=float(r['enganche'] if pd.notna(r['enganche']) else 0.0), min_value=0.0, key=f"la_eng_{r['id']}")
                    plazos_disponibles = [12, 24, 36, 48, 60, 72]
                    
                    val_plazo = int(r['plazo_meses']) if pd.notna(r['plazo_meses']) and r['plazo_meses'] else 36
                    plazo_idx = plazos_disponibles.index(val_plazo) if val_plazo in plazos_disponibles else 3
                    plazo_v = plazo_col.selectbox("Plazo (meses)", plazos_disponibles, index=plazo_idx, key=f"la_plazo_{r['id']}")

                    monto_financiar = r['monto'] if r['monto'] > 0 else max(precio_v - enganche_v, 0)
                    ltv_auto = (monto_financiar / precio_v * 100) if precio_v > 0 else 0

                    ltv_col, _ = st.columns([1, 2])
                    ltv_col.metric("LTV del Vehículo", f"{ltv_auto:.2f}%", help="Monto Financiado / Precio del Vehículo")
                    if ltv_auto > 80:
                        st.warning("⚠️ LTV superior al 80%. Considere solicitar mayor enganche.")

                    st.markdown("**Placa del Vehículo:**")
                    placa_v = st.text_input("Placa", value=str(r.get('vehiculo_placa', '') if pd.notna(r.get('vehiculo_placa')) else ''), key=f"la_placa_{r['id']}")

                    st.markdown("**Datos de la Póliza de Seguro:**")
                    sp1, sp2, sp3 = st.columns(3)
                    seg_emp = sp1.text_input("Empresa Aseguradora", value=str(r.get('seguro_empresa', '') if pd.notna(r.get('seguro_empresa')) else ''), key=f"la_segemp_{r['id']}")
                    seg_pol = sp2.text_input("N° de Póliza", value=str(r.get('seguro_poliza', '') if pd.notna(r.get('seguro_poliza')) else ''), key=f"la_segpol_{r['id']}")
                    fv_seg = st.date_input("Fecha de Vencimiento del Seguro", key=f"la_fvseg_{r['id']}")
                    if fv_seg < date.today() + timedelta(days=30):
                        st.error("⚠️ El seguro vence en menos de 30 días. Requiere renovación.")

                    st.markdown("**Verificaciones Legales Obligatorias:**")
                    l1, l2, l3 = st.columns(3)
                    seg_v = l1.checkbox("✅ Seguro del Vehículo Confirmado", key=f"la_seg_{r['id']}")
                    lien_v = l2.checkbox("✅ Reserva de Dominio Constituida", key=f"la_lien_{r['id']}")
                    transito_v = l3.checkbox("✅ Revisión de Tránsito (P51)", key=f"la_transit_{r['id']}")

                    obs_la = st.text_area("Observaciones Legales", key=f"la_obs_{r['id']}")
                    all_legal_ok = seg_v and lien_v and transito_v
                    
                    if st.button("Firmar Legal", key=f"la_f_{r['id']}", disabled=not all_legal_ok):
                        data_la = {
                            'marca': marca, 'modelo': modelo_v, 'anio': anio_v,
                            'vin': vin_v, 'precio_vehiculo': precio_v, 'tipo_vehiculo': tipo_v,
                            'enganche': enganche_v, 'plazo_meses': plazo_v, 'ltv_ratio': ltv_auto,
                            'seguro_vehiculo': seg_v, 'registro_lien': lien_v,
                            'fecha_vencimiento_seguro': fv_seg.strftime("%Y-%m-%d"),
                            'obs_leg': obs_la, 'vehiculo_placa': placa_v,
                            'seguro_empresa': seg_emp, 'seguro_poliza': seg_pol,
                            'seguro_vigencia': fv_seg.strftime("%Y-%m-%d")
                        }
                        modal_firmar_legal(r, 'auto', data_la)
                        
                    if not all_legal_ok:
                        st.caption("⚠️ Debe confirmar el seguro, la Reserva de Dominio y la Revisión de Tránsito (P51) para firmar.")
