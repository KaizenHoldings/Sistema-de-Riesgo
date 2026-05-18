import streamlit as st
import time
from services.auth_service import AuthService
from database.db_core_sqlserver import init_db
from database.daos_sqlserver import ExpedienteCorporativoDAO, ExpedienteAutomotrizDAO, PlanPagoDAO
from utils import inyectar_css_kfg, get_base64_image
from datetime import datetime
from PIL import Image

img = Image.open("./public/imgs/logoKH.png")

# 1. Configuración Global
st.set_page_config(page_title="KFG Risk Architect", layout="wide", page_icon=img)
inyectar_css_kfg()

if "kfg_session" in st.query_params:
    del st.query_params["kfg_session"]

# 2. Inicialización de la Base de Datos
init_db()

# 3. Importación de la vista de login (AuthView)
from views import auth_view

# 4. Lógica de Enrutamiento (Routing)
AuthService.try_restore_session()

if not AuthService.is_authenticated():
    auth_view.show()
else:
    role = AuthService.get_current_role()
    
    # Inyectar cookie nativa si acabamos de iniciar sesión
    if 'login_token' in st.session_state:
        token = st.session_state.pop('login_token')
        import streamlit.components.v1 as components
        js = f"""
        <script>
            window.parent.document.cookie = "kfg_auth={token}; path=/; max-age=604800";
        </script>
        """
        components.html(js, height=0)
        
    # (Modal de solicitud antiguo eliminado, ahora es una vista completa)

    # ── Contadores Optimizados (Caché de 30s) ──
    @st.cache_data(ttl=30)
    def get_sidebar_metrics():


        # Cumplimiento: dictamen PENDIENTE y status_comp 0
        n_comp = ExpedienteCorporativoDAO.count(dictamen='PENDIENTE', status_comp=0) + \
                 ExpedienteAutomotrizDAO.count(dictamen='PENDIENTE', status_comp=0)
        
        # Legal: dictamen PENDIENTE y status_leg 0
        n_leg = ExpedienteCorporativoDAO.count(dictamen='PENDIENTE', status_leg=0) + \
                ExpedienteAutomotrizDAO.count(dictamen='PENDIENTE', status_leg=0)
        
        # Riesgo: dictamen PENDIENTE y status_riesgo 0
        n_ries = ExpedienteCorporativoDAO.count(dictamen='PENDIENTE', status_riesgo=0) + \
                 ExpedienteAutomotrizDAO.count(dictamen='PENDIENTE', status_riesgo=0)
        
        # Comité: dictamen PENDIENTE y todos los status aprobados (1)
        n_comite = ExpedienteCorporativoDAO.count(dictamen='PENDIENTE', status_comp=1, status_leg=1, status_riesgo=1) + \
                   ExpedienteAutomotrizDAO.count(dictamen='PENDIENTE', status_comp=1, status_leg=1, status_riesgo=1)
        
        # Cobranzas: Plan de pagos PENDIENTE con fecha vencida
        hoy_str = datetime.now().strftime("%Y-%m-%d")
        n_venc = PlanPagoDAO.count_vencidos(hoy_str)
        
        return n_comp, n_leg, n_ries, n_comite, n_venc
    
    with st.spinner("Sincronizando indicadores..."):
        n_comp, n_leg, n_ries, n_comite, n_venc = get_sidebar_metrics()
    
    def cnt(n): return f" **{n}**" if n > 0 else ""

    # ── Vistas a registrar (Lazy Loading) ──
    def show_dashboard(): from views import dashboard; dashboard.show()
    def show_compliance(): from views import compliance; compliance.show()
    def show_legal(): from views import legal; legal.show()
    def show_risk(): from views import risk; risk.show()
    def show_evaluations(): from views import evaluations; evaluations.show()
    def show_portfolio(): from views import portfolio; portfolio.show()
    def show_collections(): from views import collections; collections.show()
    def show_onboarding(): from views import onboarding; onboarding.show()
    def show_parameters(): from views import admin; admin.show()
    def show_users(): from views import users; users.show()
    def show_profile(): from views import profile; profile.show()
    def show_new_request(): from views import new_request; new_request.show()

    # Mapeo a las páginas originales exactas con sus contadores dinámicos
    p_inicio = st.Page(show_dashboard, title="Inicio", default=True)
    p_comp = st.Page(show_compliance, title=f"Cumplimiento{cnt(n_comp)}")
    p_leg = st.Page(show_legal, title=f"Legal{cnt(n_leg)}")
    p_riesgo = st.Page(show_risk, title=f"Riesgo{cnt(n_ries)}")
    p_comite = st.Page(show_evaluations, title=f"Comité & BI{cnt(n_comite)}")
    p_cobranza = st.Page(show_collections, title=f"Cobranzas{cnt(n_venc)}")
    p_cartera = st.Page(show_portfolio, title="Cartera")
    p_clientes = st.Page(show_onboarding, title="Clientes")
    p_parametros = st.Page(show_parameters, title="Parámetros")
    p_usuarios = st.Page(show_users, title="Usuarios")
    p_perfil = st.Page(show_profile, title="Mi Perfil")
    p_nueva_solicitud = st.Page(show_new_request, title="Nueva Solicitud")

    # Recrear el diccionario exacto del monolito
    pages = {}
    if role == 'Compliance':
        pages["Secciones"] = [p_inicio, p_comp, p_clientes, p_perfil]
    elif role == 'Legal':
        pages["Secciones"] = [p_inicio, p_leg, p_clientes, p_perfil]
    elif role == 'Riesgo':
        pages["Secciones"] = [p_inicio, p_riesgo, p_clientes, p_perfil]
    elif role == 'Comité':
        pages["Secciones"] = [p_inicio, p_comite, p_cartera, p_clientes, p_perfil]
    elif role == 'Cobranzas':
        pages["Secciones"] = [p_inicio, p_cobranza, p_perfil]
    elif role == 'Superadmin':
        # Agrupado para que se vea más limpio, con las exactas 11 opciones
        pages["Evaluación"] = [p_inicio, p_comp, p_leg, p_riesgo, p_comite]
        pages["Gestión"] = [p_cobranza, p_cartera, p_clientes]
        pages["Configuración"] = [p_parametros, p_usuarios, p_perfil]
    else:
        pages["Secciones"] = [p_inicio, p_clientes, p_perfil]
    
    # Agregar página de Nueva Solicitud a una sección interna para que switch_page funcione
    # pero no se renderice doble en el bucle manual
    pages["_internas"] = [p_nueva_solicitud]

    # Enrutador Nativo de Streamlit oculto (para nosotros dibujar el menú manualmente)
    pg = st.navigation(pages, position="hidden")
    
    # ── Renderizado Manual del Sidebar ──
    logo_base64 = get_base64_image("./public/imgs/logoKH.png")
    with st.sidebar:
        # 1. Info del Usuario
        st.markdown(f"""
        <div style="text-align:center; margin-bottom:10px;">
            <div style="width:54px;height:54px;background:rgba(255,255,255,0.1);
                        border-radius:14px;display:inline-flex;align-items:center;
                        justify-content:center;margin-bottom:12px;box-shadow:0 4px 10px rgba(0,0,0,0.15)">
                <img src="{logo_base64}" alt="KFG" width="32" height="32" style="object-fit:contain;">
            </div>
            <div style="color:white;font-weight:700;font-size:1.05em;letter-spacing:0.5px;">{st.session_state.get('current_user')}</div>
            <div style="color:#CBD5E1;font-size:0.85em;margin-top:2px;">Rol: {role}</div>
        </div>
        """, unsafe_allow_html=True)

        # 2. Botón de Agregar Nueva Solicitud (ARRIBA de las rutas)
        st.markdown('<span class="btn-solicitud-hook" style="display:none;"></span>', unsafe_allow_html=True)
        if st.button("Agregar Nueva Solicitud", width='stretch'):
            st.switch_page(p_nueva_solicitud)
            
        st.markdown("<hr style='border-color:rgba(255,255,255,0.15); margin:12px 0;'>", unsafe_allow_html=True)

        # 3. Enlaces de Rutas
        for section_name, page_list in pages.items():
            if section_name == "_internas":
                continue
            if section_name != "Secciones":
                st.markdown(f"<p style='color:#CBD5E1; font-weight:700; font-size:0.85em; margin-top:10px; margin-bottom:5px; text-transform:uppercase;'>{section_name}</p>", unsafe_allow_html=True)
            for page in page_list:
                if page.icon:
                    st.page_link(page, label=page.title, icon=page.icon)
                else:
                    st.page_link(page, label=page.title)
                
        st.markdown("<hr style='border-color:rgba(255,255,255,0.15); margin:12px 0;'>", unsafe_allow_html=True)
        
        # 4. Cerrar Sesión
        def handle_logout():
            for key in ['auth', 'current_user', 'role', '_default_page']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state['logout_token'] = True
            
        st.button("🚪 Cerrar Sesión", width='stretch', on_click=handle_logout)
        st.markdown("<br><div style='color:#94A3B8;font-size:0.75em;text-align:center'>Kaizen apps<br>Multipage Architecture</div>", unsafe_allow_html=True)
    
    pg.run()
