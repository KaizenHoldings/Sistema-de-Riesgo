"""Dependencias de autenticación y autorización de la API."""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import ExpiredSignatureError, InvalidTokenError

from api.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, str]:
    """Devuelve la identidad autenticada después de verificar el JWT."""
    try:
        payload = decode_access_token(token)
    except (ExpiredSignatureError, InvalidTokenError, RuntimeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de autenticación inválidas o vencidas.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"user": payload["user"], "role": payload["role"]}


def require_role(*allowed_roles: str) -> Callable:
    """Crea una dependencia que limita el endpoint a los roles indicados."""
    allowed = frozenset(allowed_roles)
    if not allowed:
        raise ValueError("require_role necesita al menos un rol permitido.")

    def dependency(current_user: dict[str, str] = Depends(get_current_user)):
        if current_user["role"] not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="El usuario no posee el rol requerido.")
        return current_user

    return dependency
