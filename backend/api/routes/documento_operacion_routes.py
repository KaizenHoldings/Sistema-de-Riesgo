"""
Documentos de la operación, por expediente.

El repositorio del cliente —`document_routes`— guarda su expediente KYC: una
lista cerrada de requisitos con un archivo vigente cada uno. Esto es lo otro: lo
que sustenta **esta** solicitud y que Legal necesita descargar e inspeccionar.
No hay checklist ni nombres fijos; se cargan los archivos que la operación
tenga, con su propio nombre, y se listan los que haya.

Quién los ve está restringido: el área comercial, que los reúne, y Legal, que
los inspecciona. El resto del circuito evalúa con lo que cada etapa registra en
el expediente —riesgo con sus cifras, Cumplimiento con su debida diligencia— y
no necesita el respaldo documental de la operación, que incluye títulos de
propiedad y avalúos de terceros.
"""

import io
from datetime import datetime
from urllib.parse import quote

from fastapi import (APIRouter, Depends, File, HTTPException, UploadFile,
                     status)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, require_role
from api.routes._errores import a_http
from api.schemas.base import ModeloKFG
from database.daos_sqlserver import SYNC_OK, DocumentoExpedienteDAO
from database.db_core_sqlserver import get_db
from services.sharepoint_service import SharePointService
from services.storage_service import StorageService
from services.workflow_service import ErrorFlujo, WorkflowService

router = APIRouter(prefix="/api/v1/expedientes", tags=["Documentos de la operación"],
                   dependencies=[Depends(get_current_user)])

# Comercial y Legal aportan documentos (Legal aporta los contratos y anexos juridicos).
# Todos los roles involucrados en la evaluación y comité pueden consultar y descargar documentos.
ver_documentos = require_role("Comercial", "Legal", "Comité", "Riesgo", "Compliance", "Superadmin")
carga_documentos = require_role("Comercial", "Legal", "Superadmin")
# El tamano se limita para que una carga accidental no llene el disco del
# servidor de archivos.
LIMITE_BYTES = 25 * 1024 * 1024


class DocumentoOperacion(ModeloKFG):
    """Un archivo cargado contra la solicitud."""

    id: int
    expediente_id: int
    tipo_expediente: str
    file_name: str
    carpeta: str = ""
    tamano_bytes: int = 0
    cargado_por: str = ""
    fecha_carga: str = ""
    sp_sync_status: str = "No Sincronizado"
    fecha_sync: str = ""


class _Subida:
    """
    Adaptador entre `UploadFile` de FastAPI y lo que espera `StorageService`,
    que nacio para los objetos de Streamlit: nombre y bytes en memoria.
    """

    def __init__(self, nombre: str, contenido: bytes):
        self.name = nombre
        self._contenido = contenido

    def getvalue(self) -> bytes:
        return self._contenido


def _expediente(tipo: str, exp_id: int, db: Session) -> dict:
    try:
        return WorkflowService.obtener(exp_id, tipo, session=db)
    except ErrorFlujo as e:
        raise a_http(e) from e


def _identidad(tipo: str, registro: dict) -> tuple:
    """Cedula/RIF y nombre del cliente, que es como se nombra su carpeta."""
    documento = registro.get("rif") if tipo == "corp" else registro.get("cedula")
    return (str(documento or f"exp-{registro.get('id')}"),
            str(registro.get("cliente") or "sin nombre"))


@router.get("/{tipo}/{exp_id}/documentos", response_model=list[DocumentoOperacion],
            summary="Documentos cargados en la solicitud")
def listar(exp_id: int, tipo: str,
           _usuario: dict = Depends(ver_documentos),
           db: Session = Depends(get_db)) -> list[dict]:
    """Lo que hay cargado, del mas reciente al mas antiguo."""
    _validar_tipo(tipo)
    _expediente(tipo, exp_id, db)
    return DocumentoExpedienteDAO.get_by_expediente(exp_id, tipo, session=db)


@router.post("/{tipo}/{exp_id}/documentos", response_model=list[DocumentoOperacion],
             status_code=status.HTTP_201_CREATED,
             summary="Carga documentos en la solicitud")
async def cargar(exp_id: int, tipo: str,
                 archivos: list[UploadFile] = File(...),
                 usuario: dict = Depends(carga_documentos),
                 db: Session = Depends(get_db)) -> list[dict]:
    """
    Guarda uno o varios archivos con su propio nombre.

    No se reemplaza nada: dos avaluos de la misma garantia son dos documentos, y
    el almacenamiento desambigua el nombre si se repite. Devuelve la lista
    completa ya actualizada, que es lo que la pantalla vuelve a pintar.
    """
    _validar_tipo(tipo)
    registro = _expediente(tipo, exp_id, db)
    documento, nombre = _identidad(tipo, registro)
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for archivo in archivos:
        contenido = await archivo.read()
        if not contenido:
            raise HTTPException(status_code=422,
                                detail=f"El archivo {archivo.filename!r} llegó vacío.")
        if len(contenido) > LIMITE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"{archivo.filename!r} supera el límite de "
                       f"{LIMITE_BYTES // (1024 * 1024)} MB por archivo.")

        guardado = StorageService.save_client_documents(
            [_Subida(archivo.filename or "documento", contenido)], documento, nombre)
        escritos = guardado.get("guardados") or []
        if not escritos:
            errores = guardado.get("errores") or []
            motivo = errores[0][1] if errores else "el almacenamiento lo rechazó"
            raise HTTPException(status_code=422,
                                detail=f"No se pudo guardar {archivo.filename!r}: {motivo}")

        DocumentoExpedienteDAO.create(
            expediente_id=exp_id, tipo=tipo, file_name=escritos[0],
            carpeta=guardado.get("carpeta", ""), tamano_bytes=len(contenido),
            cargado_por=usuario["user"], fecha=ahora, session=db)

    db.commit()
    return DocumentoExpedienteDAO.get_by_expediente(exp_id, tipo, session=db)


@router.get("/{tipo}/{exp_id}/documentos/{doc_id}/descargar",
            summary="Descarga un documento de la solicitud")
def descargar(exp_id: int, tipo: str, doc_id: int,
              _usuario: dict = Depends(ver_documentos),
              db: Session = Depends(get_db)) -> StreamingResponse:
    """El archivo tal cual se cargó, con su nombre original."""
    _validar_tipo(tipo)
    registro = _expediente(tipo, exp_id, db)
    documento = _documento_de(exp_id, tipo, doc_id, db)

    cedula, nombre = _identidad(tipo, registro)
    contenido = StorageService.get_file_bytes(cedula, nombre, documento["file_name"])
    if contenido is None:
        raise HTTPException(
            status_code=404,
            detail="El registro existe pero el archivo no está en el repositorio.")

    # El nombre viaja en RFC 5987: los acentos no sobreviven a una cabecera
    # ASCII y el navegador guardaria el archivo con el nombre destrozado.
    nombre_archivo = quote(documento["file_name"])
    return StreamingResponse(
        io.BytesIO(contenido),
        media_type="application/octet-stream",
        headers={"Content-Disposition":
                 f"attachment; filename*=UTF-8''{nombre_archivo}"})


@router.post("/{tipo}/{exp_id}/documentos/{doc_id}/sincronizar",
             response_model=DocumentoOperacion,
             summary="Sincroniza un documento de la solicitud con SharePoint")
def sincronizar(exp_id: int, tipo: str, doc_id: int,
                _usuario: dict = Depends(carga_documentos),
                db: Session = Depends(get_db)) -> dict:
    """
    Sube un unico archivo al SharePoint del cliente y marca su registro.

    Va documento a documento, igual que la sincronizacion del repositorio KYC:
    un fallo de red en uno no debe dejar a los demas en un estado que no se
    corresponde con lo que hay al otro lado.

    La carpeta destino es la del cliente —«{documento} {nombre}»—, la misma que
    usa su expediente KYC, de modo que Legal encuentre en un solo sitio todo lo
    del mismo titular.
    """
    _validar_tipo(tipo)
    registro = _expediente(tipo, exp_id, db)
    documento = _documento_de(exp_id, tipo, doc_id, db)

    sp = SharePointService()
    if not sp.esta_configurado():
        raise HTTPException(
            status_code=503,
            detail="SharePoint no está configurado. Faltan estas variables de "
                   "entorno: " + ", ".join(sp.faltantes()))

    cedula, nombre = _identidad(tipo, registro)
    contenido = StorageService.get_file_bytes(cedula, nombre, documento["file_name"])
    if contenido is None:
        raise HTTPException(
            status_code=404,
            detail=f"No se pudo leer {documento['file_name']} del repositorio.")

    try:
        sp.upload_file(contenido, documento["file_name"], f"{cedula} {nombre}".strip())
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error al sincronizar {documento['file_name']}: {e}") from e

    DocumentoExpedienteDAO.update_sync_status(
        doc_id, SYNC_OK, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), session=db)
    db.commit()
    return _documento_de(exp_id, tipo, doc_id, db)


@router.delete("/{tipo}/{exp_id}/documentos/{doc_id}", status_code=204,
               summary="Retira un documento de la solicitud")
def retirar(exp_id: int, tipo: str, doc_id: int,
            _usuario: dict = Depends(carga_documentos),
            db: Session = Depends(get_db)) -> None:
    """Baja logica: el archivo se conserva, pero deja de ofrecerse."""
    _validar_tipo(tipo)
    _expediente(tipo, exp_id, db)
    _documento_de(exp_id, tipo, doc_id, db)
    DocumentoExpedienteDAO.delete(doc_id, session=db)
    db.commit()


def _documento_de(exp_id: int, tipo: str, doc_id: int, db: Session) -> dict:
    """El documento, siempre que pertenezca a esta solicitud."""
    documento = DocumentoExpedienteDAO.get_documento(doc_id, session=db)
    if not documento or documento["expediente_id"] != exp_id \
            or documento["tipo_expediente"] != tipo:
        raise HTTPException(status_code=404,
                            detail="El documento no pertenece a esta solicitud.")
    return documento


def _validar_tipo(tipo: str) -> None:
    if tipo not in ("corp", "auto"):
        raise HTTPException(status_code=422,
                            detail="Línea de producto no reconocida: use 'corp' o 'auto'.")
