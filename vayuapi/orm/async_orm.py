"""
Async ORM integrations (Tortoise ORM, SQLAlchemy Async)
"""

from typing import Any, Dict, List, Optional, Type
from tortoise import Tortoise, fields
from tortoise.models import Model


class AsyncORMIntegration:
    """
    Base class for async ORM integrations.
    """

    async def initialize(self, **config):
        """Initialize ORM connection."""
        raise NotImplementedError

    async def close(self):
        """Close ORM connections."""
        raise NotImplementedError


class TortoiseIntegration(AsyncORMIntegration):
    """
    Tortoise ORM integration.

    High-performance async ORM inspired by Django ORM.

    Example:
        ```python
        from vayuapi.orm import TortoiseIntegration
        from tortoise import fields
        from tortoise.models import Model

        class User(Model):
            id = fields.IntField(pk=True)
            username = fields.CharField(max_length=50, unique=True)
            email = fields.CharField(max_length=100)
            is_active = fields.BooleanField(default=True)
            created_at = fields.DatetimeField(auto_now_add=True)

            class Meta:
                table = "users"

        @app.get("/users")
        async def get_users():
            users = await User.all()
            return [{"id": u.id, "username": u.username} for u in users]
        ```
    """

    def __init__(self):
        self.initialized = False

    async def initialize(
        self,
        db_url: str,
        modules: Dict[str, List[str]] = None,
        generate_schemas: bool = True,
        **kwargs
    ):
        """
        Initialize Tortoise ORM.

        Args:
            db_url: Database URL (e.g., "postgres://user:pass@localhost/db")
            modules: Dict of module names and model paths
            generate_schemas: Auto-generate database schemas
        """
        config = {
            "connections": {"default": db_url},
            "apps": {
                "models": {
                    "models": modules.get("models", []) if modules else [],
                    "default_connection": "default",
                }
            },
        }

        await Tortoise.init(config=config)

        if generate_schemas:
            await Tortoise.generate_schemas()

        self.initialized = True

    async def close(self):
        """Close Tortoise connections."""
        await Tortoise.close_connections()
        self.initialized = False


def configure_tortoise(db_url: str, models: List[str]):
    """
    Configure Tortoise ORM.

    Args:
        db_url: Database URL
        models: List of model module paths
    """
    return {
        "connections": {"default": db_url},
        "apps": {
            "models": {
                "models": models,
                "default_connection": "default",
            }
        },
    }


class SQLAlchemyAsyncIntegration(AsyncORMIntegration):
    """
    SQLAlchemy async integration.

    Uses SQLAlchemy 2.0+ async features.

    Example:
        ```python
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

        class Base(DeclarativeBase):
            pass

        class User(Base):
            __tablename__ = "users"

            id: Mapped[int] = mapped_column(primary_key=True)
            username: Mapped[str]
            email: Mapped[str]

        # Configure
        engine = create_async_engine("postgresql+asyncpg://localhost/db")
        ```
    """

    def __init__(self):
        self.engine = None
        self.session_factory = None

    async def initialize(
        self,
        database_url: str,
        echo: bool = False,
        **engine_kwargs
    ):
        """
        Initialize SQLAlchemy async engine.

        Args:
            database_url: Async database URL
            echo: Enable SQL query logging
        """
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

        self.engine = create_async_engine(
            database_url,
            echo=echo,
            **engine_kwargs
        )

        self.session_factory = async_sessionmaker(
            self.engine,
            expire_on_commit=False
        )

    async def close(self):
        """Close SQLAlchemy engine."""
        if self.engine:
            await self.engine.dispose()

    def get_session(self):
        """Get database session."""
        return self.session_factory()


class BaseModel(Model):
    """
    Enhanced Tortoise Model with additional utilities.
    """

    class Meta:
        abstract = True

    @classmethod
    async def get_or_create(cls, defaults: Dict = None, **kwargs):
        """
        Get or create object.

        Returns: (object, created)
        """
        try:
            obj = await cls.get(**kwargs)
            return obj, False
        except:
            create_kwargs = {**kwargs, **(defaults or {})}
            obj = await cls.create(**create_kwargs)
            return obj, True

    async def update_from_dict(self, data: Dict[str, Any]) -> "BaseModel":
        """Update model from dictionary."""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
        await self.save()
        return self

    def to_dict(self, exclude: List[str] = None) -> Dict[str, Any]:
        """Convert model to dictionary."""
        exclude = exclude or []
        data = {}
        for field in self._meta.fields_map.keys():
            if field not in exclude:
                value = getattr(self, field)
                # Handle special types
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                data[field] = value
        return data
