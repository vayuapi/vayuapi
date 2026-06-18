"""
DI Container — IoC container with Singleton, Transient, and Scoped lifetimes.
"""

from __future__ import annotations

import asyncio
import inspect
import typing
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar

T = TypeVar("T")


class ServiceLifetime(Enum):
    """Service lifetime options."""
    SINGLETON = "singleton"   # One instance for the entire application
    TRANSIENT = "transient"   # New instance every time
    SCOPED = "scoped"         # One instance per scope (e.g. per request)


class ServiceDescriptor:
    """Describes how to create a service."""

    def __init__(
        self,
        service_type: Type,
        lifetime: ServiceLifetime,
        implementation_type: Optional[Type] = None,
        factory: Optional[Callable] = None,
        instance: Optional[Any] = None,
    ):
        if sum([implementation_type is not None, factory is not None, instance is not None]) != 1:
            raise ValueError("Exactly one of implementation_type, factory, or instance must be provided.")

        self.service_type = service_type
        self.lifetime = lifetime
        self.implementation_type = implementation_type
        self.factory = factory
        self.instance = instance

    def __repr__(self) -> str:
        return (
            f"ServiceDescriptor(type={self.service_type.__name__}, "
            f"lifetime={self.lifetime.value})"
        )


class ServiceScope:
    """
    A resolution scope. Scoped services are created once per scope.
    Use as a context manager for per-request scopes.
    """

    def __init__(self, container: "DIContainer"):
        self._container = container
        self._scoped_instances: Dict[Type, Any] = {}
        self._async_generators: List[Any] = []
        self._sync_generators: List[Any] = []

    async def resolve(self, service_type: Type[T]) -> T:
        return await self._container._resolve(service_type, scope=self)

    async def __aenter__(self) -> "ServiceScope":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._cleanup()

    async def _cleanup(self):
        for gen in reversed(self._async_generators):
            try:
                await gen.aclose()
            except Exception:
                pass
        for gen in reversed(self._sync_generators):
            try:
                gen.close()
            except Exception:
                pass
        self._scoped_instances.clear()
        self._async_generators.clear()
        self._sync_generators.clear()


class DIContainer:
    """
    Inversion of Control container for VayuAPI.

    Supports three service lifetimes:
    - SINGLETON: created once, shared across all requests
    - TRANSIENT: new instance for every resolution
    - SCOPED: one instance per scope (request)

    Example::

        container = DIContainer()

        # Register by type
        container.add_singleton(Database)
        container.add_transient(IEmailService, SmtpEmailService)
        container.add_scoped(UnitOfWork)

        # Register with a factory
        container.add_singleton_factory(Config, lambda c: Config.from_env())

        # Register an existing instance
        container.add_instance(Config, Config.from_env())

        # Resolve
        async with container.create_scope() as scope:
            db = await scope.resolve(Database)
    """

    def __init__(self):
        self._descriptors: Dict[Type, ServiceDescriptor] = {}
        self._singletons: Dict[Type, Any] = {}
        # Tracks types currently being created to detect circular dependencies.
        self._creating: set = set()

    # ------------------------------------------------------------------
    # Registration helpers
    # ------------------------------------------------------------------

    def register(self, descriptor: ServiceDescriptor) -> "DIContainer":
        self._descriptors[descriptor.service_type] = descriptor
        return self

    def add_singleton(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type[T]] = None,
    ) -> "DIContainer":
        impl = implementation_type or service_type
        return self.register(ServiceDescriptor(service_type, ServiceLifetime.SINGLETON, implementation_type=impl))

    def add_singleton_factory(
        self,
        service_type: Type[T],
        factory: Callable[["DIContainer"], T],
    ) -> "DIContainer":
        return self.register(ServiceDescriptor(service_type, ServiceLifetime.SINGLETON, factory=factory))

    def add_instance(self, service_type: Type[T], instance: T) -> "DIContainer":
        return self.register(ServiceDescriptor(service_type, ServiceLifetime.SINGLETON, instance=instance))

    def add_transient(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type[T]] = None,
    ) -> "DIContainer":
        impl = implementation_type or service_type
        return self.register(ServiceDescriptor(service_type, ServiceLifetime.TRANSIENT, implementation_type=impl))

    def add_transient_factory(
        self,
        service_type: Type[T],
        factory: Callable[["DIContainer"], T],
    ) -> "DIContainer":
        return self.register(ServiceDescriptor(service_type, ServiceLifetime.TRANSIENT, factory=factory))

    def add_scoped(
        self,
        service_type: Type[T],
        implementation_type: Optional[Type[T]] = None,
    ) -> "DIContainer":
        impl = implementation_type or service_type
        return self.register(ServiceDescriptor(service_type, ServiceLifetime.SCOPED, implementation_type=impl))

    def add_scoped_factory(
        self,
        service_type: Type[T],
        factory: Callable[["DIContainer"], T],
    ) -> "DIContainer":
        return self.register(ServiceDescriptor(service_type, ServiceLifetime.SCOPED, factory=factory))

    # ------------------------------------------------------------------
    # Scope factory
    # ------------------------------------------------------------------

    def create_scope(self) -> ServiceScope:
        return ServiceScope(self)

    # ------------------------------------------------------------------
    # Internal resolution
    # ------------------------------------------------------------------

    async def _resolve(self, service_type: Type[T], scope: Optional[ServiceScope] = None) -> T:
        descriptor = self._descriptors.get(service_type)
        if descriptor is None:
            raise LookupError(
                f"Service '{service_type.__name__}' is not registered in the container."
            )

        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            return await self._resolve_singleton(descriptor, scope)
        elif descriptor.lifetime == ServiceLifetime.TRANSIENT:
            return await self._create_instance(descriptor, scope)
        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            if scope is None:
                raise RuntimeError(
                    f"Cannot resolve scoped service '{service_type.__name__}' outside of a scope."
                )
            if service_type not in scope._scoped_instances:
                instance = await self._create_instance(descriptor, scope)
                scope._scoped_instances[service_type] = instance
            return scope._scoped_instances[service_type]

    async def _resolve_singleton(self, descriptor: ServiceDescriptor, scope: Optional[ServiceScope]) -> Any:
        if descriptor.service_type in self._singletons:
            return self._singletons[descriptor.service_type]

        if descriptor.service_type in self._creating:
            raise RuntimeError(
                f"Circular dependency detected while creating '{descriptor.service_type.__name__}'."
            )

        self._creating.add(descriptor.service_type)
        try:
            instance = await self._create_instance(descriptor, scope)
        finally:
            self._creating.discard(descriptor.service_type)

        # Store only if not already stored (concurrent tasks are not possible in
        # single-threaded asyncio, but guard for completeness).
        if descriptor.service_type not in self._singletons:
            self._singletons[descriptor.service_type] = instance
        return self._singletons[descriptor.service_type]

    async def _create_instance(self, descriptor: ServiceDescriptor, scope: Optional[ServiceScope]) -> Any:
        if descriptor.instance is not None:
            return descriptor.instance

        if descriptor.factory is not None:
            result = descriptor.factory(self)
            if asyncio.iscoroutine(result):
                result = await result
            elif inspect.isasyncgen(result):
                instance = await result.__anext__()
                if scope is not None:
                    scope._async_generators.append(result)
                return instance
            elif inspect.isgenerator(result):
                instance = next(result)
                if scope is not None:
                    scope._sync_generators.append(result)
                return instance
            return result

        impl_type = descriptor.implementation_type
        # Auto-wire constructor dependencies
        kwargs = await self._autowire(impl_type, scope)
        return impl_type(**kwargs)

    async def _autowire(self, impl_type: Type, scope: Optional[ServiceScope]) -> Dict[str, Any]:
        # Use get_type_hints to properly resolve string annotations
        # (PEP 563 / from __future__ import annotations in caller modules).
        try:
            hints = typing.get_type_hints(impl_type.__init__)
        except Exception:
            hints = {}

        sig = inspect.signature(impl_type.__init__)
        kwargs: Dict[str, Any] = {}

        for name, param in sig.parameters.items():
            if name == "self":
                continue
            # Prefer resolved hint; fall back to raw annotation on the Parameter.
            annotation = hints.get(name, param.annotation)
            if annotation is inspect.Parameter.empty:
                if param.default is not inspect.Parameter.empty:
                    continue  # has default, skip
                raise TypeError(
                    f"Cannot auto-wire parameter '{name}' in '{impl_type.__name__}': "
                    f"no type annotation and no default value."
                )
            if annotation in self._descriptors:
                kwargs[name] = await self._resolve(annotation, scope)
            elif param.default is not inspect.Parameter.empty:
                continue  # use default, skip
            # else: unknown / primitive type — skip silently, constructor
            # will raise if it was required (gives a clear Python TypeError).

        return kwargs

    # ------------------------------------------------------------------
    # Direct resolve (no scope — for singletons / root resolution)
    # ------------------------------------------------------------------

    async def resolve(self, service_type: Type[T]) -> T:
        return await self._resolve(service_type, scope=None)

    def is_registered(self, service_type: Type) -> bool:
        return service_type in self._descriptors

    def __contains__(self, service_type: Type) -> bool:
        return self.is_registered(service_type)

    def __repr__(self) -> str:
        names = [d.service_type.__name__ for d in self._descriptors.values()]
        return f"DIContainer(services=[{', '.join(names)}])"


__all__ = [
    "DIContainer",
    "ServiceLifetime",
    "ServiceDescriptor",
    "ServiceScope",
]
