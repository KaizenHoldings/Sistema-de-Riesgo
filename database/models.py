from dataclasses import dataclass
from typing import Optional

@dataclass
class Usuario:
    user: str
    password: str
    role: str

@dataclass
class ConfigParametro:
    clave: str
    valor: float

# Para las entidades más complejas, definimos las clases base
# Se recomienda usar kwargs o mapeo a diccionarios en las inserciones por la cantidad de columnas

@dataclass
class ExpedienteCorporativo:
    id: Optional[int] = None
    fecha: str = ""
    cliente: str = ""
    rif: str = ""
    monto: float = 0.0
    dictamen: str = "PENDIENTE"
    moneda: str = "USD"
    # ... otras decenas de campos. Para simplificar, los DAOs pueden recibir y devolver diccionarios / DataFrames
    # pero el modelo queda establecido como contrato.

@dataclass
class ExpedienteAutomotriz:
    id: Optional[int] = None
    fecha: str = ""
    cliente: str = ""
    cedula: str = ""
    monto: float = 0.0
    dictamen: str = "PENDIENTE"
    moneda: str = "USD"
    marca: str = ""
    modelo: str = ""
    anio: int = 0

@dataclass
class Cliente:
    id: Optional[int] = None
    fecha_registro: str = ""
    tipo: str = "Natural"
    nombre: str = ""
    cedula_rif: str = ""
    kyc_status: str = "Prospecto"

@dataclass
class PlanPago:
    id: Optional[int] = None
    expediente_id: int = 0
    tipo_expediente: str = ""
    periodo: int = 0
    fecha_pago: str = ""
    cuota: float = 0.0
    capital: float = 0.0
    interes: float = 0.0
    saldo: float = 0.0
    estado: str = "PENDIENTE"

@dataclass
class GestionCobranza:
    id: Optional[int] = None
    expediente_id: int = 0
    tipo_expediente: str = ""
    fecha: str = ""
    tipo_gestion: str = ""
    responsable: str = ""
    resultado: str = ""
    proxima_accion: str = ""
    fecha_proxima: str = ""
    obs: str = ""
