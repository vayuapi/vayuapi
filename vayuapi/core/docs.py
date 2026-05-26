"""
OpenAPI documentation generation for VayuAPI
Provides Swagger UI and ReDoc endpoints
"""

from typing import Dict, List, Any, Optional, get_type_hints
from starlette.responses import HTMLResponse
from starlette.routing import Route
from pydantic import BaseModel
import inspect


# Note: JSONResponse is imported from application module where needed


class OpenAPIGenerator:
    """
    Generates OpenAPI 3.0 specification from VayuAPI routes.
    """

    def __init__(self, app):
        self.app = app
        self.openapi_schema = None

    def generate_schema(self) -> Dict[str, Any]:
        """Generate OpenAPI schema."""
        if self.openapi_schema:
            return self.openapi_schema

        schema = {
            "openapi": "3.0.3",
            "info": {
                "title": self.app.title,
                "version": self.app.version,
                "description": self.app.description or "",
            },
            "paths": {},
            "components": {
                "schemas": {}
            }
        }

        # Generate paths from routes
        for route in self.app._routes:
            # Skip websocket routes from OpenAPI docs
            if route.get("type") == "websocket":
                continue

            path = route.get("path", "")
            methods = route.get("methods", ["GET"])
            # Use original_endpoint if available, otherwise use endpoint
            endpoint = route.get("original_endpoint") or route.get("endpoint")
            name = route.get("name", "")

            if path not in schema["paths"]:
                schema["paths"][path] = {}

            # Get function info
            func_doc = inspect.getdoc(endpoint) or ""
            func_signature = inspect.signature(endpoint)

            # Extract parameters and response info from function
            parameters = []
            request_body = None

            # Check function parameters for Pydantic models
            for param_name, param in func_signature.parameters.items():
                if param_name in ["request", "websocket"]:
                    continue

                # Check if parameter is a Pydantic model (for request body)
                param_annotation = param.annotation
                if param_annotation != inspect.Parameter.empty:
                    is_pydantic_model = False

                    # Try multiple ways to detect Pydantic model
                    try:
                        # Method 1: Check if it's a subclass of BaseModel
                        if isinstance(param_annotation, type) and issubclass(param_annotation, BaseModel):
                            is_pydantic_model = True
                    except (TypeError, AttributeError):
                        pass

                    # Method 2: Check for model_json_schema method (Pydantic v2)
                    if not is_pydantic_model and hasattr(param_annotation, 'model_json_schema'):
                        is_pydantic_model = True

                    # Method 3: Check for __pydantic_model__ attribute
                    if not is_pydantic_model and hasattr(param_annotation, '__pydantic_model__'):
                        is_pydantic_model = True

                    if is_pydantic_model:
                        # It's a Pydantic model - use as request body
                        request_body = {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": self._pydantic_to_schema(param_annotation)
                                }
                            }
                        }
                    else:
                        # Path or query parameter
                        param_in = "path" if f"{{{param_name}}}" in path else "query"
                        parameters.append({
                            "name": param_name,
                            "in": param_in,
                            "required": param_in == "path",
                            "schema": {"type": self._python_type_to_openapi(param_annotation)}
                        })

            for method in methods:
                method_lower = method.lower()

                operation = {
                    "summary": name or func_doc.split('\n')[0] if func_doc else f"{method} {path}",
                    "description": func_doc,
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            }
                        }
                    }
                }

                if parameters:
                    operation["parameters"] = parameters

                if request_body:
                    operation["requestBody"] = request_body

                schema["paths"][path][method_lower] = operation

        self.openapi_schema = schema
        return schema

    def _pydantic_to_schema(self, model: type[BaseModel]) -> Dict[str, Any]:
        """Convert Pydantic model to OpenAPI schema."""
        try:
            # Use Pydantic's built-in schema generation (Pydantic v2)
            schema = model.model_json_schema()

            # Remove the title and add to components if it has definitions
            if '$defs' in schema:
                # Move definitions to components/schemas
                for def_name, def_schema in schema['$defs'].items():
                    if def_name not in self.openapi_schema['components']['schemas']:
                        self.openapi_schema['components']['schemas'][def_name] = def_schema
                del schema['$defs']

            return schema
        except AttributeError:
            # Fallback for Pydantic v1 or if model_json_schema doesn't exist
            try:
                return model.schema()
            except Exception:
                return {"type": "object"}
        except Exception:
            return {"type": "object"}

    def _python_type_to_openapi(self, python_type) -> str:
        """Convert Python type to OpenAPI type."""
        type_mapping = {
            int: "integer",
            str: "string",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }

        # Handle Optional types
        if hasattr(python_type, '__origin__'):
            if python_type.__origin__ is list:
                return "array"
            if python_type.__origin__ is dict:
                return "object"

        return type_mapping.get(python_type, "string")


def get_swagger_ui_html(openapi_url: str, title: str) -> str:
    """Generate Swagger UI HTML."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title} - Swagger UI</title>
        <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
        <link rel="icon" type="image/ico" href="http://vayuapi.amrits.in/ingue/2.ico">
        <style>
            html {{ box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }}
            *, *:before, *:after {{ box-sizing: inherit; }}
            body {{ margin:0; padding:0; }}
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
        <script>
            window.onload = function() {{
                window.ui = SwaggerUIBundle({{
                    url: "{openapi_url}",
                    dom_id: '#swagger-ui',
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIStandalonePreset
                    ],
                    layout: "BaseLayout",
                    deepLinking: true,
                    showExtensions: true,
                    showCommonExtensions: true
                }})
            }}
        </script>
    </body>
    </html>
    """


def get_redoc_html(openapi_url: str, title: str) -> str:
    """Generate ReDoc HTML."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title} - ReDoc</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="icon" type="image/png" href="https://fastapi.tiangolo.com/img/favicon.png">
        <style>
            body {{ margin: 0; padding: 0; }}
        </style>
    </head>
    <body>
        <redoc spec-url="{openapi_url}"></redoc>
        <script src="https://cdn.jsdelivr.net/npm/redoc@latest/bundles/redoc.standalone.js"></script>
    </body>
    </html>
    """
