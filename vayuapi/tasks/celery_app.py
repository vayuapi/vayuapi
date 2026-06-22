"""
VayuCelery — thin wrapper around Celery that integrates with VayuAPI.

Install the extra: pip install 'vayuapi[celery]'
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, Dict, List, Optional, TypeVar

logger = logging.getLogger("vayuapi.tasks.celery")
T = TypeVar("T")


def _require_celery():
    try:
        from celery import Celery
        return Celery
    except ImportError:
        raise ImportError(
            "Celery is required for VayuCelery. "
            "Install it with: pip install 'vayuapi[celery]'"
        )


class VayuCelery:
    """
    VayuAPI Celery integration.

    Wraps a ``celery.Celery`` instance and provides VayuAPI-style
    ``@app.task`` / ``@app.periodic_task`` decorators plus lifecycle
    hooks compatible with ``on_event('startup')``.

    Example::

        from vayuapi.tasks import VayuCelery

        celery = VayuCelery(
            "myapp",
            broker="redis://localhost:6379/0",
            backend="redis://localhost:6379/1",
        )

        @celery.task
        def send_email(to: str, subject: str):
            ...

        @celery.task(queue="high", max_retries=3, retry_backoff=True)
        def process_payment(order_id: int):
            ...

        # Enqueue
        send_email.delay("user@example.com", "Welcome!")
        process_payment.apply_async(args=[42], countdown=5)

    Periodic tasks (requires celery beat)::

        @celery.periodic_task(crontab="0 0 * * *")
        def nightly_report():
            ...
    """

    def __init__(
        self,
        name: str = "vayuapi",
        broker: str = "redis://localhost:6379/0",
        backend: Optional[str] = "redis://localhost:6379/1",
        include: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        Celery = _require_celery()
        self._app = Celery(name, broker=broker, backend=backend, include=include or [], **kwargs)
        self._beat_schedule: Dict[str, Any] = {}

        # Apply extra configuration
        default_config = {
            "task_serializer": "json",
            "result_serializer": "json",
            "accept_content": ["json"],
            "timezone": "UTC",
            "enable_utc": True,
            "task_track_started": True,
            "task_acks_late": True,
            "worker_prefetch_multiplier": 1,
        }
        if config:
            default_config.update(config)
        self._app.config_from_object(default_config)

    @property
    def celery(self):
        """Access the underlying celery.Celery instance."""
        return self._app

    # ------------------------------------------------------------------
    # Task decorator
    # ------------------------------------------------------------------

    def task(
        self,
        func: Optional[Callable] = None,
        *,
        name: Optional[str] = None,
        queue: str = "default",
        max_retries: int = 3,
        retry_backoff: bool = False,
        retry_backoff_max: int = 600,
        time_limit: Optional[int] = None,
        soft_time_limit: Optional[int] = None,
        bind: bool = False,
        **celery_kwargs,
    ) -> Callable:
        """
        Decorator to register a Celery task.

        Can be used with or without arguments::

            @celery.task
            def simple_task(x, y):
                return x + y

            @celery.task(queue="low", max_retries=5)
            def heavy_task(data):
                ...
        """
        def decorator(fn: Callable) -> Callable:
            task_name = name or f"{fn.__module__}.{fn.__qualname__}"
            opts = dict(
                name=task_name,
                bind=bind,
                max_retries=max_retries,
                queue=queue,
                **celery_kwargs,
            )
            if time_limit is not None:
                opts["time_limit"] = time_limit
            if soft_time_limit is not None:
                opts["soft_time_limit"] = soft_time_limit
            if retry_backoff:
                opts["retry_backoff"] = retry_backoff
                opts["retry_backoff_max"] = retry_backoff_max

            registered = self._app.task(**opts)(fn)
            logger.debug(f"Registered Celery task: {task_name}")
            return registered

        if func is not None:
            return decorator(func)
        return decorator

    # ------------------------------------------------------------------
    # Periodic task decorator
    # ------------------------------------------------------------------

    def periodic_task(
        self,
        func: Optional[Callable] = None,
        *,
        crontab: Optional[str] = None,
        interval: Optional[int] = None,  # seconds
        name: Optional[str] = None,
        queue: str = "default",
        **celery_kwargs,
    ) -> Callable:
        """
        Register a Celery beat periodic task.

        Args:
            crontab: Cron expression, e.g. ``"0 8 * * *"`` (daily at 08:00).
            interval: Run every N seconds (uses ``celery.schedules.timedelta``).
            name: Beat schedule entry name (defaults to function name).

        Example::

            @celery.periodic_task(crontab="*/5 * * * *")
            def check_health():
                ...

            @celery.periodic_task(interval=30)
            def poll_queue():
                ...
        """
        def decorator(fn: Callable) -> Callable:
            try:
                from celery.schedules import crontab as _crontab, timedelta
            except ImportError:
                raise ImportError("celery is required for periodic tasks")

            task_fn = self.task(fn, name=name, queue=queue, **celery_kwargs)
            entry_name = name or fn.__qualname__

            if crontab:
                parts = crontab.split()
                if len(parts) == 5:
                    minute, hour, day_of_month, month_of_year, day_of_week = parts
                    schedule = _crontab(
                        minute=minute,
                        hour=hour,
                        day_of_month=day_of_month,
                        month_of_year=month_of_year,
                        day_of_week=day_of_week,
                    )
                else:
                    raise ValueError(f"Invalid crontab expression: {crontab!r}")
            elif interval is not None:
                from datetime import timedelta as dt_timedelta
                schedule = dt_timedelta(seconds=interval)
            else:
                raise ValueError("Either 'crontab' or 'interval' must be provided for periodic_task.")

            self._beat_schedule[entry_name] = {
                "task": task_fn.name,
                "schedule": schedule,
                "options": {"queue": queue},
            }
            self._app.conf.beat_schedule = self._beat_schedule
            logger.debug(f"Registered Celery beat task: {entry_name}")
            return task_fn

        if func is not None:
            return decorator(func)
        return decorator

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def autodiscover(self, *packages: str) -> None:
        """Autodiscover tasks in given packages (calls celery.autodiscover_tasks)."""
        self._app.autodiscover_tasks(list(packages))

    def __repr__(self) -> str:
        return f"VayuCelery(broker={self._app.conf.broker_url!r})"


__all__ = ["VayuCelery"]
