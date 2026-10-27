import pytest
from services.auth_service import AuthService
from database.models import Usuario

class MockSessionState(dict):
    def __getattr__(self, item):
        return self.get(item)
    def __setattr__(self, key, value):
        self[key] = value

@pytest.fixture
def mock_st(mocker):
    # Creamos un mock completo para streamlit
    mock_streamlit = mocker.patch("services.auth_service.st")
    
    # Configuramos session_state como nuestro dict especial
    session_state = MockSessionState()
    mock_streamlit.session_state = session_state
    
    # Configuramos context.cookies
    mock_streamlit.context.cookies = {}
    
    return mock_streamlit

@pytest.fixture
def mock_dao(mocker):
    # Mockeamos el DAO donde se importa (en services.auth_service)
    return mocker.patch("services.auth_service.UsuarioDAO.get_by_credentials")

def test_login_happy_path(mock_st, mock_dao):
    """Evalúa el inicio de sesión exitoso con credenciales válidas."""
    # Configurar el DAO para devolver un usuario válido
    mock_dao.return_value = Usuario(user="admin@kfg.com", password="hash", role="Superadmin")
    
    # Ejecutar login
    result = AuthService.login("admin@kfg.com", "secret123")
    
    # Verificaciones
    assert result is True
    assert mock_st.session_state['auth'] is True
    assert mock_st.session_state['current_user'] == "admin@kfg.com"
    assert mock_st.session_state['role'] == "Superadmin"
    assert 'login_token' in mock_st.session_state

def test_login_invalid_credentials(mock_st, mock_dao):
    """Evalúa el fallo de inicio de sesión con credenciales incorrectas."""
    # Configurar el DAO para devolver None (usuario no encontrado)
    mock_dao.return_value = None
    
    # Ejecutar login
    result = AuthService.login("wrong@user.com", "wrongpass")
    
    # Verificaciones
    assert result is False
    assert mock_st.session_state.get('auth') is not True

def test_try_restore_session_success(mock_st, mocker):
    """Evalúa la restauración de sesión mediante una cookie válida."""
    # Simular una cookie con un token base64 válido: "testuser::Admin"
    # "testuser::Admin" -> dGVzdHVzZXI6OkFkbWlu
    mock_st.context.cookies = {"kfg_auth": "dGVzdHVzZXI6OkFkbWlu"}
    
    # Asegurar que no hay sesión activa ni token de logout
    mock_st.session_state['auth'] = False
    mock_st.session_state['logout_token'] = False
    
    # Ejecutar restauración
    result = AuthService.try_restore_session()
    
    # Verificaciones
    assert result is True
    assert mock_st.session_state['auth'] is True
    assert mock_st.session_state['current_user'] == "testuser"
    assert mock_st.session_state['role'] == "Admin"
