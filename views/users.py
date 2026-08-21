import streamlit as st
from utils import page_header, paginate_dataframe, APP_ICONS
from database.daos_sqlserver import UsuarioDAO

@st.dialog("Cambiar Contraseña")
def modal_change_password(usuario):
    st.markdown(f"### Actualizar contraseña para **{usuario}**")
    new_pwd = st.text_input("Nueva Contraseña", type="password", key=f"inp_pwd_{usuario}")
    if st.button("Actualizar Contraseña", type="primary", width='stretch'):
        if new_pwd:
            try:
                UsuarioDAO.update_password(usuario, new_pwd)
                st.success(f"Contraseña actualizada exitosamente.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al actualizar: {e}")
        else:
            st.error("Por favor, ingresa una nueva contraseña.")

@st.dialog("Agregar Nuevo Usuario")
def modal_add_user():
    st.markdown("### Gestión de Credenciales")
    un = st.text_input("Usuario (Correo)")
    up = st.text_input("Contraseña", type="password")
    ur = st.selectbox("Rol", ["Compliance", "Legal", "Riesgo", "Comité", "Cobranzas", "Superadmin"])
    if st.button("Guardar Usuario", type="primary", width="stretch"):
        if un and up:
            try:
                UsuarioDAO.upsert(un, up, ur)
                st.success(f"Usuario {un} guardado exitosamente.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar usuario: {e}")
        else:
            st.error("Por favor, completa todos los campos.")

def show():
    page_header("users", "Usuarios", "Gestión de roles y accesos", "KFG Risk Architect · Usuarios")
    
    try:
        df_users = UsuarioDAO.get_all_as_df()
    except Exception as e:
        df_users = None
        st.error(f"Error cargando usuarios: {e}")

    hdr1, hdr2 = st.columns([3, 1])
    with hdr1:
        st.subheader("Usuarios Registrados")
    with hdr2:
        st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
        if st.button("Agregar Nuevo Usuario", type="primary", use_container_width=True):
            modal_add_user()

    if df_users is not None and not df_users.empty:
        df_pag = paginate_dataframe(df_users, page_size=10, key_prefix="users_list")
        for _, row in df_pag.iterrows():
            with st.container(border=True):
                c_user, c_rol, c_btn = st.columns([2, 1, 1])
                icon_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path d="M0 0h24v24H0z" fill="none" /><path fill="#162e70" d="M12 2a5 5 0 1 0 0 10a5 5 0 1 0 0-10M4 22h16c.55 0 1-.45 1-1v-1c0-3.86-3.14-7-7-7h-4c-3.86 0-7 3.14-7 7v1c0 .55.45 1 1 1" /></svg>"""
                c_user.markdown(f"<div style='display:flex;align-items:center;gap:8px;'>{icon_svg} <b>{row['Usuario']}</b></div>", unsafe_allow_html=True)
                c_rol.markdown(f"<span style='color:#64748B;font-size:0.9em;'>Rol:</span> **{row['Rol']}**", unsafe_allow_html=True)
                if c_btn.button("Cambiar Clave", key=f"btn_pwd_{row['Usuario']}", use_container_width=True):
                    modal_change_password(row['Usuario'])
