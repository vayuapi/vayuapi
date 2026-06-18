"""
VayuAPI Dependency Injection Container
Full IoC container with Singleton, Transient, and Scoped lifetimes.
"""

from vayuapi.di.container import (
    DIContainer,
    ServiceLifetime,
    ServiceDescriptor,
    ServiceScope,
)
from vayuapi.di.injectable import injectable, inject
from vayuapi.di.provider import ServiceProvider

__all__ = [
    "DIContainer",
    "ServiceLifetime",
    "ServiceDescriptor",
    "ServiceScope",
    "ServiceProvider",
    "injectable",
    "inject",
]
