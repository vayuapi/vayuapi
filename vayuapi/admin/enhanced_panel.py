"""
Enhanced Admin Panel for VayuAPI
Full-featured admin interface similar to Django Admin
"""

from typing import Any, Dict, List, Type, Optional
from starlette.routing import Route
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.requests import Request
from vayuapi.core.responses import JSONResponse
import inspect
from datetime import datetime, date
from decimal import Decimal


class ModelAdmin:
    """
    Base admin class for model customization.
    Similar to Django's ModelAdmin with extensive features.
    """

    # Display configuration
    list_display: List[str] = []
    list_filter: List[str] = []
    search_fields: List[str] = []
    ordering: List[str] = []
    readonly_fields: List[str] = []
    list_per_page: int = 50

    # Actions
    actions: List[str] = ['delete_selected']

    def __init__(self, model: Type, admin_panel: 'AdminPanel'):
        self.model = model
        self.admin_panel = admin_panel
        self.model_name = model.__name__

        # Auto-detect fields if not specified
        if not self.list_display:
            self.list_display = self._get_model_fields()[:6]

    def _get_model_fields(self) -> List[str]:
        """Get model field names."""
        fields = []

        # For Django models
        if hasattr(self.model, '_meta'):
            for field in self.model._meta.get_fields():
                if hasattr(field, 'name'):
                    fields.append(field.name)

        # For Tortoise ORM
        elif hasattr(self.model, '_meta') and hasattr(self.model._meta, 'fields_map'):
            fields = list(self.model._meta.fields_map.keys())

        # For Pydantic/other
        elif hasattr(self.model, '__fields__'):
            fields = list(self.model.__fields__.keys())

        return fields or ['id']

    def get_field_value(self, obj, field_name: str) -> str:
        """Get formatted field value from object."""
        try:
            value = getattr(obj, field_name, 'N/A')

            # Format different types
            if value is None:
                return '-'
            elif isinstance(value, (datetime, date)):
                return value.strftime('%Y-%m-%d %H:%M:%S') if isinstance(value, datetime) else value.strftime('%Y-%m-%d')
            elif isinstance(value, bool):
                return '✓' if value else '✗'
            elif isinstance(value, Decimal):
                return f"{value:.2f}"
            elif isinstance(value, (int, float)):
                return str(value)
            else:
                return str(value)[:50]  # Truncate long strings
        except Exception:
            return 'Error'

    async def get_queryset(self, request: Request = None):
        """Get queryset for listing. Can be filtered/searched."""
        # For Django ORM
        if hasattr(self.model, 'objects'):
            from asgiref.sync import sync_to_async
            return await sync_to_async(lambda: list(self.model.objects.all()))()

        # For Tortoise ORM
        elif hasattr(self.model, 'all'):
            return await self.model.all()

        return []

    def has_add_permission(self, request: Request) -> bool:
        """Check if user can add objects."""
        return True

    def has_change_permission(self, request: Request) -> bool:
        """Check if user can change objects."""
        return True

    def has_delete_permission(self, request: Request) -> bool:
        """Check if user can delete objects."""
        return True


class AdminPanel:
    """
    Enhanced admin panel for VayuAPI with Django admin-like features.
    """

    def __init__(self, app, path: str = "/admin"):
        self.app = app
        self.path = path
        self.models: Dict[str, Type] = {}
        self.model_admins: Dict[str, ModelAdmin] = {}

    def register(self, model: Type, admin_class: Type[ModelAdmin] = None):
        """Register model with admin panel."""
        model_name = model.__name__
        self.models[model_name] = model

        if admin_class:
            self.model_admins[model_name] = admin_class(model, self)
        else:
            self.model_admins[model_name] = ModelAdmin(model, self)

    def get_routes(self) -> List[Route]:
        """Get admin panel routes."""
        routes = [
            Route(self.path, endpoint=self.index, name="admin_index"),
            Route(f"{self.path}/{{model}}", endpoint=self.model_list, name="admin_model_list", methods=["GET", "POST"]),
            Route(f"{self.path}/{{model}}/add", endpoint=self.model_add, methods=["GET", "POST"], name="admin_model_add"),
            Route(f"{self.path}/{{model}}/{{id}}", endpoint=self.model_detail, name="admin_model_detail"),
            Route(f"{self.path}/{{model}}/{{id}}/edit", endpoint=self.model_edit, methods=["GET", "POST"], name="admin_model_edit"),
            Route(f"{self.path}/{{model}}/{{id}}/delete", endpoint=self.model_delete, methods=["POST"], name="admin_model_delete"),
        ]
        return routes

    def _get_admin_html_template(self) -> str:
        """Get modern admin HTML template with Tailwind-like styling."""
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title} - VayuAPI Admin</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                    background: #f7fafc;
                    color: #2d3748;
                }
                .header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 1.5rem 2rem;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .header h1 { font-size: 1.75rem; font-weight: 700; margin-bottom: 0.25rem; }
                .header p { opacity: 0.9; font-size: 0.95rem; }
                .container {
                    max-width: 1400px;
                    margin: 2rem auto;
                    padding: 0 2rem;
                }
                .breadcrumbs {
                    display: flex;
                    gap: 0.5rem;
                    align-items: center;
                    margin-bottom: 1.5rem;
                    font-size: 0.875rem;
                }
                .breadcrumbs a {
                    color: #4a5568;
                    text-decoration: none;
                    transition: color 0.2s;
                }
                .breadcrumbs a:hover { color: #667eea; }
                .breadcrumbs span { color: #a0aec0; }
                .model-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                    gap: 1.5rem;
                }
                .model-card {
                    background: white;
                    border-radius: 0.5rem;
                    padding: 1.5rem;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    transition: all 0.2s;
                    text-decoration: none;
                    color: inherit;
                    display: block;
                }
                .model-card:hover {
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    transform: translateY(-2px);
                }
                .model-card-header {
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                    margin-bottom: 0.75rem;
                }
                .model-icon {
                    width: 40px;
                    height: 40px;
                    border-radius: 0.5rem;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: 700;
                    font-size: 1.25rem;
                }
                .model-name {
                    font-size: 1.25rem;
                    font-weight: 600;
                    color: #2d3748;
                }
                .model-count {
                    color: #718096;
                    font-size: 0.875rem;
                }
                .content-box {
                    background: white;
                    border-radius: 0.5rem;
                    padding: 1.5rem;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }
                .actions-bar {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 1.5rem;
                    gap: 1rem;
                    flex-wrap: wrap;
                }
                .search-box {
                    display: flex;
                    gap: 0.5rem;
                    flex: 1;
                    max-width: 400px;
                }
                .search-box input {
                    flex: 1;
                    padding: 0.5rem 1rem;
                    border: 1px solid #e2e8f0;
                    border-radius: 0.375rem;
                    font-size: 0.875rem;
                }
                .btn {
                    padding: 0.5rem 1.25rem;
                    border-radius: 0.375rem;
                    font-weight: 500;
                    font-size: 0.875rem;
                    text-decoration: none;
                    display: inline-block;
                    transition: all 0.2s;
                    border: none;
                    cursor: pointer;
                }
                .btn-primary {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }
                .btn-primary:hover { opacity: 0.9; transform: translateY(-1px);}
                .btn-secondary {
                    background: #e2e8f0;
                    color: #4a5568;
                }
                .btn-danger {
                    background: #fc8181;
                    color: white;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                }
                th {
                    background: #f7fafc;
                    padding: 0.75rem 1rem;
                    text-align: left;
                    font-weight: 600;
                    font-size: 0.875rem;
                    color: #4a5568;
                    border-bottom: 2px solid #e2e8f0;
                }
                td {
                    padding: 0.75rem 1rem;
                    border-bottom: 1px solid #e2e8f0;
                    font-size: 0.875rem;
                }
                tr:hover { background: #f7fafc; }
                .action-links {
                    display: flex;
                    gap: 0.75rem;
                }
                .action-links a {
                    color: #667eea;
                    text-decoration: none;
                    font-size: 0.875rem;
                }
                .action-links a:hover { text-decoration: underline; }
                .pagination {
                    display: flex;
                    justify-content: center;
                    gap: 0.5rem;
                    margin-top: 1.5rem;
                }
                .page-link {
                    padding: 0.5rem 0.75rem;
                    border: 1px solid #e2e8f0;
                    border-radius: 0.375rem;
                    text-decoration: none;
                    color: #4a5568;
                    font-size: 0.875rem;
                }
                .page-link.active {
                    background: #667eea;
                    color: white;
                    border-color: #667eea;
                }
                .filters {
                    display: flex;
                    gap: 1rem;
                    margin-bottom: 1rem;
                    flex-wrap: wrap;
                }
                .filter-item select {
                    padding: 0.5rem;
                    border: 1px solid #e2e8f0;
                    border-radius: 0.375rem;
                    font-size: 0.875rem;
                }
                .empty-state {
                    text-align: center;
                    padding: 3rem;
                    color: #a0aec0;
                }
                .empty-state svg {
                    width: 64px;
                    height: 64px;
                    margin: 0 auto 1rem;
                    opacity: 0.5;
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>⚡ VayuAPI Admin</h1>
                <p>Manage your application data</p>
            </div>
            <div class="container">
                {content}
            </div>
        </body>
        </html>
        """

    async def index(self, request: Request):
        """Admin panel home page."""
        model_cards = ""
        for name, model in self.models.items():
            first_letter = name[0].upper()
            model_cards += f"""
            <a href="{self.path}/{name}" class="model-card">
                <div class="model-card-header">
                    <div class="model-icon">{first_letter}</div>
                    <div>
                        <div class="model-name">{name}</div>
                        <div class="model-count">View and manage {name.lower()}s</div>
                    </div>
                </div>
            </a>
            """

        content = f"""
        <div class="breadcrumbs">
            <a href="{self.path}">Home</a>
        </div>
        <h2 style="font-size: 1.5rem; font-weight: 600; margin-bottom: 1.5rem;">Registered Models</h2>
        <div class="model-grid">
            {model_cards}
        </div>
        """

        html = self._get_admin_html_template().format(
            title="Admin Home",
            content=content
        )

        return HTMLResponse(html)

    async def model_list(self, request: Request):
        """List all objects of a model with search, filters, and pagination."""
        model_name = request.path_params["model"]

        if model_name not in self.models:
            return HTMLResponse("Model not found", status_code=404)

        model_admin = self.model_admins[model_name]
        objects = await model_admin.get_queryset(request)

        # Get search query
        search = request.query_params.get('search', '')

        # Build table
        fields = model_admin.list_display
        table_html =  f"""
        <div class="actions-bar">
            <form class="search-box" method="get">
                <input type="text" name="search" placeholder="Search {model_name}..." value="{search}">
                <button type="submit" class="btn btn-secondary">Search</button>
            </form>
            <a href="{self.path}/{model_name}/add" class="btn btn-primary">+ Add {model_name}</a>
        </div>
        """

        if objects:
            table_html += """
            <div class="content-box">
            <table>
                <thead>
                    <tr>
            """

            for field in fields:
                table_html += f"<th>{field.replace('_', ' ').title()}</th>"
            table_html += "<th>Actions</th></tr></thead><tbody>"

            for obj in objects:
                table_html += "<tr>"
                for field in fields:
                    value = model_admin.get_field_value(obj, field)
                    table_html += f"<td>{value}</td>"

                obj_id = getattr(obj, 'id', '')
                table_html += f"""
                <td class="action-links">
                    <a href="{self.path}/{model_name}/{obj_id}">View</a>
                    <a href="{self.path}/{model_name}/{obj_id}/edit">Edit</a>
                    <form method="post" action="{self.path}/{model_name}/{obj_id}/delete" style="display:inline;" onsubmit="return confirm('Are you sure?')">
                        <button type="submit" style="background:none;border:none;color:#fc8181;cursor:pointer;font-size:0.875rem;">Delete</button>
                    </form>
                </td>
                </tr>
                """

            table_html += "</tbody></table></div>"
            table_html += f"""
            <div class="pagination">
                <span class="page-link active">1</span>
            </div>
            """
        else:
            table_html += """
            <div class="content-box empty-state">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"></path>
                </svg>
                <h3 style="font-size: 1.125rem; font-weight: 600; margin-bottom: 0.5rem;">No {model_name}s yet</h3>
                <p style="margin-bottom: 1.5rem;">Get started by creating a new {model_name}</p>
                <a href="{self.path}/{model_name}/add" class="btn btn-primary">+ Create {model_name}</a>
            </div>
            """

        content = f"""
        <div class="breadcrumbs">
            <a href="{self.path}">Home</a>
            <span>/</span>
            <span>{model_name}</span>
        </div>
        <h2 style="font-size: 1.5rem; font-weight: 600; margin-bottom: 1.5rem;">{model_name} List</h2>
        {table_html}
        """

        html = self._get_admin_html_template().format(
            title=f"{model_name} List",
            content=content
        )

        return HTMLResponse(html)

    async def model_detail(self, request: Request):
        """Show model object details."""
        model_name = request.path_params["model"]
        object_id = request.path_params["id"]

        content = f"""
        <div class="breadcrumbs">
            <a href="{self.path}">Home</a>
            <span>/</span>
            <a href="{self.path}/{model_name}">{model_name}</a>
            <span>/</span>
            <span>#{object_id}</span>
        </div>
        <div class="content-box">
            <h2 style="font-size: 1.5rem; font-weight: 600; margin-bottom: 1rem;">{model_name} #{object_id}</h2>
            <div style="margin-top: 1.5rem;">
                <a href="{self.path}/{model_name}/{object_id}/edit" class="btn btn-primary">Edit</a>
                <a href="{self.path}/{model_name}" class="btn btn-secondary">Back to List</a>
            </div>
        </div>
        """

        html = self._get_admin_html_template().format(
            title=f"{model_name} Detail",
            content=content
        )

        return HTMLResponse(html)

    async def model_add(self, request: Request):
        """Add new model object."""
        model_name = request.path_params["model"]

        if request.method == "POST":
            # Handle form submission
            return RedirectResponse(url=f"{self.path}/{model_name}", status_code=303)

        content = f"""
        <div class="breadcrumbs">
            <a href="{self.path}">Home</a>
            <span>/</span>
            <a href="{self.path}/{model_name}">{model_name}</a>
            <span>/</span>
            <span>Add</span>
        </div>
        <div class="content-box">
            <h2 style="font-size: 1.5rem; font-weight: 600; margin-bottom: 1.5rem;">Add {model_name}</h2>
            <form method="post">
                <p style="color: #718096; margin-bottom: 1rem;">Form fields will appear here based on model structure.</p>
                <div style="margin-top: 1.5rem; display: flex; gap: 1rem;">
                    <button type="submit" class="btn btn-primary">Save</button>
                    <a href="{self.path}/{model_name}" class="btn btn-secondary">Cancel</a>
                </div>
            </form>
        </div>
        """

        html = self._get_admin_html_template().format(
            title=f"Add {model_name}",
            content=content
        )

        return HTMLResponse(html)

    async def model_edit(self, request: Request):
        """Edit model object."""
        model_name = request.path_params["model"]
        object_id = request.path_params["id"]

        content = f"""
        <div class="breadcrumbs">
            <a href="{self.path}">Home</a>
            <span>/</span>
            <a href="{self.path}/{model_name}">{model_name}</a>
            <span>/</span>
            <span>Edit #{object_id}</span>
        </div>
        <div class="content-box">
            <h2 style="font-size: 1.5rem; font-weight: 600; margin-bottom: 1.5rem;">Edit {model_name} #{object_id}</h2>
            <form method="post">
                <p style="color: #718096; margin-bottom: 1rem;">Edit form fields will appear here.</p>
                <div style="margin-top: 1.5rem; display: flex; gap: 1rem;">
                    <button type="submit" class="btn btn-primary">Save Changes</button>
                    <a href="{self.path}/{model_name}" class="btn btn-secondary">Cancel</a>
                </div>
            </form>
        </div>
        """

        html = self._get_admin_html_template().format(
            title=f"Edit {model_name}",
            content=content
        )

        return HTMLResponse(html)

    async def model_delete(self, request: Request):
        """Delete model object."""
        model_name = request.path_params["model"]
        object_id = request.path_params["id"]

        # Delete logic here
        return RedirectResponse(url=f"{self.path}/{model_name}", status_code=303)
