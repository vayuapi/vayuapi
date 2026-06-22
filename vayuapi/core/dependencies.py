"""
Dependency injection system for VayuAPI

"""

from __future__ import annotations

from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Generator,
    Iterator,
    AsyncIterator,
    Optional,
    Sequence,
    Type,
    TypeVar,
    overload,
)
import inspect

T = TypeVar("T")


class Depends:
    """
    Dependency injection marker.

    Use to declare dependencies that should be resolved and injected
    into endpoint functions.

    Example:
        ```python
        from vayuapi import Depends

        # Simple dependency
        def get_db():
            db = Database()
            try:
                yield db
            finally:
                db.close()

        @app.get("/users/")
        async def get_users(db = Depends(get_db)):
            return db.query_users()

        # Dependency with parameters
        def pagination(skip: int = 0, limit: int = 10):
            return {"skip": skip, "limit": limit}

        @app.get("/items/")
        async def get_items(params = Depends(pagination)):
            return {"skip": params["skip"], "limit": params["limit"]}

        # Class-based dependency
        class DatabaseDependency:
            def __init__(self):
                self.db = Database()

            def __call__(self):
                return self.db

        @app.get("/products/")
        async def get_products(db = Depends(DatabaseDependency())):
            return db.query_products()
        ```

    Args:
        dependency: Callable that returns the dependency value
        use_cache: Whether to cache the dependency result per request
    """

    def __init__(
        self,
        dependency: Optional[Callable] = None,
        *,
        use_cache: bool = True,
    ):
        self.dependency = dependency
        self.use_cache = use_cache

    # Allow `Depends[Session]` as a valid type annotation so type checkers
    # understand the resolved type without raising "unresolved attribute".
    def __class_getitem__(cls, item):
        return cls

    def __repr__(self):
        dep = self.dependency.__name__ if self.dependency else "None"
        return f"Depends({dep})"


# ---------------------------------------------------------------------------
# Type-safe factory — use instead of bare Depends() when you want the IDE /
# type checker to infer the resolved type from the dependency's return annotation.
#
#   from vayuapi.core.dependencies import depends
#
#   def get_db() -> Session: ...
#
#   @app.get("/users")
#   async def list_users(db: Session = depends(get_db)):
#       db.query(...)   # ← no "unresolved attribute" warning
# ---------------------------------------------------------------------------

@overload
def depends(dependency: Callable[..., AsyncGenerator[T, None]], *, use_cache: bool = ...) -> T: ...
@overload
def depends(dependency: Callable[..., AsyncIterator[T]], *, use_cache: bool = ...) -> T: ...
@overload
def depends(dependency: Callable[..., Generator[T, None, None]], *, use_cache: bool = ...) -> T: ...
@overload
def depends(dependency: Callable[..., Iterator[T]], *, use_cache: bool = ...) -> T: ...
@overload
def depends(dependency: Callable[..., T], *, use_cache: bool = ...) -> T: ...


def depends(dependency: Callable[..., Any], *, use_cache: bool = True) -> Any:  # type: ignore[misc]
    """
    Type-aware wrapper around ``Depends``.

    Identical at runtime to ``Depends(dependency, use_cache=use_cache)`` but
    the return annotation lets Pylance / mypy infer the resolved type from
    the dependency callable's own return annotation, eliminating
    "unresolved attribute reference" errors.

    Example::

        from sqlalchemy.orm import Session
        from vayuapi.core.dependencies import depends

        def get_db() -> Session:
            db = SessionLocal()
            try:
                yield db
            finally:
                db.close()

        @app.get("/users")
        async def list_users(db: Session = depends(get_db)):
            return db.query(User).all()   # ← no IDE warning
    """
    return Depends(dependency, use_cache=use_cache)  # type: ignore[return-value]


class Security:
    """
    Security dependency marker.

    Similar to Depends but specifically for security/authentication.

    Example:
        ```python
        from vayuapi import Security
        from vayuapi.security import HTTPBearer

        security = HTTPBearer()

        @app.get("/protected/")
        async def protected_route(token = Security(security)):
            return {"token": token}

        # With scopes
        def verify_token(
            credentials = Security(security, scopes=["admin"])
        ):
            # Verify token and scopes
            return credentials

        @app.get("/admin/")
        async def admin_route(user = Depends(verify_token)):
            return {"user": user}
        ```

    Args:
        dependency: Callable that returns the security credentials
        scopes: Required security scopes
        use_cache: Whether to cache the dependency result per request
    """

    def __init__(
        self,
        dependency: Optional[Callable] = None,
        *,
        scopes: Optional[Sequence[str]] = None,
        use_cache: bool = True,
    ):
        self.dependency = dependency
        self.scopes = list(scopes) if scopes else []
        self.use_cache = use_cache

    def __repr__(self):
        dep = self.dependency.__name__ if self.dependency else "None"
        return f"Security({dep}, scopes={self.scopes})"


class DependencyCache:
    """
    Cache for dependency results during request processing.

    Ensures that dependencies are only resolved once per request.
    """

    def __init__(self):
        self._cache = {}

    def get(self, key: str) -> Any:
        """Get cached dependency result."""
        return self._cache.get(key)

    def set(self, key: str, value: Any):
        """Set cached dependency result."""
        self._cache[key] = value

    def has(self, key: str) -> bool:
        """Check if dependency is cached."""
        return key in self._cache

    def clear(self):
        """Clear cache."""
        self._cache.clear()


async def solve_dependencies(
    endpoint: Callable,
    request: Any,
    dependency_cache: DependencyCache,
) -> dict:
    """
    Solve all dependencies for an endpoint.

    Args:
        endpoint: The endpoint function
        request: The request object
        dependency_cache: Cache for dependency results

    Returns:
        Dictionary of resolved dependencies
    """
    import asyncio

    sig = inspect.signature(endpoint)
    resolved = {}

    for param_name, param in sig.parameters.items():
        if param_name == "request":
            resolved[param_name] = request
            continue

        # Check if parameter has a Depends or Security default
        if isinstance(param.default, (Depends, Security)):
            dep = param.default

            # Generate cache key
            cache_key = f"{id(dep.dependency)}_{param_name}"

            # Check cache
            if dep.use_cache and dependency_cache.has(cache_key):
                resolved[param_name] = dependency_cache.get(cache_key)
                continue

            # Resolve dependency
            if dep.dependency:
                # Check if dependency is a callable
                if callable(dep.dependency):
                    # Recursively solve dependencies for the dependency function
                    dep_params = await solve_dependencies(
                        dep.dependency,
                        request,
                        dependency_cache
                    )

                    # Call dependency
                    if asyncio.iscoroutinefunction(dep.dependency):
                        result = await dep.dependency(**dep_params)
                    else:
                        result = dep.dependency(**dep_params)

                    # Handle generators (for cleanup)
                    if inspect.isgenerator(result) or inspect.isasyncgen(result):
                        if inspect.isasyncgen(result):
                            result = await result.__anext__()
                        else:
                            result = next(result)

                    # Cache result
                    if dep.use_cache:
                        dependency_cache.set(cache_key, result)

                    resolved[param_name] = result

    return resolved


__all__ = [
    "Depends",
    "Security",
    "DependencyCache",
    "solve_dependencies",
]
