"""
Rutas de administración: motor de scoring y cuentas de acceso.

Son las que sostienen la pantalla de configuración del frontend. Hasta ahora
estos dos ajustes solo se podían tocar desde la interfaz de Streamlit, así que
al retirarla la plataforma se habría quedado sin ninguna forma de cambiar un
peso, una tasa base o dar de alta un usuario.

Ambos recursos quedan reservados a Superadmin: los parámetros gobiernan el
scoring y el pricing de toda la cartera, y las cuentas dan acceso al circuito.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.dependencies import require_role
from api.schemas import ConfigParametro, Usuario
from database.daos_sqlserver import ConfigParametroDAO, UsuarioDAO
from database.db_core_sqlserver import get_db

router = APIRouter(prefix="/api/v1", tags=["Administración"])

solo_superadmin = require_role("Superadmin")

ROLES = ("Comercial", "Compliance", "Legal", "Riesgo", "Comité", "Cobranzas",
         "Superadmin")


class CambioParametro(BaseModel):
    """Un parámetro a actualizar."""

    clave: str = Field(..., min_length=1)
    valor: float


class AltaUsuario(BaseModel):
    """Alta o actualización de una cuenta. La contraseña se guarda con bcrypt."""

    usuario: str = Field(..., min_length=3)
    contrasena: str = Field(..., min_length=4)
    rol: str


class CambioContrasena(BaseModel):
    contrasena: str = Field(..., min_length=4)


# ── Parámetros del motor ──────────────────────────────────────────────
@router.get("/config/parametros", response_model=list[ConfigParametro],
            summary="Parámetros del motor de scoring")
def parametros(_: dict = Depends(solo_superadmin)) -> list[dict]:
    """Pesos de calificación, tasas base y factores de riesgo de ambas líneas."""
    valores = ConfigParametroDAO.get_all_as_dict()
    return [{"clave": clave, "valor": valor} for clave, valor in sorted(valores.items())]


@router.put("/config/parametros", response_model=list[ConfigParametro],
            summary="Actualiza parámetros del motor")
def actualizar_parametros(cambios: list[CambioParametro],
                          db: Session = Depends(get_db),
                          _: dict = Depends(solo_superadmin)) -> list[dict]:
    """
    Aplica todos los cambios en una sola transacción: una política de scoring a
    medio guardar dejaría el motor calificando con pesos incoherentes.
    """
    if not cambios:
        raise HTTPException(status_code=422,
                            detail="No se recibió ningún parámetro que actualizar.")

    conocidos = ConfigParametroDAO.get_all_as_dict()
    desconocidos = [c.clave for c in cambios if c.clave not in conocidos]
    if desconocidos:
        raise HTTPException(
            status_code=422,
            detail="Parámetros no reconocidos: " + ", ".join(sorted(desconocidos)))

    try:
        for cambio in cambios:
            ConfigParametroDAO.update_param(cambio.clave, cambio.valor, session=db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        # La caché del proceso queda invalidada tanto si se guardó como si no.
        ConfigParametroDAO.get_all_as_dict.clear()

    return parametros(_)


# ── Cuentas de acceso ─────────────────────────────────────────────────
# `Usuario` lleva los alias `user`/`role` para poder leerse de las columnas de la
# tabla, pero la API habla en los mismos términos que el resto de sus recursos:
# se serializa por nombre de campo, no por alias.
@router.get("/usuarios", response_model=list[Usuario], response_model_by_alias=False,
            summary="Cuentas de acceso")
def usuarios(db: Session = Depends(get_db),
             _: dict = Depends(solo_superadmin)) -> list[dict]:
    """Usuario y rol. El hash de la contraseña no sale nunca de la base."""
    return [{"usuario": f["Usuario"], "rol": f["Rol"]}
            for f in UsuarioDAO.get_all(session=db)]


@router.post("/usuarios", response_model=Usuario, response_model_by_alias=False,
             status_code=status.HTTP_201_CREATED,
             summary="Alta o actualización de una cuenta")
def crear_usuario(datos: AltaUsuario, db: Session = Depends(get_db),
                  _: dict = Depends(solo_superadmin)) -> dict:
    if datos.rol not in ROLES:
        raise HTTPException(status_code=422,
                            detail="Rol no reconocido: " + datos.rol)
    UsuarioDAO.upsert(datos.usuario, datos.contrasena, datos.rol, session=db)
    db.commit()
    return {"usuario": datos.usuario, "rol": datos.rol}


@router.put("/usuarios/{usuario}/contrasena", status_code=204,
            summary="Restablece la contraseña de una cuenta")
def cambiar_contrasena(usuario: str, datos: CambioContrasena,
                       db: Session = Depends(get_db),
                       _: dict = Depends(solo_superadmin)) -> None:
    existentes = {f["Usuario"] for f in UsuarioDAO.get_all(session=db)}
    if usuario not in existentes:
        raise HTTPException(status_code=404,
                            detail=f"No existe la cuenta {usuario}.")
    UsuarioDAO.update_password(usuario, datos.contrasena, session=db)
    db.commit()
