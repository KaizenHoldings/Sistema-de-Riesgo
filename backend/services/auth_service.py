"""Puente de autenticación JWT para la interfaz Streamlit."""

import streamlit as st
from jwt import ExpiredSignatureError, InvalidTokenError

from api.security import create_access_token, decode_access_token
from database.daos_sqlserver import UsuarioDAO


class AuthService:

    @staticmethod
    def login(username, password):
        user = UsuarioDAO.get_by_credentials(username, password)
        if not user:
            return False

        token = create_access_token(user.user, user.role)
        st.session_state['auth'] = token
        st.session_state['current_user'] = user.user
        st.session_state['role'] = user.role
        st.session_state['login_token'] = token
        return True

    @staticmethod
    def logout():
        pass  # La eliminación de la cookie se maneja en route.py/AuthView.

    @staticmethod
    def _clear_session():
        for key in ('auth', 'current_user', 'role', 'login_token'):
            st.session_state.pop(key, None)

    @staticmethod
    def _restore_from_token(token):
        try:
            payload = decode_access_token(token)
        except (ExpiredSignatureError, InvalidTokenError, RuntimeError, TypeError):
            AuthService._clear_session()
            return False

        st.session_state['auth'] = token
        st.session_state['current_user'] = payload['user']
        st.session_state['role'] = payload['role']
        return True

    @staticmethod
    def try_restore_session():
        if st.session_state.get('logout_token', False):
            return False

        token = st.session_state.get('auth')
        if not isinstance(token, str):
            token = st.context.cookies.get("kfg_auth")
        return bool(token and AuthService._restore_from_token(token))

    @staticmethod
    def get_current_role():
        token = st.session_state.get('auth')
        if not isinstance(token, str) or not AuthService._restore_from_token(token):
            return None
        return st.session_state['role']

    @staticmethod
    def is_authenticated():
        return AuthService.get_current_role() is not None
