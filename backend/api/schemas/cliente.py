"""Esquemas de `clientes` y `documentos_cliente`."""

from .base import Entero, ModeloKFG, Texto


class Cliente(ModeloKFG):
    """Cliente del registro KYC. Refleja las 19 columnas de `clientes`."""

    id: Entero = None
    fecha_registro: Texto = None
    tipo: Texto = "Natural"
    nombre: Texto = None
    cedula_rif: Texto = None
    fecha_nacimiento: Texto = None
    nacionalidad: Texto = "Venezolana"
    telefono: Texto = None
    email: Texto = None
    direccion: Texto = None
    actividad_economica: Texto = None

    # Representante legal (solo personas jurídicas)
    nombre_rep: Texto = None
    cedula_rep: Texto = None
    cargo_rep: Texto = None

    # Checklist documental serializado como JSON y estado del expediente KYC
    docs_json: Texto = "{}"
    kyc_status: Texto = "Prospecto"
    obs_kyc: Texto = None
    kyc_aprobado_por: Texto = None
    kyc_fecha: Texto = None


class DocumentoCliente(ModeloKFG):
    """
    Archivo del repositorio documental de un cliente.

    `doc_name` identifica el requisito del checklist al que corresponde y queda
    vacío en las cargas libres; `sp_sync_status` es el estado frente a SharePoint.
    """

    id: Entero = None
    cliente_id: int
    doc_name: Texto = None
    file_name: str
    carpeta: Texto = None
    fecha_carga: Texto = None
    fecha_sync: Texto = None
    sp_sync_status: str = "No Sincronizado"
