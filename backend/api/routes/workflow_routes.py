"""
Rutas del circuito de evaluación.

Ninguna regla se decide aquí: cada manejador llama a `WorkflowService` y se
limita a traducir sus excepciones de dominio a códigos HTTP mediante `a_http`.
Así la API y la interfaz de Streamlit aplican exactamente las mismas guardas.
"""

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import Field
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, require_role
from api.routes._errores import a_http, a_http_datos
from api.schemas import TareaWorkflow
from api.schemas.base import ModeloKFG, Texto
from database.daos_sqlserver import (ExpedienteAutomotrizDAO,
                                      ExpedienteCorporativoDAO)
from database.db_core_sqlserver import get_db
from services.workflow_service import ErrorFlujo, WorkflowService

router = APIRouter(prefix="/api/v1/workflow", tags=["Flujo de trabajo"], dependencies=[Depends(get_current_user)])
solo_cumplimiento = require_role("Compliance", "Superadmin")
solo_legal = require_role("Legal", "Superadmin")
solo_riesgo = require_role("Riesgo", "Superadmin")
solo_comite = require_role("Comité", "Superadmin")
# Devolver y denegar no son solo del Comité: Legal también cierra o para una
# operación cuando la garantía no se sostiene jurídicamente.
devolucion_o_rechazo = require_role("Legal", "Comité", "Superadmin")

# A dónde puede devolver cada rol. El Comité llega al final y puede reabrir
# cualquier etapa; Legal evalúa en paralelo con Riesgo, así que no devuelve a
# una etapa simultánea a la suya: manda el expediente atrás, a quien lo presentó
# o a quien lo certificó.
DESTINOS_POR_ROL = {
    "Legal": ("Comercial", "Cumplimiento"),
}

Tipo = Path(..., pattern="^(corp|auto)$",
            description="Línea de producto: 'corp' o 'auto'.")


# ── Cuerpos de petición ───────────────────────────────────────────────
class Actor(ModeloKFG):
    """Quien ejecuta la transición; queda en la traza del expediente."""

    usuario: Texto = ""


class Certificacion(Actor):
    """
    Firma de Cumplimiento.

    `datos` son los campos AML/CFT que espera `update_compliance` de cada línea
    de producto. Viajan con la firma para que el servicio los persista en la
    misma transacción: una etapa certificada sin su debida diligencia registrada
    sería un expediente incompleto.
    """

    datos: dict | None = None


class Justificacion(Actor):
    """Transición que exige motivo escrito."""

    observaciones: str = Field(..., min_length=1)


class Devolucion(Justificacion):
    """Devolución a una etapa previa del circuito."""

    etapa_destino: str = Field(..., min_length=1)


class Dictamen(Actor):
    """Decisión del Comité. La tasa y el plazo solo aplican al aprobar."""

    dictamen: str = Field(..., pattern="^(APROBADO|RECHAZADO)$")
    tasa: float = 0.0
    plazo: int | None = None


@router.get("/pendientes/conteo", summary="Conteo de evaluaciones pendientes para el rol actual")
def conteo_pendientes(usuario: dict = Depends(get_current_user),
                      db: Session = Depends(get_db)) -> dict:
    rol = usuario.get("role") or ""
    corp = ExpedienteCorporativoDAO.count(rol_visibilidad=rol, modo_vista="pending", session=db)
    auto = ExpedienteAutomotrizDAO.count(rol_visibilidad=rol, modo_vista="pending", session=db)
    total = int(corp + auto)
    return {"total": total, "corp": int(corp), "auto": int(auto)}


# ── Consultas ─────────────────────────────────────────────────────────
@router.get("/{tipo}/{exp_id}/estado", summary="Estado del circuito")
def estado(exp_id: int, tipo: str = Tipo, db: Session = Depends(get_db)) -> dict:
    """Estado de flujo, dictamen y firmas registradas."""
    try:
        return WorkflowService.estado(exp_id, tipo, session=db)
    except ErrorFlujo as e:
        raise a_http(e) from e


@router.get("/{tipo}/{exp_id}/tareas", response_model=list[TareaWorkflow],
            summary="Tareas del expediente")
def tareas(exp_id: int, tipo: str = Tipo, estado: str | None = None,
           db: Session = Depends(get_db)) -> list[dict]:
    try:
        return WorkflowService.tareas(exp_id, tipo, estado=estado, session=db)
    except ErrorFlujo as e:
        raise a_http(e) from e


# ── Etapa de Cumplimiento ─────────────────────────────────────────────
@router.post("/{tipo}/{exp_id}/cumplimiento/certificar",
             summary="Certifica Cumplimiento y abre Crédito y Legal")
def certificar(exp_id: int, cuerpo: Certificacion, tipo: str = Tipo,
               _usuario: dict = Depends(solo_cumplimiento),
               db: Session = Depends(get_db)) -> dict:
    """
    Cierra la primera revisión formal y abre de golpe las dos evaluaciones
    simultáneas. Devuelve cuántas tareas quedaron abiertas.
    """
    try:
        resultado = WorkflowService.certificar_cumplimiento(
            exp_id, tipo, usuario=cuerpo.usuario or "", datos=cuerpo.datos,
            session=db)
    except ErrorFlujo as e:
        db.rollback()
        raise a_http(e) from e
    db.commit()
    return resultado


@router.post("/{tipo}/{exp_id}/cumplimiento/observar",
             summary="Devuelve el expediente a subsanación comercial")
def observar(exp_id: int, cuerpo: Justificacion, tipo: str = Tipo,
             _usuario: dict = Depends(solo_cumplimiento),
             db: Session = Depends(get_db)) -> dict:
    try:
        resultado = WorkflowService.observar(
            exp_id, tipo, cuerpo.observaciones, usuario=cuerpo.usuario or "",
            session=db)
    except ErrorFlujo as e:
        db.rollback()
        raise a_http(e) from e
    db.commit()
    return resultado


@router.post("/{tipo}/{exp_id}/cumplimiento/rechazar",
             summary="Desestima el expediente en Cumplimiento")
def rechazar_cumplimiento(exp_id: int, cuerpo: Justificacion, tipo: str = Tipo,
                          _usuario: dict = Depends(solo_cumplimiento),
                          db: Session = Depends(get_db)) -> dict:
    try:
        resultado = WorkflowService.rechazar_cumplimiento(
            exp_id, tipo, cuerpo.observaciones, usuario=cuerpo.usuario or "",
            session=db)
    except ErrorFlujo as e:
        db.rollback()
        raise a_http(e) from e
    db.commit()
    return resultado


# ── Etapas posteriores ────────────────────────────────────────────────
@router.post("/{tipo}/{exp_id}/legal", summary="Registra la firma de Legal")
def registrar_legal(exp_id: int, datos: dict, tipo: str = Tipo,
                    _usuario: dict = Depends(solo_legal),
                    db: Session = Depends(get_db)) -> dict:
    """
    `datos` son los campos de `update_legal` de la línea de producto. El
    servicio exige la certificación previa de Cumplimiento.
    """
    try:
        resultado = WorkflowService.registrar_legal(exp_id, tipo, datos, session=db)
    except ErrorFlujo as e:
        db.rollback()
        raise a_http(e) from e
    except TypeError as e:
        db.rollback()
        raise a_http_datos(e) from e
    db.commit()
    return resultado


@router.post("/{tipo}/{exp_id}/riesgo", summary="Registra la firma de Riesgo")
def registrar_riesgo(exp_id: int, datos: dict, tipo: str = Tipo,
                     _usuario: dict = Depends(solo_riesgo),
                     db: Session = Depends(get_db)) -> dict:
    try:
        resultado = WorkflowService.registrar_riesgo(exp_id, tipo, datos, session=db)
    except ErrorFlujo as e:
        db.rollback()
        raise a_http(e) from e
    except TypeError as e:
        db.rollback()
        raise a_http_datos(e) from e
    db.commit()
    return resultado


@router.post("/{tipo}/{exp_id}/dictamen", summary="Decisión del Comité")
def dictamen(exp_id: int, cuerpo: Dictamen, tipo: str = Tipo,
             _usuario: dict = Depends(solo_comite),
             db: Session = Depends(get_db)) -> dict:
    """Aprobar exige las tres firmas; rechazar puede hacerse en cualquier punto."""
    try:
        resultado = WorkflowService.emitir_dictamen(
            exp_id, tipo, cuerpo.dictamen, usuario=cuerpo.usuario or "",
            tasa=cuerpo.tasa, plazo=cuerpo.plazo, session=db)
    except ErrorFlujo as e:
        db.rollback()
        raise a_http(e) from e
    except Exception:
        db.rollback()
        raise
    db.commit()
    return resultado


@router.post("/{tipo}/{exp_id}/devolver", summary="Devuelve a una etapa previa")
def devolver(exp_id: int, cuerpo: Devolucion, tipo: str = Tipo,
             usuario: dict = Depends(devolucion_o_rechazo),
             db: Session = Depends(get_db)) -> dict:
    """La etapa destino se limita a la que el rol puede reabrir."""
    permitidas = DESTINOS_POR_ROL.get(usuario["role"])
    if permitidas and cuerpo.etapa_destino not in permitidas:
        raise HTTPException(
            status_code=422,
            detail=f"{usuario['role']} solo puede devolver a: "
                   + ", ".join(permitidas))
    try:
        resultado = WorkflowService.devolver(
            exp_id, tipo, cuerpo.etapa_destino, cuerpo.observaciones,
            usuario=cuerpo.usuario or "", session=db)
    except ErrorFlujo as e:
        db.rollback()
        raise a_http(e) from e
    db.commit()
    return resultado


@router.post("/{tipo}/{exp_id}/rechazar", summary="Rechazo administrativo")
def rechazar(exp_id: int, cuerpo: Justificacion, tipo: str = Tipo,
             _usuario: dict = Depends(devolucion_o_rechazo),
             db: Session = Depends(get_db)) -> dict:
    try:
        resultado = WorkflowService.rechazar(
            exp_id, tipo, cuerpo.observaciones, usuario=cuerpo.usuario or "",
            session=db)
    except ErrorFlujo as e:
        db.rollback()
        raise a_http(e) from e
    db.commit()
    return resultado
