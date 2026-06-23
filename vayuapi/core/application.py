"""
VayuAPI main application class
High-performance async API framework built on Starlette
"""

import asyncio
import inspect
import typing
from typing import Any, Callable, Dict, List, Optional, Sequence, Type, Union

import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware as StarletteMiddleware
from starlette.routing import Route, Mount, WebSocketRoute
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send
from pydantic import BaseModel, ValidationError

from vayuapi.core.routing import Router
from vayuapi.core.middleware import Middleware, MiddlewareStack
from vayuapi.core.responses import JSONResponse
from vayuapi.admin.panel import AdminPanel
from vayuapi.scheduler.tasks import TaskScheduler
from vayuapi.core.docs import OpenAPIGenerator, get_swagger_ui_html, get_redoc_html


class VayuAPI:
    """
    Main VayuAPI application class.

    Ultra-fast async API framework with Django ORM support, admin panel,
    task scheduling, and extensive integrations.

    Example:
        ```python
        app = VayuAPI(title="My API", version="1.0.0")

        @app.get("/")
        async def home():
            return {"message": "Hello"}

        app.run()
        ```
    """

    def __init__(
        self,
        title: str = "VayuAPI",
        version: str = "0.1.0",
        description: str = "",
        debug: bool = False,
        docs_enabled: bool = True,
        docs_path: str = "/docs",
        redoc_path: str = "/redoc",
        openapi_path: str = "/openapi.json",
        admin_enabled: bool = False,
        admin_path: str = "/admin",
        scheduler_enabled: bool = False,
        cors_enabled: bool = True,
        allowed_origins: List[str] = None,
        middleware: List[Middleware] = None,
        lifespan: Optional[Callable] = None,
    ):
        """
        Initialize VayuAPI application.

        Args:
            title: Application title
            version: API version
            description: API description
            debug: Enable debug mode
            docs_enabled: Enable API documentation (Swagger UI)
            docs_path: Path for Swagger UI documentation
            redoc_path: Path for ReDoc documentation
            openapi_path: Path for OpenAPI JSON schema
            admin_enabled: Enable admin panel
            admin_path: Admin panel URL path
            scheduler_enabled: Enable task scheduler
            cors_enabled: Enable CORS middleware
            allowed_origins: List of allowed origins for CORS
            middleware: List of middleware to add
            lifespan: Lifespan context manager
        """
        self.title = title
        self.version = version
        self.description = description
        self.debug = debug

        # Initialize router
        self.router = Router()

        # Initialize middleware stack
        self.middleware_stack = MiddlewareStack()

        # Initialize storage for routes and middleware
        self._routes = []
        self._starlette_middleware = []

        # Add default middleware
        if cors_enabled:
            from starlette.middleware.cors import CORSMiddleware
            self.add_starlette_middleware(
                CORSMiddleware,
                allow_origins=allowed_origins or ["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        # Add custom middleware
        if middleware:
            for mw in middleware:
                self.add_middleware(mw)

        # Initialize components
        self.admin_enabled = admin_enabled
        self.admin_panel = None
        if admin_enabled:
            # Add session middleware for admin authentication
            from starlette.middleware.sessions import SessionMiddleware
            import secrets
            self.add_starlette_middleware(
                SessionMiddleware,
                secret_key=secrets.token_urlsafe(32)
            )
            self.admin_panel = AdminPanel(self, path=admin_path)

        self.scheduler_enabled = scheduler_enabled
        self.scheduler = None
        if scheduler_enabled:
            self.scheduler = TaskScheduler()

        # Documentation
        self.docs_enabled = docs_enabled
        self.docs_path = docs_path
        self.redoc_path = redoc_path
        self.openapi_path = openapi_path
        self.openapi_generator = None
        if docs_enabled:
            self.openapi_generator = OpenAPIGenerator(self)

        # ORM configuration
        self.orm_engine = None
        self.orm_config = {}

        # Starlette app (initialized on run)
        self._starlette_app = None
        self._lifespan = lifespan

        # Event handlers
        self._startup_handlers = []
        self._shutdown_handlers = []

        # Exception handlers
        from vayuapi.core.exceptions import ExceptionHandler
        self.exception_handler = ExceptionHandler()
#---------------------Routes------------------------------Added-------#
    @property
    def routes(self):
        """Get list of registered routes."""
        return self._routes

    @property
    def middleware(self):
        """Get list of registered Starlette middleware."""
        return self._starlette_middleware
#---------------------Routes------------------------------ended-------#
    def configure_orm(
        self,
        engine: str = "tortoise",
        db_url: str = None,
        databases: Dict = None,
        models: List[str] = None,
        **kwargs
    ):
        """
        Configure ORM engine.

        Args:
            engine: ORM engine ('django', 'tortoise', 'sqlalchemy')
            db_url: Database URL
            databases: Django-style databases configuration
            models: List of model modules
            **kwargs: Additional ORM-specific configuration
        """
        self.orm_engine = engine
        self.orm_config = {
            "db_url": db_url,
            "databases": databases,
            "models": models,
            **kwargs
        }

        if engine == "django":
            from vayuapi.orm.django_orm import configure_django
            configure_django(databases or {})
        elif engine == "tortoise":
            from vayuapi.orm.async_orm import configure_tortoise
            self._tortoise_config = {
                "db_url": db_url,
                "models": models or []
            }

    def on_event(self, event_type: str):
        """
        Decorator for registering event handlers.

        Supported events:
        - "startup": Called when the application starts
        - "shutdown": Called when the application shuts down

        Example:
            ```python
            @app.on_event("startup")
            async def startup():
                print("App started")

            @app.on_event("shutdown")
            async def shutdown():
                print("App stopped")
            ```

        Args:
            event_type: Type of event ('startup' or 'shutdown')

        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            if event_type == "startup":
                self._startup_handlers.append(func)
            elif event_type == "shutdown":
                self._shutdown_handlers.append(func)
            else:
                raise ValueError(f"Invalid event type: {event_type}. Use 'startup' or 'shutdown'")
            return func
        return decorator

    def add_middleware(self, middleware: Middleware):
        """Add custom middleware to the stack."""
        self.middleware_stack.add(middleware)

    def add_starlette_middleware(self, middleware_class: Type, **options):
        """Add Starlette middleware."""
        self._starlette_middleware.append(
            StarletteMiddleware(middleware_class, **options)
        )

    def add_exception_handler(self, exc_class: Type[Exception], handler: Callable):
        """
        Add a custom exception handler.

        Example:
            ```python
            from vayuapi import HTTPException

            async def custom_http_exception_handler(request, exc):
                return JSONResponse(
                    status_code=exc.status_code,
                    content={"error": exc.detail}
                )

            app.add_exception_handler(HTTPException, custom_http_exception_handler)

            # Custom exception
            class CustomError(Exception):
                pass

            async def custom_error_handler(request, exc):
                return JSONResponse(
                    status_code=500,
                    content={"error": "Custom error occurred"}
                )

            app.add_exception_handler(CustomError, custom_error_handler)
            ```

        Args:
            exc_class: Exception class to handle
            handler: Async function that handles the exception
        """
        self.exception_handler.add_handler(exc_class, handler)

    def route(
        self,
        path: str,
        methods: List[str] = None,
        name: str = None,
        **kwargs
    ):
        """
        Route decorator for registering endpoints.

        Example:
            ```python
            @app.route("/users", methods=["GET", "POST"])
            async def users(request):
                return {"users": []}
            ```
        """
        def decorator(func: Callable):
            self._add_route(path, func, methods or ["GET"], name, **kwargs)
            return func
        return decorator

    def api_route(
        self,
        path: str,
        methods: List[str] = None,
        name: str = None,
        **kwargs
    ):
        """
        API route decorator for registering endpoints (alias for route).
        Commonly used for multi-method routes in API gateways and microservices.

        Example:
            ```python
            @app.api_route("/users", methods=["GET", "POST"])
            async def users(request):
                if request.method == "GET":
                    return {"users": []}
                return {"created": True}
            ```
        """
        def decorator(func: Callable):
            self._add_route(path, func, methods or ["GET"], name, **kwargs)
            return func
        return decorator

    def get(self, path: str, **kwargs):
        """Decorator for GET requests."""
        return self.route(path, methods=["GET"], **kwargs)

    def post(self, path: str, **kwargs):
        """Decorator for POST requests."""
        return self.route(path, methods=["POST"], **kwargs)

    def put(self, path: str, **kwargs):
        """Decorator for PUT requests."""
        return self.route(path, methods=["PUT"], **kwargs)

    def delete(self, path: str, **kwargs):
        """Decorator for DELETE requests."""
        return self.route(path, methods=["DELETE"], **kwargs)

    def patch(self, path: str, **kwargs):
        """Decorator for PATCH requests."""
        return self.route(path, methods=["PATCH"], **kwargs)

    def websocket(self, path: str, **kwargs):
        """
        WebSocket route decorator.

        Example:
            ```python
            @app.websocket("/ws")
            async def websocket_endpoint(websocket):
                await websocket.accept()
                await websocket.send_json({"msg": "Connected"})
            ```
        """
        def decorator(func: Callable):
            self._add_websocket_route(path, func, **kwargs)
            return func
        return decorator

    def include_router(
        self,
        router: "Router",
        prefix: str = "",
        tags: List[str] = None,
        dependencies: List[Callable] = None,
    ):
        """
        Include a router's routes into the application.

        Example:
            ```python
            from vayuapi import Router

            # Create router
            users_router = Router(prefix="/users", tags=["users"])

            @users_router.get("/")
            async def get_users():
                return []

            # Include in app
            app.include_router(users_router)

            # Or with additional prefix
            app.include_router(users_router, prefix="/api/v1")
            ```

        Args:
            router: Router instance to include
            prefix: Additional prefix to prepend to all routes
            tags: Additional tags to add to all routes (for future OpenAPI enhancement)
            dependencies: Additional dependencies for all routes (for future enhancement)
        """
        # Import here to avoid circular import
        from vayuapi.core.routing import Router

        # Add all routes from the router
        for route in router.routes:
            # Combine prefixes
            full_path = prefix + route.path

            # Add the route to app
            self._add_route(
                path=full_path,
                endpoint=route.endpoint,
                methods=route.methods,
                name=route.name,
            )

    def mount(
        self,
        path: str,
        app: ASGIApp,
        name: str = None
    ):
        """
        Mount a sub-application or ASGI app (e.g., StaticFiles).

        Example:
            ```python
            from vayuapi import VayuAPI
            from vayuapi.staticfiles import StaticFiles

            app = VayuAPI()

            # Mount static files
            app.mount("/static", StaticFiles(directory="static"), name="static")

            # Mount another ASGI app
            sub_app = VayuAPI()
            app.mount("/sub", sub_app)
            ```

        Args:
            path: URL path to mount at
            app: ASGI application to mount
            name: Optional name for the mount
        """
        self._routes.append({
            "type": "mount",
            "path": path,
            "app": app,
            "name": name,
        })

    def _add_route(
        self,
        path: str,
        endpoint: Callable,
        methods: List[str],
        name: str = None,
        **kwargs
    ):
        """Internal method to add route."""
        # Wrap endpoint with Pydantic validation if needed
        wrapped_endpoint = self._wrap_endpoint(endpoint, path=path)

        self._routes.append({
            "type": "route",
            "path": path,
            "endpoint": wrapped_endpoint,
            "original_endpoint": endpoint,  # Store original for OpenAPI generation
            "methods": methods,
            "name": name or endpoint.__name__,
        })
        # Invalidate cached OpenAPI schema so new routes appear in /docs
        if self.openapi_generator:
            self.openapi_generator.invalidate()

    def _add_websocket_route(self, path: str, endpoint: Callable, **kwargs):
        """Internal method to add WebSocket route."""
        self._routes.append({
            "type": "websocket",
            "path": path,
            "endpoint": endpoint,
        })

    def _wrap_endpoint(self, endpoint: Callable, path: str = "") -> Callable:
        """
        Wrap endpoint with parameter extraction, validation, and dependency injection.
        Supports Path, Query, Header, Cookie, Body, Form, File, and Depends.
        OPTIMIZED: Fast-path for endpoints with no parameters.
        """
        import re
        sig = inspect.signature(endpoint)

        # Import parameter types
        from vayuapi.core.params import Param, ParamType
        from vayuapi.core.dependencies import Depends, Security, DependencyCache, solve_dependencies

        # Detect path parameter names from the URL template, e.g. /users/{user_id}
        path_param_names = set(re.findall(r"\{(\w+)\}", path))

        # Analyze parameters
        param_info = {}
        pydantic_body_params = {}
        has_form = False
        has_file = False

        for param_name, param in sig.parameters.items():
            if param_name == "request":
                param_info[param_name] = {"type": "request"}
                continue

            # Check for Param types (Path, Query, etc.)
            if isinstance(param.default, Param):
                param_info[param_name] = {
                    "type": "param",
                    "param": param.default,
                    "annotation": param.annotation,
                }
                if param.default.param_type == ParamType.FORM:
                    has_form = True
                elif param.default.param_type == ParamType.FILE:
                    has_file = True
            # Check for Depends/Security
            elif isinstance(param.default, (Depends, Security)):
                param_info[param_name] = {
                    "type": "dependency",
                    "dependency": param.default,
                }
            # Callable instance used directly as a dependency (e.g. jwt_bearer without Depends())
            elif (param.default is not inspect.Parameter.empty
                  and callable(param.default)
                  and not isinstance(param.default, type)
                  and hasattr(param.default, "__call__")):
                param_info[param_name] = {
                    "type": "dependency",
                    "dependency": Depends(param.default),
                }
            # Check for Pydantic models (body)
            elif (param.annotation != inspect.Parameter.empty and
                  isinstance(param.annotation, type) and
                  issubclass(param.annotation, BaseModel)):
                pydantic_body_params[param_name] = param.annotation
                param_info[param_name] = {
                    "type": "body",
                    "model": param.annotation,
                }
            else:
                annotation = param.annotation if param.annotation != inspect.Parameter.empty else None
                default = param.default if param.default != inspect.Parameter.empty else None
                # Detect path vs query param from the route template
                if param_name in path_param_names:
                    param_info[param_name] = {
                        "type": "path_param",
                        "annotation": annotation,
                        "default": default,
                    }
                else:
                    param_info[param_name] = {
                        "type": "query",
                        "annotation": annotation,
                        "default": default,
                    }
  #-----------------------------------------------------------------------------------------------------------------#
        # OPTIMIZATION: Fast-path for simple endpoints with no parameters
        is_simple_endpoint = len(param_info) == 0
        is_async = asyncio.iscoroutinefunction(endpoint)

        if is_simple_endpoint:
            # Ultra-fast path for simple endpoints
            if is_async:
                async def simple_wrapped(request: Request) -> Response:
                    try:
                        result = await endpoint()
                        # Fast response handling
                        if isinstance(result, Response):
                            return result
                        if isinstance(result, dict):
                            return JSONResponse(result)
                        if isinstance(result, list):
                            return JSONResponse(result)
                        if isinstance(result, BaseModel):
                            return JSONResponse(result.model_dump())
                        if result is None:
                            return JSONResponse({"message": "Success"})
                        return JSONResponse({"data": result})
                    except Exception as e:
                        return await self.exception_handler.handle(request, e)
                return simple_wrapped
            else:
                async def simple_wrapped_sync(request: Request) -> Response:
                    try:
                        result = endpoint()
                        # Fast response handling
                        if isinstance(result, Response):
                            return result
                        if isinstance(result, dict):
                            return JSONResponse(result)
                        if isinstance(result, list):
                            return JSONResponse(result)
                        if isinstance(result, BaseModel):
                            return JSONResponse(result.model_dump())
                        if result is None:
                            return JSONResponse({"message": "Success"})
                        return JSONResponse({"data": result})
                    except Exception as e:
                        return await self.exception_handler.handle(request, e)
                return simple_wrapped_sync

#------------------------------------------------------------------------------------------------------------#

        # Standard path for endpoints with parameters
        async def wrapped(request: Request) -> Response:
            try:
                kwargs = {}
                dependency_cache = DependencyCache()

                # Extract parameters
                for param_name, info in param_info.items():
                    if info["type"] == "request":
                        kwargs[param_name] = request
                        continue

                    if info["type"] == "param":
                        param_obj = info["param"]
                        value = None

                        # Extract based on param type
                        if param_obj.param_type == ParamType.PATH:
                            value = request.path_params.get(param_name)
                        elif param_obj.param_type == ParamType.QUERY:
                            value = request.query_params.get(param_obj.alias or param_name)
                        elif param_obj.param_type == ParamType.HEADER:
                            header_name = param_obj.alias or param_name
                            if hasattr(param_obj, 'convert_underscores') and param_obj.convert_underscores:
                                header_name = header_name.replace('_', '-')
                            value = request.headers.get(header_name)
                        elif param_obj.param_type == ParamType.COOKIE:
                            value = request.cookies.get(param_obj.alias or param_name)
                        elif param_obj.param_type == ParamType.FORM:
                            form_data = await request.form()
                            value = form_data.get(param_obj.alias or param_name)
                        elif param_obj.param_type == ParamType.FILE:
                            form_data = await request.form()
                            field_name = param_obj.alias or param_name

                            # Check if annotation is List type for multiple files
                            is_list = False
                            if "annotation" in info and info["annotation"] != inspect.Parameter.empty:
                                annotation = info["annotation"]
                                if hasattr(annotation, '__origin__'):
                                    from typing import get_origin, get_args
                                    origin = get_origin(annotation)
                                    if origin is list or (hasattr(origin, '__name__') and origin.__name__ == 'list'):
                                        is_list = True

                            from vayuapi.core.uploads import UploadFile

                            if is_list:
                                # Handle multiple files with the same field name
                                # Starlette form() returns all values, we need to filter for files
                                file_list = []
                                for key, file_data in form_data.multi_items():
                                    if key == field_name:
                                        if hasattr(file_data, 'filename'):  # It's a file
                                            file_list.append(UploadFile(file=file_data))
                                value = file_list if file_list else None
                            else:
                                # Single file
                                file_data = form_data.get(field_name)
                                if file_data and hasattr(file_data, 'filename'):
                                    value = UploadFile(file=file_data)
                                else:
                                    value = None

                        # Handle default values
                        if value is None and param_obj.default != ...:
                            value = param_obj.default
                        elif value is None and param_obj.default == ...:
                            from vayuapi.core.exceptions import RequestValidationError
                            raise RequestValidationError(
                                f"Missing required parameter: {param_name}"
                            )

                        # Type conversion (skip for files and complex types)
                        if value is not None and "annotation" in info and info["annotation"] != inspect.Parameter.empty:
                            # Skip conversion for UploadFile objects
                            from vayuapi.core.uploads import UploadFile
                            if isinstance(value, (UploadFile, list)):
                                # Already the right type or list of files
                                pass
                            else:
                                try:
                                    annotation = info["annotation"]
                                    # Handle Optional types
                                    if hasattr(annotation, '__origin__'):
                                        if annotation.__origin__ is Union:
                                            # Get the non-None type
                                            args = [a for a in annotation.__args__ if a is not type(None)]
                                            if args:
                                                annotation = args[0]

                                    if annotation in (int, float, str, bool):
                                        value = annotation(value)
                                except (ValueError, TypeError):
                                    pass

                        kwargs[param_name] = value

                    elif info["type"] == "dependency":
                        # Resolve dependency
                        dep_values = await solve_dependencies(
                            endpoint if info["dependency"].dependency is None else info["dependency"].dependency,
                            request,
                            dependency_cache
                        )
                        if info["dependency"].dependency:
                            # Call the dependency — detect async via the callable
                            # itself OR via its __call__ method (handles class instances
                            # with async def __call__, e.g. JWTBearer).
                            dep_fn = info["dependency"].dependency
                            is_async = (
                                asyncio.iscoroutinefunction(dep_fn)
                                or asyncio.iscoroutinefunction(getattr(dep_fn, "__call__", None))
                            )
                            if is_async:
                                dep_result = await dep_fn(**dep_values)
                            else:
                                dep_result = dep_fn(**dep_values)
                            # Await if result is still a coroutine (safety net)
                            if asyncio.iscoroutine(dep_result):
                                dep_result = await dep_result

                            # Drive generator / async-generator dependencies (yield-based cleanup)
                            import inspect as _inspect
                            if _inspect.isasyncgen(dep_result):
                                dep_result = await dep_result.__anext__()
                            elif _inspect.isgenerator(dep_result):
                                dep_result = next(dep_result)

                            kwargs[param_name] = dep_result
                        else:
                            kwargs[param_name] = dep_values

                    elif info["type"] == "body":
                        # Parse JSON body
                        try:
                            body = await request.json()
                            kwargs[param_name] = info["model"](**body)
                        except Exception as e:
                            from vayuapi.core.exceptions import RequestValidationError
                            raise RequestValidationError(f"Invalid request body: {str(e)}")

                    elif info["type"] == "path_param":
                        # Extract from URL path parameters and type-coerce
                        raw = request.path_params.get(param_name)
                        if raw is None:
                            raw = info["default"]
                        if raw is not None and info["annotation"] is not None:
                            ann = info["annotation"]
                            if ann in (int, float, bool):
                                try:
                                    raw = ann(raw)
                                except (ValueError, TypeError):
                                    from vayuapi.core.exceptions import RequestValidationError
                                    raise RequestValidationError(
                                        f"Path parameter '{param_name}' must be {ann.__name__}, got {raw!r}"
                                    )
                        kwargs[param_name] = raw

                    elif info["type"] == "query":
                        # Default query parameter handling with type coercion
                        value = request.query_params.get(param_name)
                        if value is None:
                            value = info["default"]
                        if value is not None and info.get("annotation") is not None:
                            ann = info["annotation"]
                            if ann in (int, float, bool):
                                try:
                                    value = ann(value)
                                except (ValueError, TypeError):
                                    pass  # leave as-is; let the endpoint handle it
                        kwargs[param_name] = value

                # Call endpoint
                if asyncio.iscoroutinefunction(endpoint):
                    result = await endpoint(**kwargs)
                else:
                    result = endpoint(**kwargs)

                # Handle response
                if isinstance(result, Response):
                    return result
                elif isinstance(result, BaseModel):
                    return JSONResponse(result.model_dump())
                elif isinstance(result, (dict, list)):
                    return JSONResponse(result)
                elif result is None:
                    return JSONResponse({"message": "Success"})
                else:
                    return JSONResponse({"data": result})

            except ValidationError as e:
                from vayuapi.core.exceptions import RequestValidationError
                validation_error = RequestValidationError(e.errors())
                return await self.exception_handler.handle(request, validation_error)
            except Exception as e:
                # Use exception handler
                return await self.exception_handler.handle(request, e)

        return wrapped

    def _build_starlette_app(self) -> Starlette:
        """Build Starlette application with all routes and middleware."""
        # Convert routes to Starlette format
        starlette_routes = []

        for route_info in self._routes:
            if route_info["type"] == "route":
                starlette_routes.append(
                    Route(
                        route_info["path"],
                        endpoint=route_info["endpoint"],
                        methods=route_info["methods"],
                        name=route_info.get("name"),
                    )
                )
            elif route_info["type"] == "websocket":
                starlette_routes.append(
                    WebSocketRoute(
                        route_info["path"],
                        endpoint=route_info["endpoint"],
                    )
                )
            elif route_info["type"] == "mount":
                starlette_routes.append(
                    Mount(
                        route_info["path"],
                        app=route_info["app"],
                        name=route_info.get("name"),
                    )
                )

        # Add admin routes if enabled
        if self.admin_panel:
            starlette_routes.extend(self.admin_panel.get_routes())

        # Add documentation routes if enabled
        if self.docs_enabled and self.openapi_generator:
            from starlette.responses import HTMLResponse

            # OpenAPI JSON schema — async so Starlette runs it on the event loop
            async def openapi_schema(request: Request):
                try:
                    schema = self.openapi_generator.generate_schema()
                    return JSONResponse(schema)
                except Exception as exc:
                    return JSONResponse(
                        {"detail": f"Failed to generate OpenAPI schema: {exc}"},
                        status_code=500,
                    )

            # Swagger UI
            def swagger_ui(request: Request):
                html = get_swagger_ui_html(
                    openapi_url=self.openapi_path,
                    title=f"{self.title} - Swagger UI"
                )
                return HTMLResponse(html)

            # ReDoc
            def redoc_ui(request: Request):
                html = get_redoc_html(
                    openapi_url=self.openapi_path,
                    title=f"{self.title} - ReDoc"
                )
                return HTMLResponse(html)

            starlette_routes.append(Route(self.openapi_path, openapi_schema, methods=["GET"]))
            starlette_routes.append(Route(self.docs_path, swagger_ui, methods=["GET"]))
            starlette_routes.append(Route(self.redoc_path, redoc_ui, methods=["GET"]))

        # Wrap custom VayuAPI middleware stack as a Starlette BaseHTTPMiddleware
        # so it participates in the normal Starlette middleware chain.
        if self.middleware_stack.middleware:
            from starlette.middleware.base import BaseHTTPMiddleware
            from vayuapi.core.exceptions import HTTPException as VayuHTTPException
            from starlette.exceptions import HTTPException as StarletteHTTPException

            mw_stack = self.middleware_stack  # capture reference
            exc_handler = self.exception_handler  # capture reference

            class _VayuMiddlewareWrapper(BaseHTTPMiddleware):
                async def dispatch(self, request, call_next):
                    try:
                        return await mw_stack.process(request, call_next)
                    except (VayuHTTPException, StarletteHTTPException) as e:
                        return await exc_handler.handle(request, e)
                    except Exception as e:
                        return await exc_handler.handle(request, e)

            starlette_middleware = [
                StarletteMiddleware(_VayuMiddlewareWrapper),
            ] + list(self._starlette_middleware)
        else:
            starlette_middleware = list(self._starlette_middleware)

        # Create Starlette app
        app = Starlette(
            debug=self.debug,
            routes=starlette_routes,
            middleware=starlette_middleware,
            lifespan=self._create_lifespan(),
        )

        return app

    def _create_lifespan(self):
        """Create lifespan context manager."""
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def lifespan(app):
            # Startup
            if self.orm_engine == "tortoise":
                from tortoise import Tortoise
                await Tortoise.init(
                    db_url=self.orm_config.get("db_url"),
                    modules={"models": self.orm_config.get("models", [])}
                )
                await Tortoise.generate_schemas()

            if self.scheduler:
                await self.scheduler.start()

            # Execute startup event handlers
            for handler in self._startup_handlers:
                if inspect.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()

            if self._lifespan:
                async with self._lifespan(app):
                    yield
            else:
                yield

            # Shutdown
            # Execute shutdown event handlers
            for handler in self._shutdown_handlers:
                if inspect.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()

            if self.orm_engine == "tortoise":
                from tortoise import Tortoise
                await Tortoise.close_connections()

            if self.scheduler:
                await self.scheduler.stop()

        return lifespan

    def run(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        reload: bool = None,
        workers: int = 1,
        log_level: str = "info",
        **kwargs
    ):
        """
        Run the application with uvicorn.

        Args:
            host: Host to bind to
            port: Port to bind to
            reload: Enable auto-reload (defaults to debug mode)
            workers: Number of worker processes
            log_level: Log level
            **kwargs: Additional uvicorn configuration

        Note:
            When using reload=True, it's recommended to run via CLI:
            `uvicorn your_app:app --reload` instead of app.run(reload=True)
        """
        if reload is None:
            reload = self.debug

        # Reload mode requires running via CLI with import string
        if reload and workers > 1:
            print("⚠️  WARNING: Cannot use both reload=True and workers>1")
            print("   Setting workers=1 for reload mode")
            workers = 1

        if reload:
            print("⚠️  WARNING: Reload mode doesn't work with app.run()")
            print("   For auto-reload, run: uvicorn <module>:app --reload")
            print("   Disabling reload for this session...")
            reload = False

        # Build Starlette app
        self._starlette_app = self._build_starlette_app()

        # Run with uvicorn
        import sys
        use_uvloop = sys.platform != 'win32'  # uvloop not supported on Windows

        uvicorn.run(
            self._starlette_app,
            host=host,
            port=port,
            reload=reload,
            workers=workers,
            log_level=log_level,
            loop="uvloop" if use_uvloop else "asyncio",
            **kwargs
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        """ASGI interface."""
        if self._starlette_app is None:
            self._starlette_app = self._build_starlette_app()

        await self._starlette_app(scope, receive, send)
