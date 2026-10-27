"""
Sincronización de documentos de clientes con SharePoint vía Microsoft Graph.

Autenticación por client credentials (aplicación daemon, sin usuario) y subida
de archivos al drive configurado. Toda la configuración se toma de variables de
entorno; no hay credenciales en el código.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

# Endpoints de Microsoft
TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
GRAPH_UPLOAD_URL = "https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{ruta}:/content"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"

# Tiempo máximo de espera de cada llamada HTTP, en segundos
TIMEOUT_TOKEN = 20
TIMEOUT_UPLOAD = 120


def _env(*nombres):
    """
    Primera variable de entorno no vacía de las indicadas.

    Se aceptan varios nombres porque el proyecto ya documentaba las credenciales
    con prefijo (`GRAPH_TENANT_ID`, `SHAREPOINT_DRIVE_ID`) y se admite también la
    forma corta.
    """
    for nombre in nombres:
        valor = (os.getenv(nombre) or "").strip()
        if valor:
            return valor
    return ""


class SharePointService:
    """Cliente mínimo de Microsoft Graph para subir documentos de clientes."""

    def __init__(self):
        self.tenant_id = _env("TENANT_ID", "GRAPH_TENANT_ID")
        self.client_id = _env("CLIENT_ID", "GRAPH_CLIENT_ID")
        self.client_secret = _env("CLIENT_SECRET", "GRAPH_CLIENT_SECRET")
        self.drive_id = _env("DRIVE_ID", "SHAREPOINT_DRIVE_ID")

    # ── Configuración ─────────────────────────────────────────────────
    def faltantes(self):
        """Nombres de las credenciales que no están configuradas."""
        requeridas = {
            "TENANT_ID": self.tenant_id,
            "CLIENT_ID": self.client_id,
            "CLIENT_SECRET": self.client_secret,
            "DRIVE_ID": self.drive_id,
        }
        return [n for n, v in requeridas.items() if not v]

    def esta_configurado(self) -> bool:
        return not self.faltantes()

    # ── Autenticación ─────────────────────────────────────────────────
    def _get_access_token(self):
        """
        Obtiene un token de aplicación contra Azure AD (client credentials).

        Returns:
            str: el `access_token` devuelto por Microsoft.

        Raises:
            RuntimeError: si faltan credenciales o la respuesta no trae token.
            requests.HTTPError: si Azure AD responde con un código de error.
        """
        faltan = self.faltantes()
        if faltan:
            raise RuntimeError(
                "Faltan variables de entorno para SharePoint: " + ", ".join(faltan))

        datos = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "scope": GRAPH_SCOPE,
        }
        cabeceras = {"Content-Type": "application/x-www-form-urlencoded"}

        resp = requests.post(
            TOKEN_URL.format(tenant_id=self.tenant_id),
            data=datos, headers=cabeceras, timeout=TIMEOUT_TOKEN)
        resp.raise_for_status()

        token = (resp.json() or {}).get("access_token")
        if not token:
            raise RuntimeError("Azure AD no devolvió un access_token.")
        return token

    # ── Subida de archivos ────────────────────────────────────────────
    def upload_file(self, file_bytes, filename, folder_path, access_token=None):
        """
        Sube un archivo al drive de SharePoint mediante una carga simple.

        Args:
            file_bytes: contenido binario del archivo.
            filename: nombre con el que se guardará en SharePoint.
            folder_path: carpeta destino relativa a la raíz del drive.
            access_token: token ya obtenido; si se omite, se solicita uno nuevo.
                Permite reutilizar el mismo token en una sincronización de varios
                archivos en lugar de pedir uno por documento.

        Returns:
            dict con la respuesta de Graph (id, name, webUrl, size...).

        Raises:
            requests.HTTPError: si Graph responde con un código de error.
            RuntimeError: si faltan credenciales.
        """
        token = access_token or self._get_access_token()

        ruta = f"{str(folder_path).strip('/')}/{filename}"
        cabeceras = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream",
        }

        resp = requests.put(
            GRAPH_UPLOAD_URL.format(drive_id=self.drive_id, ruta=ruta),
            headers=cabeceras, data=file_bytes, timeout=TIMEOUT_UPLOAD)
        resp.raise_for_status()

        try:
            return resp.json()
        except ValueError:
            return {"name": filename, "status_code": resp.status_code}
