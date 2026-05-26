"""
Django ORM integration for VayuAPI
Enables async usage of Django ORM
"""

import asyncio
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor


class DjangoORMIntegration:
    """
    Django ORM integration with async support.

    Uses sync_to_async to wrap Django ORM calls for use in async context.

    Example:
        ```python
        from vayuapi.orm import DjangoORMIntegration
        from myapp.models import User

        django_orm = DjangoORMIntegration()

        @app.get("/users")
        async def get_users():
            users = await django_orm.all(User)
            return [{"id": u.id, "name": u.name} for u in users]
        ```
    """

    def __init__(self, executor: ThreadPoolExecutor = None):
        self.executor = executor or ThreadPoolExecutor(max_workers=10)
        self._configured = False

    async def sync_to_async(self, func, *args, **kwargs):
        """
        Convert sync Django ORM call to async.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            lambda: func(*args, **kwargs)
        )

    async def all(self, model_class):
        """Get all objects from a model."""
        def _get_all():
            return list(model_class.objects.all())
        return await self.sync_to_async(_get_all)

    async def get(self, model_class, **kwargs):
        """Get single object."""
        def _get():
            return model_class.objects.get(**kwargs)
        return await self.sync_to_async(_get)

    async def filter(self, model_class, **kwargs):
        """Filter objects."""
        def _filter():
            return list(model_class.objects.filter(**kwargs))
        return await self.sync_to_async(_filter)

    async def create(self, model_class, **kwargs):
        """Create new object."""
        def _create():
            return model_class.objects.create(**kwargs)
        return await self.sync_to_async(_create)

    async def update(self, instance, **kwargs):
        """Update object."""
        def _update():
            for key, value in kwargs.items():
                setattr(instance, key, value)
            instance.save()
            return instance
        return await self.sync_to_async(_update)

    async def delete(self, instance):
        """Delete object."""
        def _delete():
            instance.delete()
        return await self.sync_to_async(_delete)

    async def execute_raw(self, query: str, params: List = None):
        """Execute raw SQL query."""
        from django.db import connection

        def _execute():
            with connection.cursor() as cursor:
                cursor.execute(query, params or [])
                return cursor.fetchall()

        return await self.sync_to_async(_execute)


def configure_django(databases: Dict[str, Any] = None):
    """
    Configure Django settings for ORM usage.

    Args:
        databases: Django DATABASES configuration
    """
    import django
    from django.conf import settings

    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES=databases or {
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.contenttypes',
                'django.contrib.auth',
            ],
            USE_TZ=True,
        )
        django.setup()


class AsyncQuerySetWrapper:
    """
    Wrapper for Django QuerySet to provide async methods.

    Example:
        ```python
        User = AsyncQuerySetWrapper(User)
        users = await User.objects.filter(is_active=True)
        ```
    """

    def __init__(self, model_class):
        self.model_class = model_class
        self.orm = DjangoORMIntegration()

    @property
    def objects(self):
        """Return async manager."""
        return AsyncManager(self.model_class, self.orm)


class AsyncManager:
    """Async manager for Django models."""

    def __init__(self, model_class, orm: DjangoORMIntegration):
        self.model_class = model_class
        self.orm = orm

    async def all(self):
        """Get all objects."""
        return await self.orm.all(self.model_class)

    async def get(self, **kwargs):
        """Get single object."""
        return await self.orm.get(self.model_class, **kwargs)

    async def filter(self, **kwargs):
        """Filter objects."""
        return await self.orm.filter(self.model_class, **kwargs)

    async def create(self, **kwargs):
        """Create object."""
        return await self.orm.create(self.model_class, **kwargs)

    async def count(self):
        """Count objects."""
        async def _count():
            return await self.orm.sync_to_async(self.model_class.objects.count)
        return await _count()

    async def exists(self):
        """Check if any objects exist."""
        async def _exists():
            return await self.orm.sync_to_async(self.model_class.objects.exists)
        return await _exists()
