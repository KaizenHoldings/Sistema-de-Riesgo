import time
from datetime import datetime
from functools import lru_cache

from database.daos_sqlserver import ExpedienteCorporativoDAO, ExpedienteAutomotrizDAO, PlanPagoDAO

# Ventana de validez de la caché, en segundos. Reproduce el `ttl=60` que aportaba
# `@st.cache_data` sin depender de Streamlit: la clave del `lru_cache` es el cubo
# temporal, de modo que al cambiar de ventana el valor se recalcula solo.
TTL_SEGUNDOS = 60


@lru_cache(maxsize=1)
def _calcular_metricas(_ventana):
    """
    Cálculo real de los contadores del sidebar.

    `_ventana` no se usa dentro: es la clave que caduca la caché cada
    `TTL_SEGUNDOS`.
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


def get_sidebar_metrics():
    """
    Contadores de notificaciones de la barra lateral.

    Devuelve `(n_comp, n_leg, n_ries, n_comite, n_venc)`. El resultado se cachea
    durante `TTL_SEGUNDOS` para no golpear la base en cada rerun; las vistas
    fuerzan el recálculo con `get_sidebar_metrics.clear()` tras cada escritura,
    exactamente igual que antes.
    """
    return _calcular_metricas(int(time.time() // TTL_SEGUNDOS))


# Se conserva la firma que exponía Streamlit para no tener que tocar las vistas
get_sidebar_metrics.clear = _calcular_metricas.cache_clear
get_sidebar_metrics.cache_clear = _calcular_metricas.cache_clear
