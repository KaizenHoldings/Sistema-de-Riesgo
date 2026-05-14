import streamlit as st
from services.auth_service import AuthService
from utils import inyectar_css_kfg, get_base64_image

def show():
    # El CSS ya está inyectado globalmente en route.py, pero si se necesitara:
    # inyectar_css_kfg()
    
    logo_base64 = get_base64_image("./public/imgs/logoKH.png")
    
    st.markdown("""
    <style>
        [data-testid="collapsedControl"] { display: none !important; }
        [data-testid="stSidebar"] { display: none !important; }
    </style>
    <div style="position:fixed;top:0;left:0;right:0;bottom:0;
                background:#F0F2F5;z-index:-1"></div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)
    _, col_c, _ = st.columns([1, 1.1, 1])
    with col_c:
        st.markdown(f"""
        <div style="text-align:center;margin-bottom:28px">
            <div style="display:inline-flex;align-items:center;justify-content:center;
                        background:white;
                        width:64px;height:64px;border-radius:16px;margin-bottom:16px;
                        box-shadow:0 8px 24px rgba(11,29,78,0.15); border: 1px solid #E2E8F0">
                <img src="{logo_base64}" width="40" height="40" style="object-fit:contain">
            </div>
            <div style="color:#64748B;font-size:0.78em;font-weight:600;
                        letter-spacing:0.12em;text-transform:uppercase;margin-bottom:4px">
                Kaizen Financial Group
            </div>
            <div style="color:#0B1D4E;font-size:1.55em;font-weight:800;letter-spacing:-0.02em">
                KFG Risk Architect
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        def handle_login():
            u = st.session_state.get("user_input_login", "")
            p = st.session_state.get("pass_input_login", "")
            if AuthService.login(u, p):
                st.session_state['login_success_msg'] = True
            else:
                st.session_state['login_error_msg'] = True

        with st.form("login_form"):
            st.text_input("Usuario / Correo", placeholder="Ej. jperez@kz.finance", key="user_input_login")
            st.text_input("Contraseña", type="password", key="pass_input_login")
            st.form_submit_button("INICIAR SESIÓN", type="primary", on_click=handle_login, key="submit_button")

        if st.session_state.get('login_success_msg'):
            st.success("Sesión iniciada. Accediendo...")
            st.session_state['login_success_msg'] = False
            import time
            time.sleep(0.5)
            st.rerun()
                
        elif st.session_state.get('login_error_msg'):
            st.error("⚠️ Credenciales incorrectas. Intente nuevamente.")
            st.session_state['login_error_msg'] = False

    if st.session_state.get('logout_token'):
        import streamlit.components.v1 as components
        js = """
        <script>
            window.parent.document.cookie = "kfg_auth=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        </script>
        """
        components.html(js, height=0)
        st.session_state.pop('logout_token')
