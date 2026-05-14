import streamlit as st
from utils import page_header
from database.daos_sqlserver import UsuarioDAO

def show():
    page_header("profile", "Mi Perfil", "Configuración de cuenta y credenciales de acceso", "KFG Risk Architect · Perfil")
    
    current_user = st.session_state.get('current_user', 'Usuario Desconocido')
    role = st.session_state.get('user_role', 'Sin Rol')
    
    st.write(f"Has iniciado sesión como: **{current_user}**")
    st.write(f"Rol asignado: **{role}**")
    
    with st.form("perfil_form"):
        new_pwd = st.text_input("Nueva Contraseña", type="password")
        new_pwd_c = st.text_input("Confirmar Nueva Contraseña", type="password")
        if st.form_submit_button("Actualizar Contraseña"):
            if new_pwd and new_pwd == new_pwd_c:
                UsuarioDAO.update_password(current_user, new_pwd)
                st.success("Contraseña actualizada exitosamente.")
            elif new_pwd != new_pwd_c:
                st.error("Las contraseñas no coinciden.")
            else:
                st.warning("Por favor ingresa una contraseña.")
