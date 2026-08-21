import streamlit as st
from datetime import datetime
from database.daos_sqlserver import ExpedienteCorporativoDAO, ExpedienteAutomotrizDAO, PlanPagoDAO

@st.cache_data(ttl=60)
def get_sidebar_metrics():
    """
    Obtiene las métricas para los contadores de notificaciones del sidebar.
    Los resultados se almacenan en caché para evitar sobrecargar la base de datos,
    pero la caché se limpia de forma manual al crear expedientes o actualizar dictámenes.
    """
    # Cada bandeja cuenta las solicitudes nuevas (PENDIENTE) y las devueltas a
    # esa etapa para corrección (REVISIÓN-{etapa}).
    D_COMP = ['PENDIENTE', 'REVISIÓN-Cumplimiento']
    D_LEG = ['PENDIENTE', 'REVISIÓN-Legal']
    D_RIES = ['PENDIENTE', 'REVISIÓN-Riesgo']
    D_COMITE = ['PENDIENTE', 'REVISIÓN-Comité']

    # Cumplimiento: pendiente o devuelto a Cumplimiento, con status_comp 0
    n_comp = ExpedienteCorporativoDAO.count(dictamen=D_COMP, status_comp=0) + \
             ExpedienteAutomotrizDAO.count(dictamen=D_COMP, status_comp=0)

    # Legal: pendiente o devuelto a Legal, con status_leg 0 y Cumplimiento certificado
    n_leg = ExpedienteCorporativoDAO.count(dictamen=D_LEG, status_comp=1, status_leg=0) + \
            ExpedienteAutomotrizDAO.count(dictamen=D_LEG, status_comp=1, status_leg=0)

    # Riesgo: pendiente o devuelto a Riesgo, con status_riesgo 0 y Cumplimiento certificado
    n_ries = ExpedienteCorporativoDAO.count(dictamen=D_RIES, status_comp=1, status_riesgo=0) + \
             ExpedienteAutomotrizDAO.count(dictamen=D_RIES, status_comp=1, status_riesgo=0)

    # Comité: pendiente o devuelto al Comité, con las tres firmas registradas
    n_comite = ExpedienteCorporativoDAO.count(dictamen=D_COMITE, status_comp=1, status_leg=1, status_riesgo=1) + \
               ExpedienteAutomotrizDAO.count(dictamen=D_COMITE, status_comp=1, status_leg=1, status_riesgo=1)
    
    # Cobranzas: Plan de pagos PENDIENTE con fecha vencida
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    n_venc = PlanPagoDAO.count_vencidos(hoy_str)
    
    return n_comp, n_leg, n_ries, n_comite, n_venc
