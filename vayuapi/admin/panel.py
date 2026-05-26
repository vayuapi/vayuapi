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
        if hasattr(self.model, '_meta') and hasattr(self.model._meta, 'get_fields'):
            try:
                for field in self.model._meta.get_fields():
                    if hasattr(field, 'name'):
                        fields.append(field.name)
            except (AttributeError, TypeError):
                pass

        # For Tortoise ORM
        if not fields and hasattr(self.model, '_meta') and hasattr(self.model._meta, 'fields_map'):
            fields = list(self.model._meta.fields_map.keys())

        # For Pydantic/other
        if not fields and hasattr(self.model, '__fields__'):
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
            # Check if it's a model instance (ForeignKey relationship)
            elif hasattr(value, '_meta') and hasattr(value._meta, 'model_name'):
                return str(value)  # Use the model's __str__ method
            else:
                return str(value)[:50]  # Truncate long strings
        except Exception as e:
            return 'Error'

    async def get_queryset(self, request: Request = None):
        """Get queryset for listing. Can be filtered/searched."""
        # For Django ORM
        if hasattr(self.model, 'objects'):
            from asgiref.sync import sync_to_async

            def get_objects():
                queryset = self.model.objects.all()

                # Optimize queryset by selecting related ForeignKey fields
                if hasattr(self.model, '_meta') and hasattr(self.model._meta, 'get_fields'):
                    try:
                        related_fields = []
                        for field in self.model._meta.get_fields():
                            if hasattr(field, 'get_internal_type'):
                                if field.get_internal_type() in ['ForeignKey', 'OneToOneField']:
                                    related_fields.append(field.name)

                        if related_fields:
                            queryset = queryset.select_related(*related_fields)
                    except (AttributeError, TypeError):
                        pass

                return list(queryset)

            return await sync_to_async(get_objects)()

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

    Args:
        app: VayuAPI application instance
        path: URL path for admin panel (default: "/admin")
        prefix: Alias for path parameter for compatibility
        secret_key: Secret key for session middleware (optional)
        admin_username: Username for admin authentication (optional)
        admin_password: Password for admin authentication (optional)
        require_auth: Whether authentication is required (default: True)
    """

    def __init__(
        self,
        app,
        path: str = "/admin",
        prefix: str = None,
        secret_key: str = None,
        admin_username: str = None,
        admin_password: str = None,
        require_auth: bool = True
    ):
        self.app = app
        # Support both 'path' and 'prefix' parameters for compatibility
        self.path = prefix if prefix is not None else path
        self.models: Dict[str, Type] = {}
        self.model_admins: Dict[str, ModelAdmin] = {}
        self.require_auth = require_auth
        self.secret_key = secret_key
        self.admin_username = admin_username
        self.admin_password = admin_password

    def _get_form_fields(self, model) -> str:
        """Generate HTML form fields from model."""
        form_html = ""

        # For Django models
        if hasattr(model, '_meta') and hasattr(model._meta, 'get_fields'):
            try:
                fields = model._meta.get_fields()
            except (AttributeError, TypeError):
                return form_html
            for field in fields:
                if not hasattr(field, 'name'):
                    continue

                field_name = field.name

                # Skip auto fields and relations
                if field_name == 'id' or field.auto_created:
                    continue

                # Skip auto_now and auto_now_add fields
                if hasattr(field, 'auto_now') and field.auto_now:
                    continue
                if hasattr(field, 'auto_now_add') and field.auto_now_add:
                    continue

                # Get field properties
                field_label = field.verbose_name if hasattr(field, 'verbose_name') else field_name.replace('_', ' ').title()
                required = "required" if not field.blank and not field.null else ""

                # Generate field HTML based on type
                if hasattr(field, 'choices') and field.choices:
                    # Choice field (dropdown)
                    options = ''.join([f'<option value="{choice[0]}">{choice[1]}</option>' for choice in field.choices])
                    form_html += f"""
                    <div class="form-group">
                        <label for="{field_name}">{field_label}</label>
                        <select name="{field_name}" id="{field_name}" {required}>
                            <option value="">---------</option>
                            {options}
                        </select>
                    </div>
                    """
                elif field.get_internal_type() == 'BooleanField':
                    # Boolean field (checkbox)
                    form_html += f"""
                    <div class="form-group checkbox-group">
                        <label>
                            <input type="checkbox" name="{field_name}" id="{field_name}" value="1">
                            {field_label}
                        </label>
                    </div>
                    """
                elif field.get_internal_type() == 'TextField':
                    # Text area
                    form_html += f"""
                    <div class="form-group">
                        <label for="{field_name}">{field_label}</label>
                        <textarea name="{field_name}" id="{field_name}" rows="4" {required}></textarea>
                    </div>
                    """
                elif field.get_internal_type() in ['ForeignKey', 'OneToOneField']:
                    # Foreign key field - fetch related objects
                    related_model = field.related_model
                    related_objects = []
                    try:
                        # Import here to avoid issues if Django is not installed
                        import django
                        from django.db import connection

                        # Check if we're in async context - if so, we need to handle differently
                        # For now, try synchronous query which should work when called from sync context
                        if hasattr(related_model, 'objects'):
                            # Fetch related objects synchronously
                            related_objects = list(related_model.objects.all()[:100])
                    except Exception as e:
                        # Log the error for debugging
                        import traceback
                        print(f"Error fetching related objects for {field_name}: {e}")
                        traceback.print_exc()

                    options_html = ''.join([
                        f'<option value="{obj.id}">{str(obj)}</option>'
                        for obj in related_objects
                    ])

                    form_html += f"""
                    <div class="form-group">
                        <label for="{field_name}">{field_label}</label>
                        <select name="{field_name}" id="{field_name}" {required}>
                            <option value="">---------</option>
                            {options_html}
                        </select>
                    </div>
                    """
                elif field.get_internal_type() == 'ManyToManyField':
                    # Many-to-many field - show as multi-select
                    related_model = field.related_model
                    related_objects = []
                    try:
                        if hasattr(related_model, 'objects'):
                            related_objects = list(related_model.objects.all()[:100])
                    except Exception as e:
                        import traceback
                        print(f"Error fetching m2m objects for {field_name}: {e}")
                        traceback.print_exc()

                    checkboxes_html = ''.join([
                        f'<div style="margin-bottom: 0.5rem;"><label><input type="checkbox" name="{field_name}" value="{obj.id}"> {str(obj)}</label></div>'
                        for obj in related_objects
                    ])

                    form_html += f"""
                    <div class="form-group">
                        <label>{field_label}</label>
                        <div style="border: 1px solid #e2e8f0; border-radius: 0.375rem; padding: 0.75rem; max-height: 200px; overflow-y: auto;">
                            {checkboxes_html if checkboxes_html else '<p style="color: #718096; margin: 0;">No options available</p>'}
                        </div>
                    </div>
                    """
                elif field.get_internal_type() in ['IntegerField', 'BigIntegerField', 'SmallIntegerField']:
                    # Integer field
                    form_html += f"""
                    <div class="form-group">
                        <label for="{field_name}">{field_label}</label>
                        <input type="number" name="{field_name}" id="{field_name}" step="1" {required}>
                    </div>
                    """
                elif field.get_internal_type() in ['DecimalField', 'FloatField']:
                    # Decimal field
                    form_html += f"""
                    <div class="form-group">
                        <label for="{field_name}">{field_label}</label>
                        <input type="number" name="{field_name}" id="{field_name}" step="0.01" {required}>
                    </div>
                    """
                elif field.get_internal_type() == 'EmailField':
                    # Email field
                    form_html += f"""
                    <div class="form-group">
                        <label for="{field_name}">{field_label}</label>
                        <input type="email" name="{field_name}" id="{field_name}" {required}>
                    </div>
                    """
                elif field.get_internal_type() == 'DateTimeField':
                    # DateTime field
                    form_html += f"""
                    <div class="form-group">
                        <label for="{field_name}">{field_label}</label>
                        <input type="datetime-local" name="{field_name}" id="{field_name}" {required}>
                    </div>
                    """
                elif field.get_internal_type() == 'DateField':
                    # Date field
                    form_html += f"""
                    <div class="form-group">
                        <label for="{field_name}">{field_label}</label>
                        <input type="date" name="{field_name}" id="{field_name}" {required}>
                    </div>
                    """
                else:
                    # Default to text input
                    max_length = f'maxlength="{field.max_length}"' if hasattr(field, 'max_length') and field.max_length else ''
                    form_html += f"""
                    <div class="form-group">
                        <label for="{field_name}">{field_label}</label>
                        <input type="text" name="{field_name}" id="{field_name}" {max_length} {required}>
                    </div>
                    """

        return form_html

    def _get_form_fields_with_data(self, model, obj) -> str:
        """Generate HTML form fields from model with existing data."""
        form_html = ""

        # For Django models
        if hasattr(model, '_meta') and hasattr(model._meta, 'get_fields'):
            try:
                fields = model._meta.get_fields()
            except (AttributeError, TypeError):
                return form_html
            for field in fields:
                if not hasattr(field, 'name'):
                    continue

                field_name = field.name

                # Skip auto fields and relations
                if field_name == 'id' or field.auto_created:
                    continue

                # Skip auto_now and auto_now_add fields
                if hasattr(field, 'auto_now') and field.auto_now:
                    continue
                if hasattr(field, 'auto_now_add') and field.auto_now_add:
                    continue

                # Get field properties
                field_label = field.verbose_name if hasattr(field, 'verbose_name') else field_name.replace('_', ' ').title()
                required = "required" if not field.blank and not field.null else ""

                # Get current value
                value = getattr(obj, field_name, '')
                if value is None:
                    value = ''

                # Generate field HTML based on type
                if hasattr(field, 'choices') and field.choices:
                    # Choice field (dropdown)
                    options = ''.join([
                        f'<option value="{choice[0]}" {"selected" if str(value) == str(choice[0]) else ""}>{choice[1]}</option>'
                        for choice in field.choices
                    ])
                    form_html += f"""
                    <div class="form-group">
                        <label for="{field_name}">{field_label}</label>
                        <select name="{field_name}" id="{field_name}" {required}>
                            <option value="">---------</option>
                            {options}
                        </select>
                    </div>
                    """
                elif field.get_internal_type() == 'BooleanField':
                    # Boolean field (checkbox)
                    checked = 'checked' if value else ''
                    form_html += f"""
                    <div class="form-group checkbox-group">
                        <label>
                            <input type="checkbox" name="{field_name}" id="{field_name}" value="1" {checked}>
                            {field_label}
                        </label>
                    </div>
                    """
                elif field.get_internal_type() == 'TextField':
                    # Text area
                    form_html += f"""
                    <div class="form-group">
                        <label for="{field_name}">{field_label}</label>
                        <textarea name="{field_name}" id="{field_name}" rows="4" {required}>{value}</textarea>
                    </div>
                    """
                elif field.get_internal_type() in ['ForeignKey', 'OneToOneField']:
                    # Foreign key field - fetch related objects and set current
                    related_model = field.related_model
                    related_objects = []
                    try:
                        # Import here to avoid issues if Django is not installed
                        import django
                        from django.db import connection

                        if hasattr(related_model, 'objects'):
                            related_objects = list(related_model.objects.all()[:100])
                    except Exception as e:
                        # Log the error for debugging
                        import traceback
                        print(f"Error fetching related objects for {field_name} in edit: {e}")
                        traceback.print_exc()

                    current_id = value.id if hasattr(value, 'id') else value
                    options_html = ''.join([
                        f'<option value="{obj.id}" {"selected" if str(obj.id) == str(current_id) else ""}>{str(obj)}</option>'
                        for obj in related_objects
                    ])

                    form_html += f"""
                    <div class="form-group">
                        <label for="{field_name}">{field_label}</label>
                        <select name="{field_name}" id="{field_name}" {required}>
                            <option value="">---------</option>
                            {options_html}
                        </select>
                    </div>
                    """
                elif field.get_internal_type() == 'ManyToManyField':
                    # Many-to-many field - show as checkboxes with current selections
                    related_model = field.related_model
                    related_objects = []
                    selected_ids = []

                    try:
                        if hasattr(related_model, 'objects'):
                            related_objects = list(related_model.objects.all()[:100])
                        # Get currently selected objects
                        if hasattr(obj, field_name):
                            m2m_manager = getattr(obj, field_name)
                            selected_ids = [rel_obj.id for rel_obj in m2m_manager.all()]
                    except Exception as e:
                        import traceback
                        print(f"Error fetching m2m objects for {field_name} in edit: {e}")
                        traceback.print_exc()

                    checkboxes_html = ''.join([
                        f'<div style="margin-bottom: 0.5rem;"><label><input type="checkbox" name="{field_name}" value="{rel_obj.id}" {"checked" if rel_obj.id in selected_ids else ""}> {str(rel_obj)}</label></div>'
                        for rel_obj in related_objects
                    ])

                    form_html += f"""
                    <div class="form-group">
                        <label>{field_label}</label>
                        <div style="border: 1px solid #e2e8f0; border-radius: 0.375rem; padding: 0.75rem; max-height: 200px; overflow-y: auto;">
                            {checkboxes_html if checkboxes_html else '<p style="color: #718096; margin: 0;">No options available</p>'}
                        </div>
                    </div>
                    """
                elif field.get_internal_type() in ['IntegerField', 'BigIntegerField', 'SmallIntegerField']:
                    # Integer field
                    form_html += f"""
                    <div class="form-group">
                        <label for="{field_name}">{field_label}</label>
                        <input type="number" name="{field_name}" id="{field_name}" step="1" value="{value}" {required}>
                    </div>
                    """
                elif field.get_internal_type() in ['DecimalField', 'FloatField']:
                    # Decimal field
                    form_html += f"""
                    <div class="form-group">
                        <label for="{field_name}">{field_label}</label>
                        <input type="number" name="{field_name}" id="{field_name}" step="0.01" value="{value}" {required}>
                    </div>
                    """
                elif field.get_internal_type() == 'EmailField':
                    # Email field
                    form_html += f"""
                    <div class="form-group">
                        <label for="{field_name}">{field_label}</label>
                        <input type="email" name="{field_name}" id="{field_name}" value="{value}" {required}>
                    </div>
                    """
                elif field.get_internal_type() == 'DateTimeField':
                    # DateTime field
                    datetime_value = value.strftime('%Y-%m-%dT%H:%M') if isinstance(value, datetime) else ''
                    form_html += f"""
                    <div class="form-group">
                        <label for="{field_name}">{field_label}</label>
                        <input type="datetime-local" name="{field_name}" id="{field_name}" value="{datetime_value}" {required}>
                    </div>
                    """
                elif field.get_internal_type() == 'DateField':
                    # Date field
                    date_value = value.strftime('%Y-%m-%d') if isinstance(value, (datetime, date)) else ''
                    form_html += f"""
                    <div class="form-group">
                        <label for="{field_name}">{field_label}</label>
                        <input type="date" name="{field_name}" id="{field_name}" value="{date_value}" {required}>
                    </div>
                    """
                else:
                    # Default to text input
                    max_length = f'maxlength="{field.max_length}"' if hasattr(field, 'max_length') and field.max_length else ''
                    form_html += f"""
                    <div class="form-group">
                        <label for="{field_name}">{field_label}</label>
                        <input type="text" name="{field_name}" id="{field_name}" value="{value}" {max_length} {required}>
                    </div>
                    """

        return form_html

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
            Route(f"{self.path}/login", endpoint=self.login, methods=["GET", "POST"], name="admin_login"),
            Route(f"{self.path}/logout", endpoint=self.logout, methods=["GET", "POST"], name="admin_logout"),
            Route(f"{self.path}/account", endpoint=self.account, methods=["GET", "POST"], name="admin_account"),
            Route(f"{self.path}/change-password", endpoint=self.change_password, methods=["GET", "POST"], name="admin_change_password"),
            Route(self.path, endpoint=self.index, name="admin_index"),
            Route(f"{self.path}/{{model}}/add", endpoint=self.model_add, methods=["GET", "POST"], name="admin_model_add"),
            Route(f"{self.path}/{{model}}/{{id}}/edit", endpoint=self.model_edit, methods=["GET", "POST"], name="admin_model_edit"),
            Route(f"{self.path}/{{model}}/{{id}}/delete", endpoint=self.model_delete, methods=["POST"], name="admin_model_delete"),
            Route(f"{self.path}/{{model}}/{{id}}", endpoint=self.model_detail, name="admin_model_detail"),
            Route(f"{self.path}/{{model}}", endpoint=self.model_list, name="admin_model_list", methods=["GET", "POST"]),
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
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                    background: #f7fafc;
                    color: #2d3748;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 1.5rem 2rem;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .header h1 {{ font-size: 1.75rem; font-weight: 700; margin-bottom: 0.25rem; }}
                .header p {{ opacity: 0.9; font-size: 0.95rem; }}
                .container {{
                    max-width: 1400px;
                    margin: 2rem auto;
                    padding: 0 2rem;
                }}
                .breadcrumbs {{
                    display: flex;
                    gap: 0.5rem;
                    align-items: center;
                    margin-bottom: 1.5rem;
                    font-size: 0.875rem;
                    width: 100%;
                }}
                .breadcrumbs a {{
                    color: #4a5568;
                    text-decoration: none;
                    transition: color 0.2s;
                }}
                .breadcrumbs a:hover {{ color: #667eea; }}
                .breadcrumbs span {{ color: #a0aec0; }}
                .model-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                    gap: 1.5rem;
                }}
                .model-card {{
                    background: white;
                    border-radius: 0.5rem;
                    padding: 1.5rem;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    transition: all 0.2s;
                    text-decoration: none;
                    color: inherit;
                    display: block;
                }}
                .model-card:hover {{
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    transform: translateY(-2px);
                }}
                .model-card-header {{
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                    margin-bottom: 0.75rem;
                }}
                .model-icon {{
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
                }}
                .model-name {{
                    font-size: 1.25rem;
                    font-weight: 600;
                    color: #2d3748;
                }}
                .model-count {{
                    color: #718096;
                    font-size: 0.875rem;
                }}
                .content-box {{
                    background: white;
                    border-radius: 0.5rem;
                    padding: 1.5rem;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }}
                .actions-bar {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 1.5rem;
                    gap: 1rem;
                    flex-wrap: wrap;
                }}
                .search-box {{
                    display: flex;
                    gap: 0.5rem;
                    flex: 1;
                    max-width: 400px;
                }}
                .search-box input {{
                    flex: 1;
                    padding: 0.5rem 1rem;
                    border: 1px solid #e2e8f0;
                    border-radius: 0.375rem;
                    font-size: 0.875rem;
                }}
                .btn {{
                    padding: 0.5rem 1.25rem;
                    border-radius: 0.375rem;
                    font-weight: 500;
                    font-size: 0.875rem;
                    text-decoration: none;
                    display: inline-block;
                    transition: all 0.2s;
                    border: none;
                    cursor: pointer;
                }}
                .btn-primary {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }}
                .btn-primary:hover {{ opacity: 0.9; transform: translateY(-1px);}}
                .btn-secondary {{
                    background: #e2e8f0;
                    color: #4a5568;
                }}
                .btn-danger {{
                    background: #fc8181;
                    color: white;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                th {{
                    background: #f7fafc;
                    padding: 0.75rem 1rem;
                    text-align: left;
                    font-weight: 600;
                    font-size: 0.875rem;
                    color: #4a5568;
                    border-bottom: 2px solid #e2e8f0;
                }}
                td {{
                    padding: 0.75rem 1rem;
                    border-bottom: 1px solid #e2e8f0;
                    font-size: 0.875rem;
                }}
                tr:hover {{ background: #f7fafc; }}
                .action-links {{
                    display: flex;
                    gap: 0.75rem;
                }}
                .action-links a {{
                    color: #667eea;
                    text-decoration: none;
                    font-size: 0.875rem;
                }}
                .action-links a:hover {{ text-decoration: underline; }}
                .pagination {{
                    display: flex;
                    justify-content: center;
                    gap: 0.5rem;
                    margin-top: 1.5rem;
                }}
                .page-link {{
                    padding: 0.5rem 0.75rem;
                    border: 1px solid #e2e8f0;
                    border-radius: 0.375rem;
                    text-decoration: none;
                    color: #4a5568;
                    font-size: 0.875rem;
                }}
                .page-link.active {{
                    background: #667eea;
                    color: white;
                    border-color: #667eea;
                }}
                .filters {{
                    display: flex;
                    gap: 1rem;
                    margin-bottom: 1rem;
                    flex-wrap: wrap;
                }}
                .filter-item select {{
                    padding: 0.5rem;
                    border: 1px solid #e2e8f0;
                    border-radius: 0.375rem;
                    font-size: 0.875rem;
                }}
                .empty-state {{
                    text-align: center;
                    padding: 3rem;
                    color: #a0aec0;
                }}
                .empty-state svg {{
                    width: 64px;
                    height: 64px;
                    margin: 0 auto 1rem;
                    opacity: 0.5;
                }}
                .form-group {{
                    margin-bottom: 1.5rem;
                }}
                .form-group label {{
                    display: block;
                    font-weight: 500;
                    margin-bottom: 0.5rem;
                    color: #2d3748;
                }}
                .form-group input,
                .form-group textarea,
                .form-group select {{
                    width: 100%;
                    padding: 0.5rem 0.75rem;
                    border: 1px solid #e2e8f0;
                    border-radius: 0.375rem;
                    font-size: 0.875rem;
                    font-family: inherit;
                }}
                .form-group input:focus,
                .form-group textarea:focus,
                .form-group select:focus {{
                    outline: none;
                    border-color: #667eea;
                    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
                }}
                .checkbox-group {{
                    display: flex;
                    align-items: center;
                }}
                .checkbox-group label {{
                    display: flex;
                    align-items: center;
                    margin-bottom: 0;
                    cursor: pointer;
                }}
                .checkbox-group input[type="checkbox"] {{
                    width: auto;
                    margin-right: 0.5rem;
                }}
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

    async def _check_auth(self, request: Request):
        """Check if user is authenticated as superuser."""
        if not self.require_auth:
            return True

        # Check session for authenticated user
        user_id = request.session.get('admin_user_id')
        if not user_id:
            return False

        # Try to get Django User model if available
        try:
            from django.contrib.auth.models import User
            from asgiref.sync import sync_to_async

            @sync_to_async
            def get_user():
                try:
                    return User.objects.get(id=user_id)
                except User.DoesNotExist:
                    return None

            user = await get_user()
            if user and user.is_superuser and user.is_active:
                return True
        except ImportError:
            # Django not available, allow access if session exists
            return True

        return False

    async def _require_auth(self, request: Request):
        """Require authentication, redirect to login if not authenticated."""
        is_authenticated = await self._check_auth(request)
        if not is_authenticated:
            # Redirect to login page
            return RedirectResponse(url=f"{self.path}/login?next={request.url.path}", status_code=302)
        return None

    def _get_nav_header(self, request: Request, breadcrumb_items: list = None) -> str:
        """Generate navigation header with breadcrumbs and user menu."""
        username = request.session.get('admin_username', 'Admin')

        # Build breadcrumbs
        breadcrumbs = '<a href="' + self.path + '">Home</a>'
        if breadcrumb_items:
            for item in breadcrumb_items:
                if isinstance(item, tuple):
                    # Tuple: (text, url)
                    breadcrumbs += f' <span>/</span> <a href="{item[1]}">{item[0]}</a>'
                else:
                    # String: just text
                    breadcrumbs += f' <span>/</span> <span>{item}</span>'

        return f'''
        <div class="breadcrumbs">
            {breadcrumbs}
            <span style="margin-left: auto; display: flex; align-items: center; gap: 1rem;">
                <a href="{self.path}/account" style="color: #667eea; text-decoration: none; font-weight: 500;">👤 {username}</a>
                <a href="{self.path}/change-password" style="color: #667eea; text-decoration: none; font-weight: 500;">🔑 Password</a>
                <a href="{self.path}/logout" style="color: #667eea; text-decoration: none; font-weight: 500;">🚪 Logout</a>
            </span>
        </div>
        '''

    async def login(self, request: Request):
        """Admin login page and handler."""
        error_message = ""

        if request.method == "POST":
            form_data = await request.form()
            username = form_data.get('username', '')
            password = form_data.get('password', '')

            try:
                from django.contrib.auth.models import User
                from django.contrib.auth.hashers import check_password
                from asgiref.sync import sync_to_async

                @sync_to_async
                def authenticate_user():
                    try:
                        user = User.objects.get(username=username)
                        if check_password(password, user.password):
                            return user
                    except User.DoesNotExist:
                        pass
                    return None

                user = await authenticate_user()

                if user and user.is_superuser and user.is_active:
                    # Set session
                    request.session['admin_user_id'] = user.id
                    request.session['admin_username'] = user.username

                    # Redirect to next URL or admin home
                    next_url = request.query_params.get('next', self.path)
                    return RedirectResponse(url=next_url, status_code=302)
                else:
                    error_message = "Invalid credentials or insufficient permissions. Only superusers can access the admin panel."
            except ImportError:
                error_message = "Django authentication not available."
            except Exception as e:
                error_message = f"Authentication error: {str(e)}"

        # Show login page
        error_html = f'<div class="error-message">{error_message}</div>' if error_message else ''

        login_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Admin Login - VayuAPI Admin</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: #2d3748;
                }}
                .login-container {{
                    background: white;
                    border-radius: 0.5rem;
                    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
                    width: 100%;
                    max-width: 400px;
                    padding: 2rem;
                }}
                .login-header {{
                    text-align: center;
                    margin-bottom: 2rem;
                }}
                .login-header h1 {{
                    font-size: 1.875rem;
                    font-weight: 700;
                    color: #667eea;
                    margin-bottom: 0.5rem;
                }}
                .login-header p {{
                    color: #718096;
                    font-size: 0.875rem;
                }}
                .form-group {{
                    margin-bottom: 1.5rem;
                }}
                .form-group label {{
                    display: block;
                    font-weight: 500;
                    margin-bottom: 0.5rem;
                    color: #2d3748;
                }}
                .form-group input {{
                    width: 100%;
                    padding: 0.75rem;
                    border: 1px solid #e2e8f0;
                    border-radius: 0.375rem;
                    font-size: 0.875rem;
                    font-family: inherit;
                    transition: all 0.2s;
                }}
                .form-group input:focus {{
                    outline: none;
                    border-color: #667eea;
                    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
                }}
                .error-message {{
                    background: #fed7d7;
                    border: 1px solid #fc8181;
                    color: #c53030;
                    padding: 0.75rem;
                    border-radius: 0.375rem;
                    margin-bottom: 1rem;
                    font-size: 0.875rem;
                }}
                .btn-login {{
                    width: 100%;
                    padding: 0.75rem;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    border-radius: 0.375rem;
                    font-size: 1rem;
                    font-weight: 600;
                    cursor: pointer;
                    transition: transform 0.2s;
                }}
                .btn-login:hover {{
                    transform: translateY(-1px);
                }}
                .btn-login:active {{
                    transform: translateY(0);
                }}
                .login-footer {{
                    margin-top: 1.5rem;
                    text-align: center;
                    font-size: 0.875rem;
                    color: #718096;
                }}
            </style>
        </head>
        <body>
            <div class="login-container">
                <div class="login-header">
                    <h1>⚡ VayuAPI Admin</h1>
                    <p>Sign in to continue to admin panel</p>
                </div>
                {error_html}
                <form method="POST" action="{self.path}/login">
                    <div class="form-group">
                        <label for="username">Username</label>
                        <input type="text" id="username" name="username" required autofocus>
                    </div>
                    <div class="form-group">
                        <label for="password">Password</label>
                        <input type="password" id="password" name="password" required>
                    </div>
                    <button type="submit" class="btn-login">Sign In</button>
                </form>
                <div class="login-footer">
                    <p>Only superusers can access the admin panel</p>
                </div>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(login_html)

    async def logout(self, request: Request):
        """Admin logout handler."""
        # Clear session
        request.session.clear()

        # Redirect to login page
        return RedirectResponse(url=f"{self.path}/login", status_code=302)

    async def account(self, request: Request):
        """User account management page."""
        # Check authentication
        auth_response = await self._require_auth(request)
        if auth_response:
            return auth_response

        user_id = request.session.get('admin_user_id')
        username = request.session.get('admin_username', 'Admin')
        success_message = ""
        error_message = ""

        try:
            from django.contrib.auth.models import User
            from asgiref.sync import sync_to_async

            @sync_to_async
            def get_user():
                try:
                    return User.objects.get(id=user_id)
                except User.DoesNotExist:
                    return None

            user = await get_user()

            if not user:
                return RedirectResponse(url=f"{self.path}/login", status_code=302)

            # Handle form submission
            if request.method == "POST":
                form_data = await request.form()

                @sync_to_async
                def update_user():
                    user.username = form_data.get('username', user.username)
                    user.email = form_data.get('email', user.email)
                    user.first_name = form_data.get('first_name', user.first_name)
                    user.last_name = form_data.get('last_name', user.last_name)
                    user.save()
                    return user

                try:
                    user = await update_user()
                    request.session['admin_username'] = user.username
                    success_message = "✅ Profile updated successfully!"
                except Exception as e:
                    error_message = f"❌ Error updating profile: {str(e)}"

            # Generate account page HTML
            success_html = f'<div class="success-message">{success_message}</div>' if success_message else ''
            error_html = f'<div class="error-message">{error_message}</div>' if error_message else ''

            content = f"""
            <div class="breadcrumbs">
                <a href="{self.path}">Home</a>
                <span> / </span>
                <span>My Account</span>
                <span style="margin-left: auto; display: flex; align-items: center; gap: 1rem;">
                    <a href="{self.path}/change-password" style="color: #667eea; text-decoration: none; font-weight: 500;">🔑 Change Password</a>
                    <a href="{self.path}/logout" style="color: #667eea; text-decoration: none; font-weight: 500;">🚪 Logout</a>
                </span>
            </div>

            <h2 style="font-size: 1.5rem; font-weight: 600; margin-bottom: 1.5rem;">👤 Account Settings</h2>

            {success_html}
            {error_html}

            <div class="card" style="max-width: 600px;">
                <h3 style="font-size: 1.25rem; font-weight: 600; margin-bottom: 1.5rem; color: #2d3748;">Edit Profile</h3>

                <form method="POST" action="{self.path}/account">
                    <div class="form-group">
                        <label for="username">Username</label>
                        <input type="text" id="username" name="username" value="{user.username}" required>
                    </div>

                    <div class="form-group">
                        <label for="email">Email</label>
                        <input type="email" id="email" name="email" value="{user.email or ''}" required>
                    </div>

                    <div class="form-group">
                        <label for="first_name">First Name</label>
                        <input type="text" id="first_name" name="first_name" value="{user.first_name or ''}">
                    </div>

                    <div class="form-group">
                        <label for="last_name">Last Name</label>
                        <input type="text" id="last_name" name="last_name" value="{user.last_name or ''}">
                    </div>

                    <div style="margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid #e2e8f0;">
                        <h4 style="font-size: 1rem; font-weight: 600; margin-bottom: 1rem; color: #2d3748;">Account Information</h4>
                        <div style="display: grid; gap: 0.75rem; color: #718096; font-size: 0.875rem;">
                            <div><strong>Superuser:</strong> {'✓ Yes' if user.is_superuser else '✗ No'}</div>
                            <div><strong>Staff Status:</strong> {'✓ Yes' if user.is_staff else '✗ No'}</div>
                            <div><strong>Active:</strong> {'✓ Yes' if user.is_active else '✗ No'}</div>
                            <div><strong>Date Joined:</strong> {user.date_joined.strftime('%Y-%m-%d %H:%M:%S') if user.date_joined else 'N/A'}</div>
                            <div><strong>Last Login:</strong> {user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'Never'}</div>
                        </div>
                    </div>

                    <div style="display: flex; gap: 1rem; margin-top: 1.5rem;">
                        <button type="submit" class="btn-primary">💾 Save Changes</button>
                        <a href="{self.path}" class="btn-secondary" style="display: inline-block; padding: 0.5rem 1rem; text-decoration: none;">Cancel</a>
                    </div>
                </form>
            </div>

            <style>
                .success-message {{
                    background: #c6f6d5;
                    border: 1px solid #48bb78;
                    color: #22543d;
                    padding: 1rem;
                    border-radius: 0.375rem;
                    margin-bottom: 1.5rem;
                    font-weight: 500;
                }}
                .error-message {{
                    background: #fed7d7;
                    border: 1px solid #fc8181;
                    color: #c53030;
                    padding: 1rem;
                    border-radius: 0.375rem;
                    margin-bottom: 1.5rem;
                    font-weight: 500;
                }}
                .btn-secondary {{
                    background: #e2e8f0;
                    color: #2d3748;
                    border: none;
                    border-radius: 0.375rem;
                    font-weight: 500;
                    cursor: pointer;
                    transition: background 0.2s;
                }}
                .btn-secondary:hover {{
                    background: #cbd5e0;
                }}
            </style>
            """

            return HTMLResponse(self._get_admin_html_template().format(
                title="My Account",
                content=content
            ))

        except ImportError:
            return HTMLResponse("Django authentication not available", status_code=500)

    async def change_password(self, request: Request):
        """Change password page."""
        # Check authentication
        auth_response = await self._require_auth(request)
        if auth_response:
            return auth_response

        user_id = request.session.get('admin_user_id')
        username = request.session.get('admin_username', 'Admin')
        success_message = ""
        error_message = ""

        try:
            from django.contrib.auth.models import User
            from django.contrib.auth.hashers import check_password, make_password
            from asgiref.sync import sync_to_async

            @sync_to_async
            def get_user():
                try:
                    return User.objects.get(id=user_id)
                except User.DoesNotExist:
                    return None

            user = await get_user()

            if not user:
                return RedirectResponse(url=f"{self.path}/login", status_code=302)

            # Handle form submission
            if request.method == "POST":
                form_data = await request.form()
                current_password = form_data.get('current_password', '')
                new_password = form_data.get('new_password', '')
                confirm_password = form_data.get('confirm_password', '')

                @sync_to_async
                def verify_and_change_password():
                    # Verify current password
                    if not check_password(current_password, user.password):
                        return False, "Current password is incorrect"

                    # Validate new password
                    if len(new_password) < 8:
                        return False, "New password must be at least 8 characters long"

                    if new_password != confirm_password:
                        return False, "New passwords do not match"

                    # Change password
                    user.password = make_password(new_password)
                    user.save()
                    return True, "Password changed successfully"

                try:
                    success, message = await verify_and_change_password()
                    if success:
                        success_message = f"✅ {message}! Please login again with your new password."
                        # Clear session to force re-login
                        request.session.clear()
                        # Redirect to login after a delay
                        return HTMLResponse(f'''
                            <html>
                            <head>
                                <meta http-equiv="refresh" content="2;url={self.path}/login">
                                <style>
                                    body {{
                                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                                        display: flex;
                                        align-items: center;
                                        justify-content: center;
                                        min-height: 100vh;
                                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                        margin: 0;
                                    }}
                                    .message {{
                                        background: white;
                                        padding: 2rem;
                                        border-radius: 0.5rem;
                                        text-align: center;
                                        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
                                    }}
                                    .success {{
                                        color: #22543d;
                                        font-size: 1.25rem;
                                        font-weight: 600;
                                        margin-bottom: 1rem;
                                    }}
                                    .redirect {{
                                        color: #718096;
                                        font-size: 0.875rem;
                                    }}
                                </style>
                            </head>
                            <body>
                                <div class="message">
                                    <div class="success">✅ Password Changed Successfully!</div>
                                    <div class="redirect">Redirecting to login page...</div>
                                </div>
                            </body>
                            </html>
                        ''')
                    else:
                        error_message = f"❌ {message}"
                except Exception as e:
                    error_message = f"❌ Error changing password: {str(e)}"

            # Generate change password page HTML
            success_html = f'<div class="success-message">{success_message}</div>' if success_message else ''
            error_html = f'<div class="error-message">{error_message}</div>' if error_message else ''

            content = f"""
            <div class="breadcrumbs">
                <a href="{self.path}">Home</a>
                <span> / </span>
                <a href="{self.path}/account">My Account</a>
                <span> / </span>
                <span>Change Password</span>
                <span style="margin-left: auto; display: flex; align-items: center; gap: 1rem;">
                    <a href="{self.path}/account" style="color: #667eea; text-decoration: none; font-weight: 500;">👤 {username}</a>
                    <a href="{self.path}/logout" style="color: #667eea; text-decoration: none; font-weight: 500;">🚪 Logout</a>
                </span>
            </div>

            <h2 style="font-size: 1.5rem; font-weight: 600; margin-bottom: 1.5rem;">🔑 Change Password</h2>

            {success_html}
            {error_html}

            <div class="card" style="max-width: 600px;">
                <div style="background: #edf2f7; border-left: 4px solid #4299e1; padding: 1rem; margin-bottom: 1.5rem; border-radius: 0.375rem;">
                    <p style="color: #2d3748; margin: 0; font-size: 0.875rem;">
                        <strong>Password Requirements:</strong><br>
                        • Minimum 8 characters<br>
                        • You'll need to login again after changing your password
                    </p>
                </div>

                <form method="POST" action="{self.path}/change-password">
                    <div class="form-group">
                        <label for="current_password">Current Password</label>
                        <input type="password" id="current_password" name="current_password" required autocomplete="current-password">
                    </div>

                    <div class="form-group">
                        <label for="new_password">New Password</label>
                        <input type="password" id="new_password" name="new_password" required minlength="8" autocomplete="new-password">
                    </div>

                    <div class="form-group">
                        <label for="confirm_password">Confirm New Password</label>
                        <input type="password" id="confirm_password" name="confirm_password" required minlength="8" autocomplete="new-password">
                    </div>

                    <div style="display: flex; gap: 1rem; margin-top: 1.5rem;">
                        <button type="submit" class="btn-primary">🔒 Change Password</button>
                        <a href="{self.path}/account" class="btn-secondary" style="display: inline-block; padding: 0.5rem 1rem; text-decoration: none;">Cancel</a>
                    </div>
                </form>
            </div>

            <style>
                .success-message {{
                    background: #c6f6d5;
                    border: 1px solid #48bb78;
                    color: #22543d;
                    padding: 1rem;
                    border-radius: 0.375rem;
                    margin-bottom: 1.5rem;
                    font-weight: 500;
                }}
                .error-message {{
                    background: #fed7d7;
                    border: 1px solid #fc8181;
                    color: #c53030;
                    padding: 1rem;
                    border-radius: 0.375rem;
                    margin-bottom: 1.5rem;
                    font-weight: 500;
                }}
                .btn-secondary {{
                    background: #e2e8f0;
                    color: #2d3748;
                    border: none;
                    border-radius: 0.375rem;
                    font-weight: 500;
                    cursor: pointer;
                    transition: background 0.2s;
                }}
                .btn-secondary:hover {{
                    background: #cbd5e0;
                }}
            </style>
            """

            return HTMLResponse(self._get_admin_html_template().format(
                title="Change Password",
                content=content
            ))

        except ImportError:
            return HTMLResponse("Django authentication not available", status_code=500)

    async def index(self, request: Request):
        """Admin panel home page."""
        # Check authentication
        auth_response = await self._require_auth(request)
        if auth_response:
            return auth_response

        username = request.session.get('admin_username', 'Admin')
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
            <span style="margin-left: auto; display: flex; align-items: center; gap: 1rem;">
                <a href="{self.path}/account" style="color: #667eea; text-decoration: none; font-weight: 500;">👤 {username}</a>
                <a href="{self.path}/change-password" style="color: #667eea; text-decoration: none; font-weight: 500;">🔑 Change Password</a>
                <a href="{self.path}/logout" style="color: #667eea; text-decoration: none; font-weight: 500;">🚪 Logout</a>
            </span>
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
        # Check authentication
        auth_response = await self._require_auth(request)
        if auth_response:
            return auth_response

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
            table_html += f"""
            <div class="content-box empty-state">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"></path>
                </svg>
                <h3 style="font-size: 1.125rem; font-weight: 600; margin-bottom: 0.5rem;">No {model_name}s yet</h3>
                <p style="margin-bottom: 1.5rem;">Get started by creating a new {model_name}</p>
                <a href="{self.path}/{model_name}/add" class="btn btn-primary">+ Create {model_name}</a>
            </div>
            """

        nav_header = self._get_nav_header(request, [model_name])

        content = f"""
        {nav_header}
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
        # Check authentication
        auth_response = await self._require_auth(request)
        if auth_response:
            return auth_response

        model_name = request.path_params["model"]
        object_id = request.path_params["id"]

        nav_header = self._get_nav_header(request, [
            (model_name, f"{self.path}/{model_name}"),
            f"#{object_id}"
        ])

        content = f"""
        {nav_header}
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
        # Check authentication
        auth_response = await self._require_auth(request)
        if auth_response:
            return auth_response

        model_name = request.path_params["model"]

        if model_name not in self.models:
            return HTMLResponse("Model not found", status_code=404)

        model = self.models[model_name]

        if request.method == "POST":
            # Handle form submission
            try:
                form_data = await request.form()
                data = dict(form_data)

                print(f"Form data received: {data}")  # Debug logging

                # Create object - process everything in sync context
                if hasattr(model, 'objects'):
                    from asgiref.sync import sync_to_async

                    def create_with_m2m():
                        # Separate m2m fields from regular fields
                        m2m_data = {}
                        regular_data = {}

                        if hasattr(model, '_meta'):
                            for key, value in data.items():
                                field = None
                                try:
                                    field = model._meta.get_field(key)
                                except Exception:
                                    continue

                                if field.get_internal_type() == 'ManyToManyField':
                                    # Store m2m fields for later
                                    if key not in m2m_data:
                                        m2m_data[key] = []
                                    m2m_data[key].append(value)
                                elif field.get_internal_type() in ['ForeignKey', 'OneToOneField']:
                                    # Convert ForeignKey ID to model instance
                                    if value and value != '':
                                        try:
                                            related_model = field.related_model
                                            related_obj = related_model.objects.get(id=int(value))
                                            regular_data[key] = related_obj
                                            print(f"DEBUG add: Converted {key} ID {value} to {related_model.__name__} instance: {related_obj}")
                                        except Exception as e:
                                            print(f"Error fetching {key} with ID {value}: {e}")
                                            regular_data[key] = None
                                    else:
                                        regular_data[key] = None
                                elif field.get_internal_type() == 'BooleanField':
                                    # Handle checkboxes - if not present, it's False
                                    regular_data[key] = True if value == '1' else False
                                else:
                                    regular_data[key] = value

                            # Add False for unchecked boolean fields
                            if hasattr(model._meta, 'get_fields'):
                                try:
                                    for field in model._meta.get_fields():
                                        if field.get_internal_type() == 'BooleanField' and field.name not in regular_data and not field.auto_created:
                                            regular_data[field.name] = False
                                except (AttributeError, TypeError):
                                    pass

                        print(f"Regular data: {regular_data}")  # Debug logging
                        print(f"M2M data: {m2m_data}")  # Debug logging

                        obj = model.objects.create(**regular_data)
                        print(f"Created object: {obj} (ID: {obj.id})")  # Debug logging

                        # Set m2m relationships
                        for field_name, values in m2m_data.items():
                            m2m_field = getattr(obj, field_name)
                            m2m_field.set(values)
                        return obj

                    created_obj = await sync_to_async(create_with_m2m)()
                    print(f"Successfully created {model_name} with ID: {created_obj.id}")

                return RedirectResponse(url=f"{self.path}/{model_name}", status_code=303)
            except Exception as e:
                import traceback
                error_message = str(e)
                print(f"Error creating {model_name}: {error_message}")
                traceback.print_exc()
                # Continue to show form with error
                error_html = f'<div style="background: #fee; border: 1px solid #fcc; padding: 1rem; margin-bottom: 1rem; border-radius: 0.375rem; color: #c00;"><strong>Error:</strong> {error_message}</div>'
        else:
            error_html = ''

        # Generate form fields in sync context using sync_to_async
        from asgiref.sync import sync_to_async
        form_fields = await sync_to_async(self._get_form_fields)(model)

        nav_header = self._get_nav_header(request, [
            (model_name, f"{self.path}/{model_name}"),
            "Add"
        ])

        content = f"""
        {nav_header}
        <div class="content-box">
            <h2 style="font-size: 1.5rem; font-weight: 600; margin-bottom: 1.5rem;">Add {model_name}</h2>
            {error_html}
            <form method="post">
                {form_fields}
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
        # Check authentication
        auth_response = await self._require_auth(request)
        if auth_response:
            return auth_response

        model_name = request.path_params["model"]
        object_id = request.path_params["id"]

        if model_name not in self.models:
            return HTMLResponse("Model not found", status_code=404)

        model = self.models[model_name]

        # Get the object
        obj = None
        if hasattr(model, 'objects'):
            from asgiref.sync import sync_to_async
            try:
                obj = await sync_to_async(model.objects.get)(id=object_id)
            except model.DoesNotExist:
                return HTMLResponse("Object not found", status_code=404)

        if request.method == "POST":
            # Handle form submission
            try:
                form_data = await request.form()
                data = dict(form_data)

                # Update object - process everything in sync context
                if obj:
                    def update_with_m2m():
                        # Separate m2m fields from regular fields
                        m2m_data = {}
                        regular_data = {}

                        if hasattr(model, '_meta'):
                            for key, value in data.items():
                                field = None
                                try:
                                    field = model._meta.get_field(key)
                                except Exception:
                                    continue

                                if field.get_internal_type() == 'ManyToManyField':
                                    # Store m2m fields for later
                                    if key not in m2m_data:
                                        m2m_data[key] = []
                                    m2m_data[key].append(value)
                                elif field.get_internal_type() in ['ForeignKey', 'OneToOneField']:
                                    # Convert ID to model instance
                                    if value and value != '':
                                        try:
                                            related_model = field.related_model
                                            related_obj = related_model.objects.get(id=int(value))
                                            regular_data[key] = related_obj
                                            print(f"DEBUG edit: Converted {key} ID {value} to {related_model.__name__} instance: {related_obj}")
                                        except Exception as e:
                                            print(f"Error fetching {key} with ID {value}: {e}")
                                            regular_data[key] = None
                                    else:
                                        regular_data[key] = None
                                else:
                                    # Handle checkboxes
                                    if field.get_internal_type() == 'BooleanField':
                                        regular_data[key] = True if value == '1' else False
                                    else:
                                        regular_data[key] = value

                            # Add False for unchecked boolean fields
                            if hasattr(model._meta, 'get_fields'):
                                try:
                                    for field in model._meta.get_fields():
                                        if field.get_internal_type() == 'BooleanField' and field.name not in regular_data and not field.auto_created:
                                            regular_data[field.name] = False
                                except (AttributeError, TypeError):
                                    pass

                        # Update regular fields
                        for key, value in regular_data.items():
                            if hasattr(obj, key):
                                setattr(obj, key, value)
                        obj.save()

                        # Update m2m relationships
                        for field_name, values in m2m_data.items():
                            if hasattr(obj, field_name):
                                m2m_field = getattr(obj, field_name)
                                m2m_field.set(values)
                        return obj

                    await sync_to_async(update_with_m2m)()

                return RedirectResponse(url=f"{self.path}/{model_name}", status_code=303)
            except Exception as e:
                import traceback
                error_message = str(e)
                print(f"Error updating {model_name}: {error_message}")
                traceback.print_exc()
                # Continue to show form with error
                error_html = f'<div style="background: #fee; border: 1px solid #fcc; padding: 1rem; margin-bottom: 1rem; border-radius: 0.375rem; color: #c00;"><strong>Error:</strong> {error_message}</div>'
        else:
            error_html = ''

        # Generate form fields with current values in sync context
        if obj:
            form_fields = await sync_to_async(self._get_form_fields_with_data)(model, obj)
        else:
            form_fields = await sync_to_async(self._get_form_fields)(model)

        nav_header = self._get_nav_header(request, [
            (model_name, f"{self.path}/{model_name}"),
            (f"#{object_id}", f"{self.path}/{model_name}/{object_id}"),
            "Edit"
        ])

        content = f"""
        {nav_header}
        <div class="content-box">
            <h2 style="font-size: 1.5rem; font-weight: 600; margin-bottom: 1.5rem;">Edit {model_name} #{object_id}</h2>
            {error_html}
            <form method="post">
                {form_fields}
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
        # Check authentication
        auth_response = await self._require_auth(request)
        if auth_response:
            return auth_response

        model_name = request.path_params["model"]
        object_id = request.path_params["id"]

        if model_name not in self.models:
            return HTMLResponse("Model not found", status_code=404)

        model = self.models[model_name]

        # Delete the object
        if hasattr(model, 'objects'):
            from asgiref.sync import sync_to_async
            try:
                obj = await sync_to_async(model.objects.get)(id=object_id)
                await sync_to_async(obj.delete)()
            except model.DoesNotExist:
                pass

        return RedirectResponse(url=f"{self.path}/{model_name}", status_code=303)
