"""
ServiceProvider — thin wrapper that exposes resolve() for use inside
request handlers and middleware via the VayuAPI `Depends` mechanism.
"""

from __future__ import annotations

from typing import Any, Optional, Type, TypeVar

T = TypeVar("T")


class ServiceProvider:
    """
    High-level API for resolving services from a DIContainer within a
    request scope.

    VayuAPI creates one ServiceProvider per request and injects it when
    a handler declares ``provider: ServiceProvider`` as a parameter or
    uses ``Depends(get_service_provider)``.

    Example::

        from vayuapi.di import ServiceProvider

        @app.get("/users")
        async def list_users(provider: ServiceProvider = Depends(get_provider)):
            repo = await provider.get(UserRepository)
            return await repo.all()
    """

    def __init__(self, container, scope=None):
        from vayuapi.di.container import DIContainer, ServiceScope
        self._container: DIContainer = container
        self._scope: Optional[ServiceScope] = scope

    async def get(self, service_type: Type[T]) -> T:
        if self._scope is not None:
            return await self._scope.resolve(service_type)
        return await self._container.resolve(service_type)

    async def __aenter__(self) -> "ServiceProvider":
        if self._scope is None:
            self._scope = self._container.create_scope()
            await self._scope.__aenter__()
        return self

    async def __aexit__(self, *args) -> None:
        if self._scope is not None:
            await self._scope.__aexit__(*args)

    def __repr__(self) -> str:
        return f"ServiceProvider(container={self._container!r})"


__all__ = ["ServiceProvider"]
