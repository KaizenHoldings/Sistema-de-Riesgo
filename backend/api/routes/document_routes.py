"""
Gestión documental del cliente: checklist KYC, carga, descarga y SharePoint.

Reproduce el circuito que llevaba la vista `client_profile` de Streamlit. Las
reglas que se conservan tal cual, porque son de negocio y no de presentación:

* El checklist exigible depende del tipo de cliente: siete requisitos para
  persona natural, diez para jurídica.
* Cada ítem tiene **un solo archivo vigente**. Al subir uno nuevo, el anterior
  se sustituye conservando el nombre del requisito y la extensión del original.
* Una carga sobre un ítem ya cubierto no es un alta: el documento pasa a
  `Desactualizado` para señalar que la versión de SharePoint quedó obsoleta.
* Marcar el primer requisito de un cliente en `Prospecto` lo mueve a
  `KYC Pendiente`.
* Aprobar el KYC queda reservado a Cumplimiento y Superadmin.
"""

import io
import json

from fastapi import (APIRouter, Depends, File, Form, HTTPException, UploadFile,
                     status)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, require_role
from api.schemas import Cliente, DocumentoCliente
from api.schemas.base import ModeloKFG, Texto
from database.daos_sqlserver import (SYNC_OK, SYNC_PENDIENTE, ClienteDAO,
                                     DocumentoClienteDAO)
from database.db_core_sqlserver import get_db
from services.sharepoint_service import SharePointService
from services.storage_service import StorageService

router = APIRouter(prefix="/api/v1/clientes", tags=["Documentos"])

autenticado = Depends(get_current_user)
solo_cumplimiento = require_role("Compliance", "Superadmin")

DOCS_NATURAL = (
    "Cédula de Identidad vigente",
    "RIF personal",
    "Comprobante de domicilio (menos de 3 meses)",
    "Constancia de ingresos / Declaración de ISLR",
    "Estado de cuenta bancario (últimos 3 meses)",
    "Referencias bancarias",
    "Declaración jurada de origen de fondos",
)

DOCS_JURIDICA = (
    "RIF de la empresa",
    "Acta Constitutiva y Estatutos Sociales",
    "Última Acta de Asamblea",
    "Poderes notariados del Representante Legal",
    "Cédula de Identidad del Representante Legal",
    "RIF del Representante Legal",
    "Estados financieros auditados (últimos 2 años)",
    "Referencias bancarias",
    "Comprobante de domicilio fiscal (menos de 3 meses)",
    "Declaración jurada de origen de fondos",
)

AVISO_DESACTUALIZADO = ("El documento ha sido reemplazado y la nueva versión no "
                        "se encuentra sincronizada con SharePoint")


class ItemChecklist(ModeloKFG):
    """Un requisito del checklist y el estado real de su documento."""

    doc_name: str
    marcado: bool = False
    #: Cierto solo si el archivo existe de verdad en el repositorio. Una casilla
    #: marcada a mano sin archivo detrás debe seguir pidiendo la carga.
    tiene_archivo: bool = False
    file_name: Texto = None
    documento_id: int | None = None
    sp_sync_status: str = SYNC_PENDIENTE
    aviso: Texto = None


class Checklist(ModeloKFG):
    """Checklist completo del cliente, con su avance."""

    cliente_id: int
    tipo: Texto = None
    kyc_status: Texto = None
    items: list[ItemChecklist] = []
    completados: int = 0
    total: int = 0


class MarcasChecklist(BaseModel):
    """Estado de las casillas que el usuario ha marcado o desmarcado."""

    marcas: dict[str, bool]


class AprobacionKyc(BaseModel):
    observaciones: str = ""


class ResultadoCarga(ModeloKFG):
    archivo: str
    carpeta: str
    documento_id: int | None = None
    sp_sync_status: str = SYNC_PENDIENTE
    kyc_status: Texto = None


class _ArchivoSubido:
    """
    Adaptador entre `UploadFile` de FastAPI y lo que espera `StorageService`.

    El servicio de almacenamiento se escribió contra el `UploadedFile` de
    Streamlit, que expone `.name` y `.getvalue()`. Envolverlo aquí evita tocar
    una pieza que ya está probada solo por un cambio de nombres.
    """

    def __init__(self, subida: UploadFile):
        self.name = subida.filename or "documento"
        self._contenido = subida.file.read()

    def getvalue(self) -> bytes:
        return self._contenido


def _cliente(cli_id: int, db: Session) -> dict:
    registro = ClienteDAO.get_by_id(cli_id, session=db)
    if not registro:
        raise HTTPException(status_code=404,
                            detail=f"No existe el cliente {cli_id}.")
    return registro


def _requisitos(tipo: str | None) -> tuple[str, ...]:
    return DOCS_NATURAL if (tipo or "").strip() == "Natural" else DOCS_JURIDICA


def _marcas(cliente: dict) -> dict:
    try:
        return json.loads(cliente.get("docs_json") or "{}")
    except (TypeError, ValueError):
        # Un JSON corrupto no debe tumbar la ficha: se trata como sin marcar.
        return {}


def _carpeta(cliente: dict) -> str:
    return f"{cliente.get('cedula_rif', '')} {cliente.get('nombre', '')}".strip()


@router.get("/{cli_id}/checklist", response_model=Checklist,
            summary="Checklist KYC del cliente")
def checklist(cli_id: int, db: Session = Depends(get_db),
              _: dict = autenticado) -> dict:
    """
    Requisitos exigibles y estado real de cada uno.

    Antes de responder se reconcilia el inventario: los archivos que ya estaban
    en el repositorio pero no tenían fila en la tabla se registran, que es lo que
    ocurre con los clientes anteriores a la integración con SharePoint.
    """
    cliente = _cliente(cli_id, db)
    marcas = _marcas(cliente)
    requisitos = _requisitos(cliente.get("tipo"))

    try:
        existentes = StorageService.list_client_documents(
            cliente.get("cedula_rif"), cliente.get("nombre"))
        DocumentoClienteDAO.sincronizar_inventario(
            cli_id, existentes, carpeta=f"clients/{_carpeta(cliente)}", session=db)
        db.commit()
    except Exception:
        db.rollback()

    registros = {d["file_name"]: d
                 for d in DocumentoClienteDAO.get_by_cliente(cli_id, session=db)}

    items: list[dict] = []
    for requisito in requisitos:
        archivo = None
        try:
            archivo = StorageService.get_document_file(
                cliente.get("cedula_rif"), cliente.get("nombre"), requisito)
        except Exception:
            archivo = None

        registro = registros.get(archivo[1]) if archivo else None
        estado = (registro or {}).get("sp_sync_status") or SYNC_PENDIENTE

        items.append({
            "doc_name": requisito,
            "marcado": bool(marcas.get(requisito, False)),
            "tiene_archivo": archivo is not None,
            "file_name": archivo[1] if archivo else None,
            "documento_id": (registro or {}).get("id"),
            "sp_sync_status": estado,
            "aviso": AVISO_DESACTUALIZADO if estado == "Desactualizado" else None,
        })

    return {
        "cliente_id": cli_id,
        "tipo": cliente.get("tipo"),
        "kyc_status": cliente.get("kyc_status"),
        "items": items,
        "completados": sum(1 for i in items if i["tiene_archivo"]),
        "total": len(requisitos),
    }


@router.put("/{cli_id}/checklist", response_model=Checklist,
            summary="Actualiza las casillas del checklist")
def actualizar_checklist(cli_id: int, cuerpo: MarcasChecklist,
                         db: Session = Depends(get_db),
                         _: dict = autenticado) -> dict:
    """Guarda las marcas y asciende de `Prospecto` en cuanto hay una cubierta."""
    cliente = _cliente(cli_id, db)
    requisitos = _requisitos(cliente.get("tipo"))

    desconocidas = set(cuerpo.marcas) - set(requisitos)
    if desconocidas:
        raise HTTPException(
            status_code=422,
            detail="Requisitos no aplicables a este tipo de cliente: "
                   + ", ".join(sorted(desconocidas)))

    marcas = _marcas(cliente)
    marcas.update(cuerpo.marcas)
    persistidas = {r: bool(marcas.get(r, False)) for r in requisitos}

    estado = cliente.get("kyc_status")
    if estado == "Prospecto" and any(persistidas.values()):
        estado = "KYC Pendiente"

    ClienteDAO.update_docs_and_status(cli_id, json.dumps(persistidas), estado,
                                      session=db)
    db.commit()
    return checklist(cli_id, db)


@router.post("/{cli_id}/documentos", response_model=ResultadoCarga,
             status_code=status.HTTP_201_CREATED,
             summary="Carga el documento de un requisito")
def cargar_documento(cli_id: int, doc_name: str = Form(...),
                     archivo: UploadFile = File(...),
                     db: Session = Depends(get_db),
                     _: dict = autenticado) -> dict:
    """
    Guarda el archivo del requisito indicado y deja constancia en la tabla.

    Si el requisito ya tenía documento, el registro pasa a `Desactualizado`: el
    archivo del repositorio es nuevo, pero el de SharePoint todavía es el viejo.
    """
    cliente = _cliente(cli_id, db)

    if doc_name not in _requisitos(cliente.get("tipo")):
        raise HTTPException(
            status_code=422,
            detail=f"El requisito {doc_name!r} no aplica a un cliente "
                   f"{cliente.get('tipo')}.")

    try:
        guardado = StorageService.save_single_document(
            _ArchivoSubido(archivo), cliente.get("cedula_rif"),
            cliente.get("nombre"), doc_name)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e)) from e

    doc_id, estado = DocumentoClienteDAO.registrar_carga(
        cli_id, guardado["archivo"], doc_name=doc_name,
        carpeta=guardado["carpeta"], session=db)

    marcas = _marcas(cliente)
    requisitos = _requisitos(cliente.get("tipo"))
    persistidas = {r: bool(marcas.get(r, False)) for r in requisitos}
    persistidas[doc_name] = True

    kyc = cliente.get("kyc_status")
    if kyc == "Prospecto":
        kyc = "KYC Pendiente"

    ClienteDAO.update_docs_and_status(cli_id, json.dumps(persistidas), kyc,
                                      session=db)
    db.commit()

    return {
        "archivo": guardado["archivo"],
        "carpeta": guardado["carpeta"],
        "documento_id": doc_id,
        "sp_sync_status": estado,
        "kyc_status": kyc,
    }


@router.get("/{cli_id}/documentos/{doc_id}/descargar",
            summary="Descarga un documento del cliente")
def descargar_documento(cli_id: int, doc_id: int, db: Session = Depends(get_db),
                        _: dict = autenticado) -> StreamingResponse:
    """Entrega el binario tal cual está en el repositorio."""
    cliente = _cliente(cli_id, db)

    registro = next((d for d in DocumentoClienteDAO.get_by_cliente(cli_id, session=db)
                     if d["id"] == doc_id), None)
    if not registro:
        raise HTTPException(status_code=404,
                            detail=f"El cliente {cli_id} no tiene el documento {doc_id}.")

    contenido = StorageService.get_file_bytes(
        cliente.get("cedula_rif"), cliente.get("nombre"), registro["file_name"])
    if contenido is None:
        raise HTTPException(
            status_code=404,
            detail=f"El archivo {registro['file_name']} está registrado pero no "
                   "se encuentra en el repositorio.")

    return StreamingResponse(
        io.BytesIO(contenido),
        media_type="application/octet-stream",
        headers={"Content-Disposition":
                 f'attachment; filename="{registro["file_name"]}"'},
    )


@router.post("/{cli_id}/documentos/{doc_id}/sincronizar",
             response_model=DocumentoCliente,
             summary="Sincroniza un documento con SharePoint")
def sincronizar_documento(cli_id: int, doc_id: int, db: Session = Depends(get_db),
                          _: dict = autenticado) -> dict:
    """
    Sube un único archivo y marca solo su registro.

    Es deliberadamente independiente de la sincronización masiva: un fallo de red
    en un documento no debe dejar a los demás en un estado indeterminado.
    """
    cliente = _cliente(cli_id, db)

    registro = next((d for d in DocumentoClienteDAO.get_by_cliente(cli_id, session=db)
                     if d["id"] == doc_id), None)
    if not registro:
        raise HTTPException(status_code=404,
                            detail=f"El cliente {cli_id} no tiene el documento {doc_id}.")

    sp = SharePointService()
    if not sp.esta_configurado():
        raise HTTPException(
            status_code=503,
            detail="SharePoint no está configurado. Faltan estas variables de "
                   "entorno: " + ", ".join(sp.faltantes()))

    contenido = StorageService.get_file_bytes(
        cliente.get("cedula_rif"), cliente.get("nombre"), registro["file_name"])
    if contenido is None:
        raise HTTPException(
            status_code=404,
            detail=f"No se pudo leer {registro['file_name']} del repositorio.")

    try:
        sp.upload_file(contenido, registro["file_name"], _carpeta(cliente))
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error al sincronizar {registro['file_name']}: {e}") from e

    DocumentoClienteDAO.update_sharepoint_sync_status(doc_id, SYNC_OK, session=db)
    db.commit()

    return next(d for d in DocumentoClienteDAO.get_by_cliente(cli_id, session=db)
                if d["id"] == doc_id)


@router.post("/{cli_id}/kyc/aprobar", response_model=Cliente,
             summary="Aprueba el expediente KYC")
def aprobar_kyc(cli_id: int, cuerpo: AprobacionKyc,
                db: Session = Depends(get_db),
                usuario: dict = Depends(solo_cumplimiento)) -> dict:
    """
    Cierra la debida diligencia del cliente.

    Solo desde `Prospecto` o `KYC Pendiente`: reaprobar un expediente ya cerrado
    reescribiría la firma y la fecha de quien lo aprobó en su día.
    """
    cliente = _cliente(cli_id, db)

    if cliente.get("kyc_status") not in ("Prospecto", "KYC Pendiente"):
        raise HTTPException(
            status_code=409,
            detail=f"El expediente KYC está en {cliente.get('kyc_status')!r} y "
                   "no admite una nueva aprobación.")

    from datetime import datetime

    ClienteDAO.update_kyc_approval(cli_id, cuerpo.observaciones,
                                   usuario.get("user", ""),
                                   datetime.now().strftime("%Y-%m-%d"),
                                   session=db)
    db.commit()
    return _cliente(cli_id, db)
