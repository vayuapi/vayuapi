"""
Routing system for VayuAPI
"""

from typing import Any, Callable, Dict, List, Optional, Sequence, Type, Union
from starlette.routing import Route as StarletteRoute, Mount
from pydantic import BaseModel


class Route:
    """
    Route definition for VayuAPI.

    Example:
        ```python
        route = Route(
            path="/users",
            endpoint=get_users,
            methods=["GET"],
            name="get_users",
            tags=["users"],
            response_model=List[User],
        )
        ```
    """

    def __init__(
        self,
        path: str,
        endpoint: Callable,
        methods: List[str] = None,
        name: str = None,
        include_in_schema: bool = True,
        response_model: Type[BaseModel] = None,
        status_code: int = 200,
        tags: List[str] = None,
        summary: str = None,
        description: str = None,
        response_description: str = "Successful Response",
        deprecated: bool = False,
        dependencies: List[Callable] = None,
    ):
        self.path = path
        self.endpoint = endpoint
        self.methods = methods or ["GET"]
        self.name = name
        self.include_in_schema = include_in_schema
        self.response_model = response_model
        self.status_code = status_code
        self.tags = tags or []
        self.summary = summary
        self.description = description
        self.response_description = response_description
        self.deprecated = deprecated
        self.dependencies = dependencies or []

    def to_starlette_route(self) -> StarletteRoute:
        """Convert to Starlette Route."""
        return StarletteRoute(
            self.path,
            endpoint=self.endpoint,
            methods=self.methods,
            name=self.name,
        )


class Router:
    """
    Router for organizing API routes into groups.

    FastAPI-compatible with full feature support.

    Example:
        ```python
        from vayuapi import Router

        router = Router(
            prefix="/api/v1",
            tags=["users"],
            dependencies=[verify_token],
        )

        @router.get("/users", response_model=List[User])
        async def get_users():
            return await User.all()

        @router.post("/users", status_code=201)
        async def create_user(user: UserCreate):
            return await User.create(**user.dict())

        # Include in main app
        app.include_router(router)

        # Nest routers
        api_router = Router(prefix="/api")
        api_router.include_router(router)
        ```
    """

    def __init__(
        self,
        prefix: str = "",
        tags: List[str] = None,
        dependencies: List[Callable] = None,
        default_response_class: Type = None,
        responses: Dict[Union[int, str], Dict[str, Any]] = None,
        deprecated: bool = False,
        include_in_schema: bool = True,
        redirect_slashes: bool = True,
    ):
        """
        Initialize Router.

        Args:
            prefix: URL prefix for all routes in this router
            tags: Tags for OpenAPI documentation
            dependencies: Dependencies to apply to all routes
            default_response_class: Default response class for all routes
            responses: OpenAPI responses documentation
            deprecated: Mark all routes as deprecated
            include_in_schema: Include routes in OpenAPI schema
            redirect_slashes: Redirect requests with trailing slashes
        """
        self.prefix = prefix.rstrip("/") if prefix else ""
        self.tags = tags or []
        self.dependencies = dependencies or []
        self.default_response_class = default_response_class
        self.responses = responses or {}
        self.deprecated = deprecated
        self.include_in_schema = include_in_schema
        self.redirect_slashes = redirect_slashes
        self.routes: List[Route] = []
        self.routers: List["Router"] = []

    def add_route(
        self,
        path: str,
        endpoint: Callable,
        methods: List[str] = None,
        name: str = None,
        response_model: Type[BaseModel] = None,
        status_code: int = None,
        tags: List[str] = None,
        summary: str = None,
        description: str = None,
        response_description: str = None,
        deprecated: bool = None,
        include_in_schema: bool = None,
        dependencies: List[Callable] = None,
        **kwargs
    ):
        """
        Add a route to the router.

        Args:
            path: URL path (will be prefixed with router prefix)
            endpoint: Endpoint function
            methods: HTTP methods
            name: Route name
            response_model: Pydantic model for response serialization
            status_code: Default status code
            tags: Tags for OpenAPI docs (inherited from router if not specified)
            summary: Short description for OpenAPI docs
            description: Long description for OpenAPI docs
            response_description: Description of successful response
            deprecated: Mark route as deprecated
            include_in_schema: Include in OpenAPI schema
            dependencies: Additional dependencies for this route
            **kwargs: Additional route parameters
        """
        full_path = self.prefix + path

        # Merge tags
        route_tags = tags if tags is not None else self.tags

        # Merge dependencies
        all_dependencies = self.dependencies + (dependencies or [])

        # Use router defaults if not specified
        if deprecated is None:
            deprecated = self.deprecated
        if include_in_schema is None:
            include_in_schema = self.include_in_schema

        route = Route(
            path=full_path,
            endpoint=endpoint,
            methods=methods or ["GET"],
            name=name,
            include_in_schema=include_in_schema,
            response_model=response_model,
            status_code=status_code or 200,
            tags=route_tags,
            summary=summary,
            description=description,
            response_description=response_description,
            deprecated=deprecated,
            dependencies=all_dependencies,
            **kwargs
        )
        self.routes.append(route)

    def api_route(
        self,
        path: str,
        methods: List[str] = None,
        **kwargs
    ):
        """
        Decorator for adding routes.

        Example:
            ```python
            @router.api_route("/items", methods=["GET", "POST"])
            async def items():
                return {"items": []}
            ```
        """
        def decorator(func: Callable):
            self.add_route(path, func, methods=methods, **kwargs)
            return func
        return decorator

    def get(
        self,
        path: str,
        response_model: Type[BaseModel] = None,
        status_code: int = 200,
        **kwargs
    ):
        """
        Decorator for GET requests.

        Example:
            ```python
            @router.get("/users", response_model=List[User])
            async def get_users():
                return await User.all()
            ```
        """
        def decorator(func: Callable):
            self.add_route(
                path,
                func,
                methods=["GET"],
                response_model=response_model,
                status_code=status_code,
                **kwargs
            )
            return func
        return decorator

    def post(
        self,
        path: str,
        response_model: Type[BaseModel] = None,
        status_code: int = 201,
        **kwargs
    ):
        """
        Decorator for POST requests.

        Example:
            ```python
            @router.post("/users", response_model=User, status_code=201)
            async def create_user(user: UserCreate):
                return await User.create(**user.dict())
            ```
        """
        def decorator(func: Callable):
            self.add_route(
                path,
                func,
                methods=["POST"],
                response_model=response_model,
                status_code=status_code,
                **kwargs
            )
            return func
        return decorator

    def put(
        self,
        path: str,
        response_model: Type[BaseModel] = None,
        status_code: int = 200,
        **kwargs
    ):
        """
        Decorator for PUT requests.

        Example:
            ```python
            @router.put("/users/{user_id}", response_model=User)
            async def update_user(user_id: int, user: UserUpdate):
                return await User.update(user_id, **user.dict())
            ```
        """
        def decorator(func: Callable):
            self.add_route(
                path,
                func,
                methods=["PUT"],
                response_model=response_model,
                status_code=status_code,
                **kwargs
            )
            return func
        return decorator

    def delete(
        self,
        path: str,
        response_model: Type[BaseModel] = None,
        status_code: int = 204,
        **kwargs
    ):
        """
        Decorator for DELETE requests.

        Example:
            ```python
            @router.delete("/users/{user_id}", status_code=204)
            async def delete_user(user_id: int):
                await User.delete(user_id)
                return None
            ```
        """
        def decorator(func: Callable):
            self.add_route(
                path,
                func,
                methods=["DELETE"],
                response_model=response_model,
                status_code=status_code,
                **kwargs
            )
            return func
        return decorator

    def patch(
        self,
        path: str,
        response_model: Type[BaseModel] = None,
        status_code: int = 200,
        **kwargs
    ):
        """
        Decorator for PATCH requests.

        Example:
            ```python
            @router.patch("/users/{user_id}", response_model=User)
            async def patch_user(user_id: int, data: dict):
                return await User.patch(user_id, data)
            ```
        """
        def decorator(func: Callable):
            self.add_route(
                path,
                func,
                methods=["PATCH"],
                response_model=response_model,
                status_code=status_code,
                **kwargs
            )
            return func
        return decorator

    def options(
        self,
        path: str,
        **kwargs
    ):
        """
        Decorator for OPTIONS requests.

        Example:
            ```python
            @router.options("/users")
            async def users_options():
                return {"allowed_methods": ["GET", "POST"]}
            ```
        """
        def decorator(func: Callable):
            self.add_route(path, func, methods=["OPTIONS"], **kwargs)
            return func
        return decorator

    def head(
        self,
        path: str,
        **kwargs
    ):
        """
        Decorator for HEAD requests.

        Example:
            ```python
            @router.head("/users")
            async def users_head():
                return None
            ```
        """
        def decorator(func: Callable):
            self.add_route(path, func, methods=["HEAD"], **kwargs)
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
        Include another router.

        Example:
            ```python
            # Create sub-router
            users_router = Router(prefix="/users", tags=["users"])

            @users_router.get("/")
            async def get_users():
                return []

            # Include in main router or app
            api_router = Router(prefix="/api/v1")
            api_router.include_router(users_router)

            # Or include in app
            app.include_router(users_router)
            ```

        Args:
            router: Router to include
            prefix: Additional prefix to add
            tags: Additional tags to add
            dependencies: Additional dependencies to add
        """
        # Create a copy with updated prefix
        included_router = Router(
            prefix=self.prefix + prefix + router.prefix,
            tags=self.tags + (tags or []) + router.tags,
            dependencies=self.dependencies + (dependencies or []) + router.dependencies,
            default_response_class=router.default_response_class or self.default_response_class,
            responses={**self.responses, **router.responses},
            deprecated=router.deprecated or self.deprecated,
            include_in_schema=router.include_in_schema and self.include_in_schema,
        )

        # Copy routes with updated settings
        for route in router.routes:
            # Create new route with merged settings
            new_route = Route(
                path=route.path.replace(router.prefix, included_router.prefix, 1) if router.prefix else included_router.prefix + route.path,
                endpoint=route.endpoint,
                methods=route.methods,
                name=route.name,
                include_in_schema=route.include_in_schema and included_router.include_in_schema,
                response_model=route.response_model,
                status_code=route.status_code,
                tags=included_router.tags + route.tags,
                summary=route.summary,
                description=route.description,
                response_description=route.response_description,
                deprecated=route.deprecated or included_router.deprecated,
                dependencies=included_router.dependencies + route.dependencies,
            )
            self.routes.append(new_route)

        # Recursively include nested routers
        for nested_router in router.routers:
            included_router.include_router(nested_router)

        self.routers.append(router)
        for route in router.routes:
            self.routes.append(route)
