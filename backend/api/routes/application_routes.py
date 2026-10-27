"""
Rutas de expedientes de crédito.

Las dos líneas de producto viven en tablas distintas y con columnas distintas,
así que cada una tiene su propio sub-recurso —`/corporativos` y
`/automotrices`— en lugar de un parámetro `tipo` que obligaría a devolver un
modelo difuso. Las transiciones del circuito no están aquí: son de
`workflow_routes`, que es quien aplica las reglas.

Las listas se filtran por rol y por pestaña: `view_mode=pending` devuelve lo
que espera la firma de quien consulta y `view_mode=history` lo que ya pasó por
sus manos. Quien origina —Comercial— no firma, así que sus pestañas separan las
solicitudes abiertas de las ya resueltas.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, require_role
from api.schemas import ExpedienteAutomotriz, ExpedienteCorporativo
from database.daos_sqlserver import (ExpedienteAutomotrizDAO,
                                     ExpedienteCorporativoDAO)
from database.db_core_sqlserver import get_db

router = APIRouter(prefix="/api/v1/expedientes", tags=["Expedientes"], dependencies=[Depends(get_current_user)])
solo_origen = require_role("Comercial", "Compliance", "Legal", "Riesgo",
                           "Comité", "Superadmin")
solo_comite = require_role("Comité", "Superadmin")
# Reabrir una solicitud es del área que la originó.
solo_comercial = require_role("Comercial", "Superadmin")

# Dictámenes desde los que una solicitud puede volver a presentarse: el
# rechazo firme y las devoluciones, que viajan como «REVISIÓN-<etapa>».
PREFIJOS_REEVALUABLES = ("RECHAZADO", "REVISIÓN", "REVISION")


def _obtener(dao, exp_id: int, etiqueta: str, db: Session) -> dict:
    registro = dao.get_by_id(exp_id, session=db)
    if not registro:
        raise HTTPException(status_code=404,
                            detail=f"No existe el expediente {etiqueta} {exp_id}.")
    return registro


def _ultimo_del_cliente(dao, cliente: str, db: Session) -> dict | None:
    """
    Último expediente abierto a nombre de un cliente.

    `get_paginated` ordena por id ascendente, así que el recién creado es la
    última página de tamaño uno; es la forma de devolver el recurso creado sin
    añadir un método al DAO solo para leer el identidad recién asignado.
    """
    total = dao.count(cliente=cliente, session=db)
    if total < 1:
        return None
    filas = dao.get_paginated(page=total, page_size=1, cliente=cliente, session=db)
    return filas[0] if filas else None


def _reevaluar(dao, tipo: str, etiqueta: str, exp_id: int, db: Session) -> dict:
    """
    Clona la solicitud en un expediente nuevo y sin firmas.

    El original no se toca: queda como histórico, y el hijo apunta a él con
    `parent_expediente_id`. Solo se reabre lo que está cerrado en falso —un
    rechazo o una devolución—; reevaluar un expediente vivo duplicaría el
    trabajo del circuito, así que responde 409.
    """
    registro = _obtener(dao, exp_id, etiqueta, db)
    dictamen = str(registro.get("dictamen") or "")
    if not dictamen.startswith(PREFIJOS_REEVALUABLES):
        raise HTTPException(
            status_code=409,
            detail=f"El expediente está en {dictamen or 'PENDIENTE'}: solo se "
                   "reevalúan los rechazados o devueltos.")

    nuevo_id = dao.clonar_para_reevaluacion(
        exp_id, fecha=datetime.now().strftime("%Y-%m-%d"), session=db)
    if nuevo_id is None:
        raise HTTPException(status_code=404,
                            detail=f"No existe el expediente {etiqueta} {exp_id}.")
    db.commit()
    return {"expediente_id": nuevo_id, "tipo": tipo,
            "parent_expediente_id": exp_id}


# ── Corporativos ──────────────────────────────────────────────────────
@router.get("/corporativos", response_model=list[ExpedienteCorporativo],
            summary="Lista de expedientes corporativos")
def listar_corporativos(pagina: int = Query(1, ge=1),
                        por_pagina: int = Query(25, ge=1, le=200),
                        dictamen: str | None = None,
                        cliente: str | None = None,
                        firmas_completas: bool | None = None,
                        view_mode: str | None = Query(
                            None, pattern="^(pending|history|all)$",
                            description="Pestaña: 'pending', 'history' o "
                                        "'all' para el seguimiento comercial"),
                        usuario: dict = Depends(get_current_user),
                        db: Session = Depends(get_db)) -> list[dict]:
    """
    Expedientes activos paginados; `firmas_completas` aísla los listos para Comité.

    Con `view_mode` la lista responde a la pestaña de quien consulta —lo que
    espera su firma o lo que ya firmó—; sin él, al recorte por rol de siempre.
    """
    return ExpedienteCorporativoDAO.get_paginated(
        page=pagina, page_size=por_pagina, dictamen=dictamen, cliente=cliente,
        firmas_completas=firmas_completas, rol_visibilidad=usuario["role"],
        modo_vista=view_mode, session=db)


@router.get("/corporativos/resumen", summary="Totales corporativos por dictamen")
def resumen_corporativos(db: Session = Depends(get_db)) -> dict:
    """Conteo y monto agregados por dictamen, resueltos con GROUP BY en el motor."""
    return ExpedienteCorporativoDAO.get_resumen_por_dictamen(session=db)


@router.get("/corporativos/{exp_id}", response_model=ExpedienteCorporativo,
            summary="Expediente corporativo")
def obtener_corporativo(exp_id: int, db: Session = Depends(get_db)) -> dict:
    return _obtener(ExpedienteCorporativoDAO, exp_id, "corporativo", db)


@router.post("/corporativos", response_model=ExpedienteCorporativo,
             status_code=status.HTTP_201_CREATED,
             summary="Alta de expediente corporativo")
def crear_corporativo(datos: ExpedienteCorporativo,
                      _usuario: dict = Depends(solo_origen),
                      db: Session = Depends(get_db)) -> dict:
    """Abre el expediente en Cumplimiento, que es donde empieza el circuito."""
    if not datos.cliente:
        raise HTTPException(status_code=422,
                            detail="El expediente requiere el nombre del cliente.")
    ExpedienteCorporativoDAO.create(
        fecha=datos.fecha or "", cliente=datos.cliente, rif=datos.rif or "",
        monto=float(datos.monto or 0), cliente_id=datos.cliente_id,
        descripcion=datos.descripcion or "", session=db)
    db.commit()
    return _ultimo_del_cliente(ExpedienteCorporativoDAO, datos.cliente, db) or datos.model_dump()


@router.delete("/corporativos/{exp_id}", status_code=204,
               summary="Baja lógica de expediente corporativo")
def eliminar_corporativo(exp_id: int, _usuario: dict = Depends(solo_comite), db: Session = Depends(get_db)) -> None:
    """Marca `eliminado = 1`; el histórico se conserva para auditoría."""
    _obtener(ExpedienteCorporativoDAO, exp_id, "corporativo", db)
    ExpedienteCorporativoDAO.delete(exp_id, session=db)
    db.commit()


@router.post("/corporativos/{exp_id}/reevaluar", status_code=status.HTTP_201_CREATED,
             summary="Reabre un expediente corporativo en una solicitud nueva")
def reevaluar_corporativo(exp_id: int, _usuario: dict = Depends(solo_comercial),
                          db: Session = Depends(get_db)) -> dict:
    """Devuelve el id del expediente nuevo, que empieza el circuito desde cero."""
    return _reevaluar(ExpedienteCorporativoDAO, "corp", "corporativo", exp_id, db)


# ── Automotrices ──────────────────────────────────────────────────────
@router.get("/automotrices", response_model=list[ExpedienteAutomotriz],
            summary="Lista de expedientes automotrices")
def listar_automotrices(pagina: int = Query(1, ge=1),
                        por_pagina: int = Query(25, ge=1, le=200),
                        dictamen: str | None = None,
                        cliente: str | None = None,
                        firmas_completas: bool | None = None,
                        view_mode: str | None = Query(
                            None, pattern="^(pending|history|all)$",
                            description="Pestaña: 'pending', 'history' o "
                                        "'all' para el seguimiento comercial"),
                        usuario: dict = Depends(get_current_user),
                        db: Session = Depends(get_db)) -> list[dict]:
    """Mismas pestañas y mismo recorte por rol que la lista corporativa."""
    return ExpedienteAutomotrizDAO.get_paginated(
        page=pagina, page_size=por_pagina, dictamen=dictamen, cliente=cliente,
        firmas_completas=firmas_completas, rol_visibilidad=usuario["role"],
        modo_vista=view_mode, session=db)


@router.get("/automotrices/resumen", summary="Totales automotrices por dictamen")
def resumen_automotrices(db: Session = Depends(get_db)) -> dict:
    return ExpedienteAutomotrizDAO.get_resumen_por_dictamen(session=db)


@router.get("/automotrices/{exp_id}", response_model=ExpedienteAutomotriz,
            summary="Expediente automotriz")
def obtener_automotriz(exp_id: int, db: Session = Depends(get_db)) -> dict:
    return _obtener(ExpedienteAutomotrizDAO, exp_id, "automotriz", db)


@router.post("/automotrices", response_model=ExpedienteAutomotriz,
             status_code=status.HTTP_201_CREATED,
             summary="Alta de expediente automotriz")
def crear_automotriz(datos: ExpedienteAutomotriz,
                     _usuario: dict = Depends(solo_origen),
                     db: Session = Depends(get_db)) -> dict:
    if not datos.cliente:
        raise HTTPException(status_code=422,
                            detail="El expediente requiere el nombre del cliente.")
    ExpedienteAutomotrizDAO.create(
        fecha=datos.fecha or "", cliente=datos.cliente, cedula=datos.cedula or "",
        monto=float(datos.monto or 0), cliente_id=datos.cliente_id,
        descripcion=datos.descripcion or "", session=db)
    db.commit()
    return _ultimo_del_cliente(ExpedienteAutomotrizDAO, datos.cliente, db) or datos.model_dump()


@router.delete("/automotrices/{exp_id}", status_code=204,
               summary="Baja lógica de expediente automotriz")
def eliminar_automotriz(exp_id: int, _usuario: dict = Depends(solo_comite), db: Session = Depends(get_db)) -> None:
    _obtener(ExpedienteAutomotrizDAO, exp_id, "automotriz", db)
    ExpedienteAutomotrizDAO.delete(exp_id, session=db)
    db.commit()


@router.post("/automotrices/{exp_id}/reevaluar", status_code=status.HTTP_201_CREATED,
             summary="Reabre un expediente automotriz en una solicitud nueva")
def reevaluar_automotriz(exp_id: int, _usuario: dict = Depends(solo_comercial),
                         db: Session = Depends(get_db)) -> dict:
    return _reevaluar(ExpedienteAutomotrizDAO, "auto", "automotriz", exp_id, db)
