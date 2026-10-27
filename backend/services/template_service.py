"""
Renderizado de los componentes estáticos de la interfaz con Jinja2.

Sustituye la concatenación de HTML con f-strings dentro de las vistas. Solo
produce marcado de presentación: los widgets interactivos siguen siendo nativos
de Streamlit, de modo que ninguna plantilla contiene formularios ni campos de
entrada.
"""

import os

from jinja2 import Environment, FileSystemLoader, select_autoescape

# `templates/` cuelga de la raíz del proyecto, hermana de `services/`
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")


def _filtro_moneda(valor, decimales=2):
    """Formatea un importe como `$1,234.56`, tolerando valores no numéricos."""
    try:
        return f"${float(valor):,.{decimales}f}"
    except (TypeError, ValueError):
        return "$0.00"


def _filtro_monto(valor, decimales=2):
    """Importe sin símbolo: la moneda se antepone aparte en las tarjetas."""
    try:
        return f"{float(valor):,.{decimales}f}"
    except (TypeError, ValueError):
        return "0.00"


def _filtro_numero(valor, decimales=2):
    try:
        return f"{float(valor):,.{decimales}f}"
    except (TypeError, ValueError):
        return str(valor)


class TemplateService:
    """Entorno Jinja2 del proyecto y punto único de renderizado por nombre."""

    _env = None

    @classmethod
    def get_environment(cls) -> Environment:
        """
        Entorno Jinja2 configurado, creado una sola vez por proceso.

        El autoescapado está activo: el contenido que ya es HTML —distintivos,
        iconos SVG— debe marcarse con `|safe` en la plantilla.
        """
        if cls._env is None:
            env = Environment(
                loader=FileSystemLoader(TEMPLATES_DIR, encoding="utf-8"),
                autoescape=select_autoescape(["html", "xml"]),
                trim_blocks=True,
                lstrip_blocks=True,
            )
            env.filters["moneda"] = _filtro_moneda
            env.filters["monto"] = _filtro_monto
            env.filters["numero"] = _filtro_numero
            cls._env = env
        return cls._env

    @classmethod
    def render(cls, plantilla: str, /, **contexto) -> str:
        """
        Renderiza una plantilla de `templates/` y devuelve el HTML resultante.

        El nombre de la plantilla es un parámetro solo posicional: así el
        contexto puede usar cualquier clave —`nombre`, `titulo`, `texto`— sin
        colisionar con la firma del método.

        Args:
            plantilla: nombre del archivo, por ejemplo `client_card.html`.
            **contexto: variables disponibles dentro de la plantilla.

        Raises:
            jinja2.TemplateNotFound: si la plantilla no existe.
        """
        return cls.get_environment().get_template(plantilla).render(**contexto)

    @classmethod
    def styles(cls) -> str:
        """Hoja de estilos de los componentes, para inyectar una vez por vista."""
        return cls.render("_styles.html")

    @classmethod
    def badge(cls, texto, bg, fg, dot) -> str:
        """Distintivo con punto de color, equivalente a `utils._dot_badge`."""
        return cls.render("status_badge.html", text=texto, bg=bg, fg=fg, dot=dot)

    @classmethod
    def listar_plantillas(cls) -> list:
        """Nombres de las plantillas disponibles; útil para diagnóstico."""
        return sorted(cls.get_environment().list_templates())
