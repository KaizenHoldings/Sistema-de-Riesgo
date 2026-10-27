"""
Generación de actas en PDF.

Restituye el «Generar Acta» que vivía en la vista `evaluations_profile` de
Streamlit. El documento lo compone `DocumentReportService`, que no se toca: aquí
solo se localiza el expediente, se le pasa la fila y se devuelve el binario con
el nombre de archivo que usaba la interfaz anterior, `Acta_{cliente}.pdf`.
"""

import io
import re

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.dependencies import get_current_user
from database.daos_sqlserver import (ExpedienteAutomotrizDAO,
                                     ExpedienteCorporativoDAO)
from database.db_core_sqlserver import get_db
from services.document_service import DocumentReportService

router = APIRouter(prefix="/api/v1/reportes", tags=["Reportes"])

autenticado = Depends(get_current_user)

Tipo = Path(..., pattern="^(corp|auto)$",
            description="Línea de producto: 'corp' o 'auto'.")


def _nombre_archivo(cliente: str) -> str:
    """
    Nombre del adjunto, saneado.

    El nombre del cliente viaja en la cabecera `Content-Disposition`, así que se
    limpia de comillas, saltos y separadores de ruta antes de incrustarlo.
    """
    limpio = re.sub(r'[<>:"/\\|?*\r\n]+', "_", str(cliente or "").strip())
    limpio = re.sub(r"\s+", "_", limpio) or "expediente"
    return f"Acta_{limpio[:80]}.pdf"


@router.get("/expedientes/{tipo}/{exp_id}/acta",
            summary="Acta del expediente en PDF",
            responses={200: {"content": {"application/pdf": {}}}})
def acta(exp_id: int, tipo: str = Tipo, db: Session = Depends(get_db),
         _: dict = autenticado) -> StreamingResponse:
    """
    Acta de crédito del expediente, con el formato institucional de siempre.

    Cada línea de producto tiene su propia composición —la corporativa detalla
    garantías y cobertura, la automotriz el vehículo y la capacidad de pago—, tal
    y como las generaba la interfaz anterior.
    """
    dao = ExpedienteCorporativoDAO if tipo == "corp" else ExpedienteAutomotrizDAO
    expediente = dao.get_by_id(exp_id, session=db)
    if not expediente:
        raise HTTPException(status_code=404,
                            detail=f"No existe el expediente {tipo}/{exp_id}.")

    generar = (DocumentReportService.generar_pdf_corporativo if tipo == "corp"
               else DocumentReportService.generar_pdf_auto)

    try:
        contenido = generar(expediente)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo componer el acta del expediente {exp_id}: {e}") from e

    return StreamingResponse(
        io.BytesIO(contenido),
        media_type="application/pdf",
        headers={"Content-Disposition":
                 f'attachment; filename="{_nombre_archivo(expediente.get("cliente"))}"'},
    )


def _nombre_contrato(cliente: str) -> str:
    limpio = re.sub(r'[<>:"/\\|?*\r\n]+', "_", str(cliente or "").strip())
    limpio = re.sub(r"\s+", "_", limpio) or "cliente"
    return f"Contrato_{limpio[:80]}.pdf"


@router.get("/expedientes/{tipo}/{exp_id}/contrato",
            summary="Contrato de crédito del cliente en PDF",
            responses={200: {"content": {"application/pdf": {}}}})
def contrato(exp_id: int, tipo: str = Tipo, db: Session = Depends(get_db),
             _: dict = autenticado) -> StreamingResponse:
    """
    Contrato formal a nombre del cliente con las condiciones legales de la
    operación y el apartado para su suscripción y firma.
    """
    dao = ExpedienteCorporativoDAO if tipo == "corp" else ExpedienteAutomotrizDAO
    expediente = dao.get_by_id(exp_id, session=db)
    if not expediente:
        raise HTTPException(status_code=404,
                            detail=f"No existe el expediente {tipo}/{exp_id}.")

    generar = (DocumentReportService.generar_contrato_corporativo if tipo == "corp"
               else DocumentReportService.generar_contrato_auto)

    try:
        contenido = generar(expediente)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo componer el contrato del expediente {exp_id}: {e}") from e

    return StreamingResponse(
        io.BytesIO(contenido),
        media_type="application/pdf",
        headers={"Content-Disposition":
                 f'attachment; filename="{_nombre_contrato(expediente.get("cliente"))}"'},
    )

