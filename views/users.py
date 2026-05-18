import streamlit as st
from utils import page_header
from database.daos_sqlserver import UsuarioDAO

def show():
    page_header("users", "Usuarios", "Gestión de roles y accesos", "KFG Risk Architect · Usuarios")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Usuarios Registrados")
        try:
            df_users = UsuarioDAO.get_all_as_df()
            st.dataframe(df_users, width='stretch', hide_index=True)
        except Exception as e:
            st.error(f"Error cargando usuarios: {e}")
            
    with col2:
        st.subheader("Gestión de Credenciales")
        with st.form("user_form"):
            un = st.text_input("Usuario (Correo)")
            up = st.text_input("Contraseña", type="password")
            ur = st.selectbox("Rol", ["Compliance", "Legal", "Riesgo", "Comité", "Cobranzas", "Superadmin"])
            submit = st.form_submit_button("Guardar Usuario")
            
            if submit:
                if un and up:
                    try:
                        UsuarioDAO.upsert(un, up, ur)
                        st.success(f"Usuario {un} guardado exitosamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar usuario: {e}")
                else:
                    st.error("Por favor, completa todos los campos.")
