"""
Rutas de cartera y cobranzas:
- Búsqueda universal de créditos y clientes.
- Consulta de tasa de cambio oficial del día (BCV).
- Resumen financiero detallado (mora, cuotas vencidas y liquidación anticipada).
- Procesamiento de Caja Mixta con validación de referencias únicas y motor de cascada legal.
- Emisión de recibos oficiales en PDF.
- Bitácora de gestiones, historial de cobros y módulo de arqueo diario.
"""

from datetime import date
import io
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, require_role
from api.schemas import GestionCobranza, PagoRecibido, PlanPago
from database.daos_sqlserver import (GestionCobranzaDAO, PagoRecibidoDAO,
                                     PlanPagoDAO)
from database.db_core_sqlserver import get_db
from services.collection_service import CollectionService

router = APIRouter(prefix="/api/v1/cobranza", tags=["Cobranza"], dependencies=[Depends(get_current_user)])
solo_cobranza = require_role("Cobranzas", "Superadmin")
acceso_cartera = require_role("Comité", "Cobranzas", "Superadmin")

TIPOS = ("corp", "auto")


def _validar_tipo(tipo: str) -> str:
    if tipo not in TIPOS:
        raise HTTPException(
            status_code=422,
            detail=f"Tipo de expediente no reconocido: {tipo!r}. Use 'corp' o 'auto'.")
    return tipo


# ── Modelos Pydantic para Caja Mixta y Arqueo ─────────────────────────
class MetodoPagoInput(BaseModel):
    tipo: str = Field(..., description="efectivo, transferencia, pago_movil, punto_venta")
    monto: float = Field(..., ge=0)
    moneda: str = Field("USD", description="USD, VES, COP")
    monto_recibido: float | None = None
    vuelto: float | None = None
    banco_origen: str | None = ""
    banco_destino: str | None = ""
    referencia: str | None = Field("", description="Número de referencia bancaria única")
    lote: str | None = Field("", description="Número de lote POS")
    codigo_aprobacion: str | None = Field("", description="Código de aprobación POS")
    tarjeta_ultimos_4: str | None = ""


class PagoMixtoInput(BaseModel):
    expediente_id: int
    tipo_expediente: str
    tasa_cambio: float = 1.0
    destino_abono_extra: str = Field("reducir_cuota", description="reducir_cuota o reducir_plazo")
    metodos: list[MetodoPagoInput]
    comprobante_url: str | None = ""
    observaciones: str | None = ""


class CierreArqueoInput(BaseModel):
    fecha: str | None = None
    efectivo_declarado_usd: float = 0.0
    efectivo_declarado_ves: float = 0.0
    pos_declarado_ves: float = 0.0
    transferencias_declarado_ves: float = 0.0
    observaciones: str | None = ""


# ── Búsqueda Universal y Tasa Oficial ─────────────────────────────────
@router.get("/tasas-cambio", summary="Tasa de cambio del día oficial del BCV")
def tasas_cambio(db: Session = Depends(get_db)) -> dict:
    """Devuelve la tasa oficial del día fijada para la jornada (inmodificable por el cajero)."""
    return CollectionService.obtener_tasa_cambio(session=db)


@router.get("/creditos/buscar", summary="Buscador universal de créditos")
def buscar_creditos(q: str = Query("", description="Cédula/RIF, nombre, contrato o código de crédito"),
                    db: Session = Depends(get_db)) -> list[dict]:
    return CollectionService.buscar_creditos(q=q, session=db)


@router.get("/creditos/pagados", summary="Listado consolidado y métricas de créditos pagados")
def creditos_pagados(db: Session = Depends(get_db)) -> dict:
    """Devuelve las métricas y la lista de todos los créditos totalmente cancelados / liquidados."""
    return CollectionService.obtener_creditos_pagados(session=db)


@router.get("/creditos/{tipo}/{exp_id}/finiquito/pdf", summary="Descargar Constancia Oficial de Finiquito y Solvencia en PDF")
def descargar_finiquito_pdf(tipo: str, exp_id: int, db: Session = Depends(get_db)) -> StreamingResponse:
    _validar_tipo(tipo)
    try:
        contenido = CollectionService.generar_finiquito_pdf(exp_id=exp_id, tipo=tipo, session=db)
        nombre = f"Solvencia_KFG_{tipo.upper()}_{exp_id:04d}.pdf"
        return StreamingResponse(
            io.BytesIO(contenido),
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename={quote(nombre)}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/creditos/{tipo}/{exp_id}/resumen-financiero", summary="Panel de Información Financiera")
def resumen_financiero(tipo: str, exp_id: int, db: Session = Depends(get_db)) -> dict:
    _validar_tipo(tipo)
    try:
        return CollectionService.obtener_resumen_financiero(exp_id=exp_id, tipo=tipo, session=db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Procesamiento de Pagos en Caja Mixta ──────────────────────────────
@router.post("/pagos/mixto", summary="Procesamiento del pago con Caja Mixta y Cascada Legal")
def procesar_pago_mixto(datos: PagoMixtoInput,
                        usuario: dict = Depends(solo_cobranza),
                        db: Session = Depends(get_db)) -> dict:
    _validar_tipo(datos.tipo_expediente)
    payload = datos.model_dump()
    payload["cajero"] = usuario.get("user") or "Caja"
    try:
        resultado = CollectionService.procesar_pago_mixto(payload, session=db)
        db.commit()
        return resultado
    except ValueError as e:
        db.rollback()
        msj = str(e)
        if "BLOQUEO DE SEGURIDAD" in msj:
            raise HTTPException(status_code=409, detail=msj)
        raise HTTPException(status_code=422, detail=msj)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Fallo al procesar el cobro: {e}")


@router.get("/recibos/{pago_id}/pdf", summary="Generador de recibo oficial de pago físico/digital")
def descargar_recibo_pdf(pago_id: int, db: Session = Depends(get_db)) -> StreamingResponse:
    try:
        contenido = CollectionService.generar_recibo_pdf(pago_id, session=db)
        nombre = f"Recibo_Pago_KFG_{pago_id:06d}.pdf"
        return StreamingResponse(
            io.BytesIO(contenido),
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename={quote(nombre)}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/expedientes/{tipo}/{exp_id}/pagos", summary="Historial de cobros del cliente")
def historial_pagos(tipo: str, exp_id: int, db: Session = Depends(get_db)) -> list[dict]:
    _validar_tipo(tipo)
    return CollectionService.obtener_historial_pagos(exp_id=exp_id, tipo=tipo, session=db)


# ── Módulo de Arqueo Diario ───────────────────────────────────────────
@router.get("/arqueo/hoy", summary="Módulo de arqueo diario: resumen de caja")
def arqueo_hoy(fecha: str | None = None,
               _usuario: dict = Depends(solo_cobranza),
               db: Session = Depends(get_db)) -> dict:
    return CollectionService.obtener_arqueo_diario(fecha=fecha, session=db)


@router.post("/arqueo/cierre", summary="Cierre formal de turno del cajero")
def cierre_arqueo(datos: CierreArqueoInput,
                  usuario: dict = Depends(solo_cobranza),
                  db: Session = Depends(get_db)) -> dict:
    payload = datos.model_dump()
    payload["cajero"] = usuario.get("user") or "Cajero"
    resultado = CollectionService.cerrar_arqueo_diario(payload, session=db)
    db.commit()
    return resultado


# ── Plan de pagos y Consultas Generales ───────────────────────────────
@router.get("/planes/{tipo}/{exp_id}", response_model=list[PlanPago],
            summary="Plan de pagos de un expediente")
def plan_expediente(tipo: str, exp_id: int,
                    db: Session = Depends(get_db)) -> list[dict]:
    _validar_tipo(tipo)
    return PlanPagoDAO.get_by_expediente(exp_id, tipo, session=db)


@router.get("/cuotas", response_model=list[PlanPago],
            summary="Cuotas paginadas de toda la cartera")
def cuotas(pagina: int = Query(1, ge=1),
           por_pagina: int = Query(50, ge=1, le=500),
           expediente_id: int | None = None,
           tipo: str | None = None,
           estado: str | None = None,
           db: Session = Depends(get_db)) -> list[dict]:
    if tipo is not None:
        _validar_tipo(tipo)
    return PlanPagoDAO.get_paginated(page=pagina, page_size=por_pagina,
                                     expediente_id=expediente_id, tipo=tipo,
                                     estado=estado, session=db)


@router.put("/cuotas/{plan_id}/pagada", status_code=204,
            summary="Marca una cuota como pagada")
def marcar_pagada(plan_id: int, _usuario: dict = Depends(solo_cobranza), db: Session = Depends(get_db)) -> None:
    PlanPagoDAO.mark_as_paid(plan_id, session=db)
    db.commit()


# ── Indicadores de Cartera ────────────────────────────────────────────
@router.get("/indicadores/aging", summary="Antigüedad de saldos vencidos")
def aging(fecha_referencia: str | None = None,
          db: Session = Depends(get_db)) -> dict:
    ref = fecha_referencia or date.today().strftime("%Y-%m-%d")
    return PlanPagoDAO.get_aging_buckets(ref, session=db)


@router.get("/indicadores/vencimientos", summary="Vencido y por vencer")
def vencimientos(fecha_referencia: str | None = None,
                 dias_proximos: int = Query(30, ge=1, le=365),
                 db: Session = Depends(get_db)) -> dict:
    ref = fecha_referencia or date.today().strftime("%Y-%m-%d")
    return PlanPagoDAO.get_resumen_vencimientos(ref, dias_proximos=dias_proximos,
                                                session=db)


@router.get("/indicadores/flujo", summary="Flujo mensual proyectado")
def flujo(fecha_desde: str, fecha_hasta: str,
          db: Session = Depends(get_db)) -> list[dict]:
    return PlanPagoDAO.get_flujo_mensual(fecha_desde, fecha_hasta, session=db)


@router.get("/vencidos", summary="Detalle de cuotas vencidas")
def vencidos(fecha_referencia: str | None = None,
             db: Session = Depends(get_db)) -> list[dict]:
    ref = fecha_referencia or date.today().strftime("%Y-%m-%d")
    return PlanPagoDAO.get_vencidos_detalle(ref, session=db)


# ── Gestiones de cobro ────────────────────────────────────────────────
@router.get("/gestiones", response_model=list[GestionCobranza],
            summary="Gestiones de cobro paginadas")
def gestiones(pagina: int = Query(1, ge=1),
              por_pagina: int = Query(25, ge=1, le=200),
              expediente_id: int | None = None,
              tipo: str | None = None,
              db: Session = Depends(get_db)) -> list[dict]:
    if tipo is not None:
        _validar_tipo(tipo)
    return GestionCobranzaDAO.get_paginated(page=pagina, page_size=por_pagina,
                                            expediente_id=expediente_id,
                                            tipo=tipo, session=db)


@router.post("/gestiones", response_model=GestionCobranza,
             status_code=status.HTTP_201_CREATED,
             summary="Registra una gestión de cobro")
def crear_gestion(datos: GestionCobranza,
                  _usuario: dict = Depends(solo_cobranza),
                  db: Session = Depends(get_db)) -> dict:
    _validar_tipo(datos.tipo_expediente)
    GestionCobranzaDAO.create(
        exp_id=datos.expediente_id, tipo=datos.tipo_expediente,
        fecha=datos.fecha or date.today().strftime("%Y-%m-%d"),
        tipo_gestion=datos.tipo_gestion or "Llamada",
        responsable=datos.responsable or "", resultado=datos.resultado or "",
        prox_accion=datos.proxima_accion or "", fecha_prox=datos.fecha_proxima or "",
        obs=datos.obs or "", session=db)
    db.commit()
    return datos.model_dump()


# ── Pagos tradicionales ───────────────────────────────────────────────
@router.post("/pagos", response_model=PagoRecibido,
             status_code=status.HTTP_201_CREATED,
             summary="Registra un pago recibido individual")
def crear_pago(datos: PagoRecibido, _usuario: dict = Depends(solo_cobranza), db: Session = Depends(get_db)) -> dict:
    _validar_tipo(datos.tipo_expediente)
    if (datos.monto or 0) <= 0:
        raise HTTPException(status_code=422,
                            detail="El monto del pago debe ser mayor que cero.")
    PagoRecibidoDAO.create(
        exp_id=datos.expediente_id, tipo=datos.tipo_expediente,
        fecha_pago=datos.fecha_pago or date.today().strftime("%Y-%m-%d"),
        monto=float(datos.monto), referencia=datos.referencia or "", session=db)
    db.commit()
    return datos.model_dump()


# ── Monitoreo en Tiempo Real y Auditoría ──────────────────────────────
@router.get("/ultimos-cobros", summary="Lista de últimos cobros recibidos para auditoría")
def ultimos_cobros(limite: int = Query(15, ge=1, le=100),
                   _usuario: dict = Depends(acceso_cartera),
                   db: Session = Depends(get_db)) -> list[dict]:
    return CollectionService.obtener_ultimos_cobros(limite=limite, session=db)


@router.get("/alertas-vencimientos", summary="Alertas de cobro preventivo y cuotas por vencer")
def alertas_vencimientos(dias: int = Query(30, ge=1, le=180),
                         limite: int = Query(25, ge=1, le=200),
                         _usuario: dict = Depends(acceso_cartera),
                         db: Session = Depends(get_db)) -> list[dict]:
    return CollectionService.obtener_alertas_vencimientos(dias_ventana=dias, limite=limite, session=db)

