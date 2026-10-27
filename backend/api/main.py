"""
Aplicación FastAPI de KFG Risk Architect.

Arranque:
    uvicorn api.main:app --host 0.0.0.0 --port 8000
    Documentación interactiva en http://localhost:8000/docs
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from api.routes import (amortization_routes, application_routes, auth_routes,
                        client_routes, collection_routes, dashboard_routes,
                        document_routes, documento_operacion_routes,
                        report_routes, risk_routes, system_routes,
                        workflow_routes)
from database.db_core_sqlserver import init_db

logger = logging.getLogger("api.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    auto_init = os.getenv("AUTO_INIT_DB", "true").lower() in ("true", "1", "yes")
    if auto_init:
        try:
            logger.info("Verificando/inicializando esquema de base de datos...")
            init_db()
            logger.info("Esquema de base de datos verificado con éxito.")
        except Exception as e:
            logger.error("Aviso al verificar base de datos durante el arranque: %s", e)
    yield


app = FastAPI(
    title="KFG Risk Architect API",
    version="1.1.0",
    description=(
        "Backend de KFG Risk Architect. Los motores financieros —scoring, "
        "indicadores, Altman Z-Score y amortización francesa— se sirven "
        "envolviendo los servicios existentes, sin reimplementar ninguna "
        "fórmula. Es el único backend de la plataforma: la interfaz de "
        "Next.js consume estas rutas y no queda ninguna capa de presentación "
        "en Python."
    ),
    contact={"name": "KFG Risk Architect"},
    lifespan=lifespan,
)

# Motores financieros
app.include_router(risk_routes.router)
app.include_router(amortization_routes.router)

# Dominio
app.include_router(auth_routes.router)
app.include_router(client_routes.router)
app.include_router(application_routes.router)
app.include_router(collection_routes.router)
app.include_router(workflow_routes.router)
app.include_router(system_routes.router)
app.include_router(document_routes.router)
app.include_router(documento_operacion_routes.router)
app.include_router(report_routes.router)
app.include_router(dashboard_routes.router)


@app.get("/health", tags=["Servicio"], summary="Comprobación de vida")
def health() -> dict:
    """Responde sin tocar la base: sirve para sondas de despliegue."""
    return {"estado": "ok", "version": app.version}
