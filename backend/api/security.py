"""Creación y validación de los JWT compartidos por FastAPI y Streamlit."""

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from dotenv import load_dotenv

load_dotenv()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8
ACCESS_TOKEN_EXPIRE_SECONDS = ACCESS_TOKEN_EXPIRE_MINUTES * 60
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "").strip()


def _secret_key() -> str:
    """Obtiene el secreto de firma y falla cerrado si no está configurado."""
    if len(SECRET_KEY) < 32:
        raise RuntimeError(
            "JWT_SECRET_KEY debe estar configurada con al menos 32 caracteres.")
    return SECRET_KEY


def create_access_token(user: str, role: str,
                        expires_delta: timedelta | None = None) -> str:
    """Firma un token con identidad, rol y vencimiento UTC."""
    if not str(user or "").strip() or not str(role or "").strip():
        raise ValueError("El token requiere las claims 'user' y 'role'.")
    now = datetime.now(timezone.utc)
    expires_at = now + (expires_delta or timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": str(user).strip(), "user": str(user).strip(),
        "role": str(role).strip(), "iat": now, "exp": expires_at,
    }
    return jwt.encode(payload, _secret_key(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Verifica firma, algoritmo, expiración y claims obligatorias."""
    payload = jwt.decode(
        token, _secret_key(), algorithms=[ALGORITHM],
        options={"require": ["exp", "iat", "user", "role", "sub"]},
    )
    if payload.get("sub") != payload.get("user"):
        raise jwt.InvalidTokenError("La identidad del token es inconsistente.")
    return payload


encode_token = create_access_token
decode_token = decode_access_token
