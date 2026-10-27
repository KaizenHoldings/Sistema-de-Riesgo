"""Emisión OAuth2 de tokens de acceso para KFG Risk Architect."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.security import create_access_token
from database.daos_sqlserver import UsuarioDAO
from database.db_core_sqlserver import get_db

router = APIRouter(tags=["Autenticación"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/token", response_model=TokenResponse,
             summary="Autenticación OAuth2")
def token(form: OAuth2PasswordRequestForm = Depends(),
          db: Session = Depends(get_db)) -> TokenResponse:
    """Valida con el DAO bcrypt existente y entrega un JWT firmado."""
    user = UsuarioDAO.get_by_credentials(form.username, form.password, session=db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(user.user, user.role))
