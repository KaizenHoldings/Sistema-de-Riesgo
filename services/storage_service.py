"""
Capa de almacenamiento de documentos de clientes.

Toda la manipulación de bytes vive aquí: las vistas nunca escriben archivos
directamente. El proveedor se selecciona con la variable de entorno
`STORAGE_PROVIDER` ('local' por defecto, 'sharepoint' pendiente de implementar),
y la raíz de almacenamiento con `KFG_BASE_STORAGE_PATH`.

La resolución de rutas usa exclusivamente el módulo `os` para garantizar
compatibilidad entre plataformas.
"""

import os
import re
import unicodedata

from dotenv import load_dotenv

load_dotenv()

# Raíz del proyecto (carpeta que contiene route.py), independiente del cwd
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Carpeta contenedora de todos los expedientes documentales
CLIENTS_DIRNAME = "clients"

# Caracteres no admitidos en nombres de archivo/carpeta de Windows
_INVALID_CHARS = r'<>:"/\\|?*'

# Variables de entorno que requerirá la integración con Microsoft Graph
SHAREPOINT_ENV_VARS = (
    "GRAPH_TENANT_ID",
    "GRAPH_CLIENT_ID",
    "GRAPH_CLIENT_SECRET",
    "SHAREPOINT_SITE_ID",
    "SHAREPOINT_DRIVE_ID",
)


def _base_storage_path() -> str:
    """
    Raíz de almacenamiento configurable vía `KFG_BASE_STORAGE_PATH`.

    Por defecto '.', es decir la raíz del proyecto. Una ruta relativa se ancla a
    la raíz del proyecto y no al directorio de trabajo, para que el destino no
    dependa de desde dónde se lance la aplicación. Una ruta absoluta se respeta
    tal cual, lo que permite apuntar a una unidad de red o a un volumen externo.
    """
    base = (os.getenv("KFG_BASE_STORAGE_PATH", ".") or ".").strip() or "."
    if not os.path.isabs(base):
        base = os.path.join(PROJECT_ROOT, base)
    return os.path.abspath(base)


def _sanitize(value: str, fallback: str = "sin_dato", max_len: int = 120) -> str:
    """Normaliza un fragmento de ruta: sin separadores, sin caracteres ilegales."""
    text = str(value or "").strip()
    # Neutraliza caracteres de control y separadores de ruta
    text = unicodedata.normalize("NFC", text)
    text = "".join(ch for ch in text if ord(ch) >= 32)
    text = re.sub(f"[{re.escape(_INVALID_CHARS)}]", "_", text)
    # Windows no admite nombres terminados en punto o espacio
    text = text.strip(" .")
    text = re.sub(r"\s+", " ", text)
    if not text:
        return fallback
    return text[:max_len].strip(" .") or fallback


def _dentro_de(base: str, ruta: str) -> bool:
    """True si `ruta` queda estrictamente dentro de `base` (anti path traversal)."""
    base_n = os.path.normcase(os.path.realpath(base))
    ruta_n = os.path.normcase(os.path.realpath(ruta))
    return ruta_n.startswith(base_n + os.sep)


def _unique_path(directory: str, filename: str) -> str:
    """Evita sobrescribir: agrega sufijo incremental si el nombre ya existe."""
    destino = os.path.join(directory, filename)
    if not os.path.exists(destino):
        return destino
    raiz, extension = os.path.splitext(filename)
    contador = 1
    while True:
        candidato = os.path.join(directory, f"{raiz} ({contador}){extension}")
        if not os.path.exists(candidato):
            return candidato
        contador += 1


class StorageService:
    """Punto único de entrada para persistir documentos de clientes."""

    @staticmethod
    def get_provider() -> str:
        """Proveedor activo, en minúsculas. 'local' si la variable no está definida."""
        return os.getenv("STORAGE_PROVIDER", "local").strip().lower()

    @staticmethod
    def save_client_documents(files, cedula, nombre):
        """
        Persiste una lista de `UploadedFile` de Streamlit para un cliente.

        Args:
            files: lista de objetos UploadedFile (o uno solo).
            cedula: C.I. / RIF del cliente.
            nombre: nombre o razón social del cliente.

        Returns:
            dict con las claves:
                provider  — proveedor utilizado ('local' | 'sharepoint')
                carpeta   — ruta destino en formato legible
                guardados — lista de nombres de archivo escritos
                errores   — lista de (nombre_archivo, motivo) que no se pudieron guardar

        Raises:
            ValueError: si no se recibe ningún archivo.
            NotImplementedError: si el proveedor configurado aún no está implementado.
        """
        if files is None:
            files = []
        if not isinstance(files, (list, tuple)):
            files = [files]
        files = [f for f in files if f is not None]

        if not files:
            raise ValueError("No se recibió ningún archivo para guardar.")

        provider = StorageService.get_provider()

        if provider == "local":
            return StorageService._save_local(files, cedula, nombre)
        if provider == "sharepoint":
            return StorageService._save_sharepoint(files, cedula, nombre)

        raise NotImplementedError(
            f"STORAGE_PROVIDER='{provider}' no es un proveedor reconocido. "
            f"Valores admitidos: 'local', 'sharepoint'."
        )

    @staticmethod
    def save_single_document(file, cedula, nombre, doc_name):
        """
        Persiste UN archivo asociado a un ítem concreto del checklist KYC.

        El archivo se renombra exactamente como `doc_name`, conservando de forma
        dinámica la extensión del archivo original. Si ya existía un documento
        para ese ítem, se reemplaza (es la versión vigente de ese requisito).

        Args:
            file: objeto UploadedFile de Streamlit.
            cedula: C.I. / RIF del cliente.
            nombre: nombre o razón social del cliente.
            doc_name: nombre del ítem del checklist (p. ej. "RIF personal").

        Returns:
            dict con las claves:
                provider      — proveedor utilizado
                carpeta       — ruta destino en formato legible
                archivo       — nombre final del archivo escrito
                ruta_absoluta — ruta absoluta de la carpeta del cliente

        Raises:
            ValueError: si no se recibe archivo o `doc_name` viene vacío.
            NotImplementedError: si el proveedor configurado aún no está implementado.
        """
        if file is None:
            raise ValueError("No se recibió ningún archivo para guardar.")
        if not str(doc_name or "").strip():
            raise ValueError("Se requiere el nombre del documento (doc_name).")

        provider = StorageService.get_provider()

        if provider == "local":
            return StorageService._save_single_local(file, cedula, nombre, doc_name)
        if provider == "sharepoint":
            # El placeholder comparte contrato: aún no implementado.
            return StorageService._save_sharepoint([file], cedula, nombre)

        raise NotImplementedError(
            f"STORAGE_PROVIDER='{provider}' no es un proveedor reconocido. "
            f"Valores admitidos: 'local', 'sharepoint'."
        )

    @staticmethod
    def get_document_file(cedula, nombre, doc_name):
        """
        Recupera el documento ya almacenado para un ítem del checklist.

        Busca el archivo cuyo nombre coincide con `doc_name` sin importar la
        extensión con la que se guardó.

        Returns:
            tuple(bytes, str) con el contenido y el nombre completo del archivo,
            o None si no existe (o si el proveedor activo aún no soporta lectura).
        """
        if not str(doc_name or "").strip():
            return None

        provider = StorageService.get_provider()

        if provider == "local":
            return StorageService._get_document_local(cedula, nombre, doc_name)

        # SharePoint aún no implementa lectura: se degrada a "sin archivo" en vez
        # de romper el render de la vista.
        return None

    @staticmethod
    def list_client_documents(cedula, nombre):
        """
        Lista los archivos almacenados para un cliente.

        Returns:
            list[str] con los nombres de archivo, ordenados alfabéticamente.
            Lista vacía si la carpeta no existe o el proveedor no soporta lectura.
        """
        provider = StorageService.get_provider()

        if provider == "local":
            base_dir = StorageService._client_dir(cedula, nombre)
            if not os.path.isdir(base_dir):
                return []
            try:
                return sorted(
                    n for n in os.listdir(base_dir)
                    if os.path.isfile(os.path.join(base_dir, n))
                )
            except Exception:
                return []

        # SharePoint aún no implementa listado: se degrada a lista vacía.
        return []

    @staticmethod
    def get_file_bytes(cedula, nombre, file_name):
        """
        Devuelve los bytes de un archivo concreto de la carpeta del cliente,
        buscándolo por su nombre exacto.

        Returns:
            bytes, o None si no existe o el proveedor no soporta lectura.
        """
        if not str(file_name or "").strip():
            return None

        provider = StorageService.get_provider()
        if provider != "local":
            return None

        base_dir = StorageService._client_dir(cedula, nombre)
        if not os.path.isdir(base_dir):
            return None

        # Solo el nombre base: nunca se acepta un componente de ruta
        limpio = _sanitize(os.path.basename(str(file_name).replace("\\", "/")), "")
        if not limpio:
            return None

        destino = os.path.join(base_dir, limpio)
        if not _dentro_de(base_dir, destino) or not os.path.isfile(destino):
            return None

        try:
            with open(destino, "rb") as entrada:
                return entrada.read()
        except Exception:
            return None

    # ── Proveedor: disco local ────────────────────────────────────────────
    @staticmethod
    def _client_dir(cedula, nombre, create=False):
        """
        Ruta absoluta de la carpeta de un cliente:
        `{KFG_BASE_STORAGE_PATH}/clients/{cedula} {nombre}`.

        Con `create=True` genera todo el árbol de carpetas necesario.
        """
        carpeta_cliente = StorageService._client_dirname(cedula, nombre)
        destino = os.path.abspath(
            os.path.join(_base_storage_path(), CLIENTS_DIRNAME, carpeta_cliente))
        if create:
            os.makedirs(destino, exist_ok=True)
        return destino

    @staticmethod
    def _client_dirname(cedula, nombre):
        """Nombre saneado de la carpeta del cliente: `{cedula} {nombre}`."""
        return f"{_sanitize(cedula, 'sin_documento')} {_sanitize(nombre, 'sin_nombre')}"

    @staticmethod
    def _get_document_local(cedula, nombre, doc_name):
        """Localiza `{doc_name}.*` dentro de la carpeta del cliente y lo lee."""
        base_dir = StorageService._client_dir(cedula, nombre)
        if not os.path.isdir(base_dir):
            return None

        objetivo = _sanitize(doc_name, "documento")

        for entrada in sorted(os.listdir(base_dir)):
            ruta = os.path.join(base_dir, entrada)
            if not os.path.isfile(ruta):
                continue
            # Coincide el nombre sin extensión, o el nombre completo si se guardó sin ella
            raiz = os.path.splitext(entrada)[0]
            if raiz != objetivo and entrada != objetivo:
                continue

            # Guarda de seguridad: no seguir enlaces fuera del directorio del cliente
            if not _dentro_de(base_dir, ruta):
                continue

            try:
                with open(ruta, "rb") as fichero:
                    return fichero.read(), entrada
            except Exception:
                return None

        return None

    @staticmethod
    def _save_single_local(file, cedula, nombre, doc_name):
        """
        Escribe un documento del checklist en `{base}/clients/{cedula} {nombre}/`
        con el nombre `{doc_name}{extensión original}`.
        """
        carpeta_cliente = StorageService._client_dirname(cedula, nombre)
        base_dir = StorageService._client_dir(cedula, nombre, create=True)

        # Extensión dinámica tomada del archivo original
        nombre_original = getattr(file, "name", "") or ""
        extension = os.path.splitext(str(nombre_original).replace("\\", "/"))[1]
        extension = _sanitize(extension, "", max_len=12) if extension else ""
        if extension and not extension.startswith("."):
            extension = f".{extension}"

        archivo_final = f"{_sanitize(doc_name, 'documento')}{extension}"
        destino = os.path.join(base_dir, archivo_final)

        # Guarda de seguridad: el destino debe permanecer dentro de base_dir
        if not _dentro_de(base_dir, destino):
            raise ValueError("La ruta calculada queda fuera del directorio del cliente.")

        if hasattr(file, "getvalue"):
            contenido = file.getvalue()
        else:
            file.seek(0)
            contenido = file.read()

        # Cada ítem del checklist tiene un único archivo vigente: se eliminan las
        # versiones previas guardadas con otra extensión antes de escribir.
        objetivo = _sanitize(doc_name, "documento")
        nombre_destino = os.path.basename(destino)
        for previo in os.listdir(base_dir):
            ruta_previa = os.path.join(base_dir, previo)
            if not os.path.isfile(ruta_previa) or previo == nombre_destino:
                continue
            if os.path.splitext(previo)[0] == objetivo or previo == objetivo:
                try:
                    os.remove(ruta_previa)
                except Exception:
                    pass

        with open(destino, "wb") as salida:
            salida.write(contenido)

        return {
            "provider": "local",
            "carpeta": os.path.join(CLIENTS_DIRNAME, carpeta_cliente),
            "archivo": nombre_destino,
            "ruta_absoluta": base_dir,
        }

    @staticmethod
    def _save_local(files, cedula, nombre):
        """
        Escribe los archivos en `{base}/clients/{cedula} {nombre}/`.

        La carpeta se crea si no existe. Los nombres de archivo se sanean y se
        valida que la ruta resuelta no escape del directorio del cliente
        (protección contra path traversal).
        """
        carpeta_cliente = StorageService._client_dirname(cedula, nombre)
        base_dir = StorageService._client_dir(cedula, nombre, create=True)

        guardados, errores = [], []

        for f in files:
            nombre_original = getattr(f, "name", "") or "documento"
            # Solo el nombre base: descarta cualquier componente de ruta del cliente
            limpio = _sanitize(os.path.basename(str(nombre_original).replace("\\", "/")), "documento")

            try:
                destino = _unique_path(base_dir, limpio)

                # Guarda de seguridad: el destino debe permanecer dentro de base_dir
                if not _dentro_de(base_dir, destino):
                    errores.append((nombre_original, "ruta fuera del directorio del cliente"))
                    continue

                # Streamlit expone UploadedFile como BytesIO: getvalue() no consume el buffer
                if hasattr(f, "getvalue"):
                    contenido = f.getvalue()
                else:
                    f.seek(0)
                    contenido = f.read()

                with open(destino, "wb") as salida:
                    salida.write(contenido)

                guardados.append(os.path.basename(destino))
            except Exception as e:
                errores.append((nombre_original, str(e)))

        return {
            "provider": "local",
            "carpeta": os.path.join(CLIENTS_DIRNAME, carpeta_cliente),
            "ruta_absoluta": base_dir,
            "guardados": guardados,
            "errores": errores,
        }

    # ── Proveedor: SharePoint (pendiente) ─────────────────────────────────
    @staticmethod
    def _save_sharepoint(files, cedula, nombre):
        """
        Persistencia en SharePoint / OneDrive vía Microsoft Graph API.

        NO IMPLEMENTADO. Este método define el contrato y la configuración que
        necesitará la integración real; no simula ni falsea ninguna llamada.

        Flujo previsto una vez inyectado el token de Graph:

        1. Obtener token de aplicación (client credentials) contra
           `https://login.microsoftonline.com/{GRAPH_TENANT_ID}/oauth2/v2.0/token`
           con scope `https://graph.microsoft.com/.default`.
        2. Resolver o crear la carpeta destino `{cedula} {nombre}` dentro del
           drive configurado:
           `PATCH /sites/{SHAREPOINT_SITE_ID}/drives/{SHAREPOINT_DRIVE_ID}/root:/{ruta}`
        3. Subir cada archivo:
           - < 4 MB: `PUT /drives/{drive}/root:/{ruta}/{archivo}:/content`
           - >= 4 MB: sesión de carga reanudable vía `createUploadSession`.
        4. Devolver el mismo contrato que `_save_local` (provider, carpeta,
           guardados, errores) para que la vista no distinga el proveedor.

        Raises:
            NotImplementedError: siempre, hasta que se implemente la integración.
        """
        faltantes = [v for v in SHAREPOINT_ENV_VARS if not os.getenv(v)]
        detalle = (
            f" Faltan además estas variables de entorno: {', '.join(faltantes)}."
            if faltantes else
            " Las credenciales de Graph ya están configuradas; falta implementar el cliente HTTP."
        )
        raise NotImplementedError(
            "El proveedor 'sharepoint' aún no está implementado."
            f"{detalle} Use STORAGE_PROVIDER=local mientras tanto."
        )
