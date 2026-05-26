"""
Jinja2 templating support for VayuAPI

Provides template rendering capabilities similar to FastAPI's Jinja2Templates.
"""

from typing import Any, Dict, Optional
from pathlib import Path
from starlette.responses import HTMLResponse
from starlette.requests import Request


class Jinja2Templates:
    """
    Jinja2 template renderer for VayuAPI.

    Example:
        ```python
        from vayuapi import VayuAPI, Request
        from vayuapi.templating import Jinja2Templates

        app = VayuAPI()
        templates = Jinja2Templates(directory="templates")

        @app.get("/")
        async def home(request: Request):
            return templates.TemplateResponse(
                "index.html",
                {"request": request, "title": "Home"}
            )
        ```
    """

    def __init__(
        self,
        directory: str = "templates",
        **env_options: Any
    ):
        """
        Initialize Jinja2 template engine.

        Args:
            directory: Directory containing templates
            **env_options: Additional Jinja2 Environment options
        """
        try:
            from jinja2 import Environment, FileSystemLoader, select_autoescape
        except ImportError:
            raise ImportError(
                "Jinja2 is required for template support. "
                "Install it with: pip install jinja2"
            )

        self.directory = Path(directory)

        # Set up Jinja2 environment with sensible defaults
        env_options.setdefault('autoescape', select_autoescape(['html', 'xml']))

        loader = FileSystemLoader(str(self.directory))
        self.env = Environment(loader=loader, **env_options)

    def get_template(self, name: str):
        """
        Get a template by name.

        Args:
            name: Template file name

        Returns:
            Jinja2 Template object
        """
        return self.env.get_template(name)

    def TemplateResponse(
        self,
        name: str,
        context: Dict[str, Any] = None,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: str = "text/html"
    ) -> HTMLResponse:
        """
        Render a template and return an HTML response.

        Args:
            name: Template file name
            context: Template context dictionary
            status_code: HTTP status code
            headers: Response headers
            media_type: Response media type

        Returns:
            HTMLResponse with rendered template
        """
        if context is None:
            context = {}

        template = self.get_template(name)
        content = template.render(context)

        return HTMLResponse(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type=media_type
        )

    def render_string(self, source: str, context: Dict[str, Any] = None) -> str:
        """
        Render a template from string.

        Args:
            source: Template source string
            context: Template context dictionary

        Returns:
            Rendered template string
        """
        if context is None:
            context = {}

        template = self.env.from_string(source)
        return template.render(context)


__all__ = ["Jinja2Templates"]
