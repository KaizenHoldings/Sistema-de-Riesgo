import streamlit as st
from database.daos_sqlserver import UsuarioDAO
import base64

class AuthService:

    @staticmethod
    def login(username, password):
        user = UsuarioDAO.get_by_credentials(username, password)
        if user:
            st.session_state['auth'] = True
            st.session_state['current_user'] = user.user
            st.session_state['role'] = user.role
            
            # Guardar token en memoria para que la UI lo inyecte
            token = base64.b64encode(f"{user.user}::{user.role}".encode()).decode()
            st.session_state['login_token'] = token
            return True
        return False
        
    @staticmethod
    def logout():
        pass # La lógica de logout real se maneja en route.py con JS

    @staticmethod
    def try_restore_session():
        if st.session_state.get('logout_token', False):
            return False
            
        # Solo intenta restaurar si no está autenticado
        if not st.session_state.get('auth', False):
            # API nativa de Streamlit para leer cookies de forma instantánea
            token = st.context.cookies.get("kfg_auth")
            if token:
                try:
                    decoded = base64.b64decode(token).decode()
                    user, role = decoded.split("::")
                    st.session_state['auth'] = True
                    st.session_state['current_user'] = user
                    st.session_state['role'] = role
                except Exception:
                    pass
        return st.session_state.get('auth', False)
    def get_current_role():
        return st.session_state.get('role', None)

    @staticmethod
    def is_authenticated():
        return st.session_state.get('auth', False)
