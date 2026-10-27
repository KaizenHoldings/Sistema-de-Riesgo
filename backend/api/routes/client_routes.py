"""Rutas de clientes y de su repositorio documental."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, require_role
from api.schemas import Cliente, DocumentoCliente
from database.daos_sqlserver import ClienteDAO, DocumentoClienteDAO
from database.db_core_sqlserver import get_db

router = APIRouter(prefix="/api/v1/clientes", tags=["Clientes"], dependencies=[Depends(get_current_user)])
solo_origen = require_role("Comercial", "Compliance", "Legal", "Riesgo",
                           "Comité", "Superadmin")
solo_cumplimiento = require_role("Compliance", "Superadmin")


def _obtener(cli_id: int, db: Session) -> dict:
    registro = ClienteDAO.get_by_id(cli_id, session=db)
    if not registro:
        raise HTTPException(status_code=404,
                            detail=f"No existe el cliente {cli_id}.")
    return registro


@router.get("", response_model=list[Cliente], summary="Lista de clientes")
def listar(pagina: int = Query(1, ge=1),
           por_pagina: int = Query(25, ge=1, le=200),
           nombre: str | None = None,
           tipo: str | None = None,
           kyc_status: str | None = None,
           db: Session = Depends(get_db)) -> list[dict]:
    """Clientes paginados, con filtros opcionales por nombre, tipo y estado KYC."""
    return ClienteDAO.get_paginated(page=pagina, page_size=por_pagina,
                                    nombre=nombre, tipo=tipo,
                                    kyc_status=kyc_status, session=db)


@router.get("/{cli_id}", response_model=Cliente, summary="Ficha de un cliente")
def obtener(cli_id: int, db: Session = Depends(get_db)) -> dict:
    return _obtener(cli_id, db)


@router.post("", response_model=Cliente, status_code=status.HTTP_201_CREATED,
             summary="Alta de cliente")
def crear(datos: Cliente, _usuario: dict = Depends(solo_origen), db: Session = Depends(get_db)) -> dict:
    """Registra un cliente nuevo; nace en estado `Prospecto`."""
    ClienteDAO.create(
        fecha_registro=datos.fecha_registro or "", tipo=datos.tipo or "Natural",
        nombre=datos.nombre or "", cedula_rif=datos.cedula_rif or "",
        fecha_nacimiento=datos.fecha_nacimiento or "",
        nacionalidad=datos.nacionalidad or "", telefono=datos.telefono or "",
        email=datos.email or "", direccion=datos.direccion or "",
        actividad_economica=datos.actividad_economica or "",
        nombre_rep=datos.nombre_rep or "", cedula_rep=datos.cedula_rep or "",
        cargo_rep=datos.cargo_rep or "", docs_json=datos.docs_json or "{}",
        session=db)
    db.commit()
    nuevo_id = ClienteDAO.get_id_by_rif(datos.cedula_rif, session=db)
    return _obtener(nuevo_id, db)


@router.put("/{cli_id}/kyc", response_model=Cliente,
            summary="Actualiza el estado KYC")
def actualizar_kyc(cli_id: int, estado: str, _usuario: dict = Depends(solo_cumplimiento), db: Session = Depends(get_db)) -> dict:
    """Cambia el estado del expediente KYC del cliente."""
    _obtener(cli_id, db)
    ClienteDAO.update_kyc_status(cli_id, estado, session=db)
    db.commit()
    return _obtener(cli_id, db)


@router.put("/{cli_id}/observaciones", response_model=Cliente,
            summary="Actualiza las observaciones KYC")
def actualizar_observaciones(cli_id: int, observaciones: str,
                             _usuario: dict = Depends(solo_cumplimiento),
                             db: Session = Depends(get_db)) -> dict:
    _obtener(cli_id, db)
    ClienteDAO.update_kyc_observations(cli_id, observaciones, session=db)
    db.commit()
    return _obtener(cli_id, db)


@router.get("/{cli_id}/documentos", response_model=list[DocumentoCliente],
            summary="Documentos del cliente")
def documentos(cli_id: int, db: Session = Depends(get_db)) -> list[dict]:
    """Inventario documental con el estado de sincronización con SharePoint."""
    _obtener(cli_id, db)
    return DocumentoClienteDAO.get_by_cliente(cli_id, session=db)


@router.put("/documentos/{doc_id}/sincronizacion", status_code=204,
            summary="Marca el estado de sincronización de un documento")
def marcar_sincronizacion(doc_id: int, estado: str,
                          _usuario: dict = Depends(solo_cumplimiento),
                          db: Session = Depends(get_db)) -> None:
    DocumentoClienteDAO.update_sharepoint_sync_status(doc_id, estado, session=db)
    db.commit()
