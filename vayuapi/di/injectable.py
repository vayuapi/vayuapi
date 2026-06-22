"""
@injectable and @inject decorators for VayuAPI DI.
"""

from __future__ import annotations

import functools
import inspect
from typing import Any, Callable, Optional, Type, TypeVar

T = TypeVar("T")

# Registry of injectable classes (used for auto-discovery)
_INJECTABLE_REGISTRY: dict[Type, dict] = {}


def injectable(
    lifetime: str = "transient",
    *,
    alias: Optional[Type] = None,
):
    """
    Mark a class as injectable so it can be auto-registered in a DIContainer.

    Args:
        lifetime: 'singleton', 'transient', or 'scoped'  (default 'transient')
        alias: Optional interface/base-class to register the service under.

    Example::

        @injectable(lifetime="singleton")
        class Database:
            def __init__(self, config: Config):
                self.url = config.db_url

        @injectable(lifetime="scoped", alias=IUserRepository)
        class UserRepository(IUserRepository):
            def __init__(self, db: Database):
                self.db = db
    """
    from vayuapi.di.container import ServiceLifetime

    lifetime_map = {
        "singleton": ServiceLifetime.SINGLETON,
        "transient": ServiceLifetime.TRANSIENT,
        "scoped": ServiceLifetime.SCOPED,
    }

    def decorator(cls: Type[T]) -> Type[T]:
        sl = lifetime_map.get(lifetime.lower())
        if sl is None:
            raise ValueError(
                f"Invalid lifetime '{lifetime}'. Use 'singleton', 'transient', or 'scoped'."
            )
        _INJECTABLE_REGISTRY[cls] = {
            "lifetime": sl,
            "alias": alias,
        }
        cls.__injectable_lifetime__ = sl
        cls.__injectable_alias__ = alias
        return cls

    return decorator


def inject(container_attr: str = "container"):
    """
    Decorator that auto-resolves constructor parameters from a DIContainer
    attached to ``self.<container_attr>``.

    Mainly useful for class-based views / handlers that hold a reference
    to the application's container.

    Example::

        class UserService:
            container: DIContainer

            @inject()
            async def __init__(self, repo: UserRepository):
                self.repo = repo
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            container = getattr(self, container_attr, None)
            if container is None:
                return await func(self, *args, **kwargs)

            sig = inspect.signature(func)
            resolved: dict[str, Any] = {}

            for name, param in sig.parameters.items():
                if name in ("self", *kwargs):
                    continue
                annotation = param.annotation
                if annotation is inspect.Parameter.empty:
                    continue
                if container.is_registered(annotation):
                    resolved[name] = await container.resolve(annotation)

            return await func(self, *args, **{**resolved, **kwargs})

        return wrapper

    return decorator


def register_injectables(container) -> None:
    """
    Register all classes decorated with @injectable into the given container.

    Call this once during application startup after all modules are imported.

    Example::

        from vayuapi.di.injectable import register_injectables
        register_injectables(app.container)
    """
    from vayuapi.di.container import ServiceDescriptor

    for cls, meta in _INJECTABLE_REGISTRY.items():
        service_type = meta["alias"] if meta["alias"] is not None else cls
        descriptor = ServiceDescriptor(
            service_type=service_type,
            lifetime=meta["lifetime"],
            implementation_type=cls,
        )
        container.register(descriptor)


__all__ = [
    "injectable",
    "inject",
    "register_injectables",
]
