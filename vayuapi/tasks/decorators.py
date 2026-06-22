"""
Unified @task and @periodic_task decorators that work with both VayuCelery
and VayuARQ backends.

Use these when you want backend-agnostic task definitions; the backend is
resolved at decoration time from the first ``VayuCelery`` / ``VayuARQ``
argument or via a module-level default set with ``set_default_backend()``.
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, Optional, Union

logger = logging.getLogger("vayuapi.tasks.decorators")

_DEFAULT_BACKEND = None


def set_default_backend(backend) -> None:
    """
    Set a module-level default task backend (VayuCelery or VayuARQ).

    Call once at application startup so you can use ``@task`` without
    explicitly passing a backend each time.

    Example::

        from vayuapi.tasks.decorators import set_default_backend
        from vayuapi.tasks import VayuCelery

        celery = VayuCelery("myapp", broker="redis://localhost:6379/0")
        set_default_backend(celery)

        @task
        def send_email(to, subject): ...
    """
    global _DEFAULT_BACKEND
    _DEFAULT_BACKEND = backend


def task(
    func: Optional[Callable] = None,
    *,
    backend=None,
    name: Optional[str] = None,
    queue: str = "default",
    max_retries: int = 3,
    timeout: Optional[int] = None,
    **kwargs,
) -> Callable:
    """
    Backend-agnostic task decorator.

    Dispatches to ``VayuCelery.task`` or ``VayuARQ.task`` depending on
    the backend in use.

    Args:
        backend: A ``VayuCelery`` or ``VayuARQ`` instance. Falls back to
                 the module-level default set via ``set_default_backend()``.
        name: Override the task name.
        queue: Queue to submit the task to (Celery only).
        max_retries: Maximum number of retries (Celery) / max_tries (ARQ).
        timeout: Job timeout in seconds.

    Example::

        from vayuapi.tasks import VayuCelery
        from vayuapi.tasks.decorators import task, set_default_backend

        celery = VayuCelery("myapp", broker="redis://localhost:6379/0")
        set_default_backend(celery)

        @task
        def crunch_numbers(data: list[int]) -> int:
            return sum(data)

        # Enqueue:
        crunch_numbers.delay([1, 2, 3])
    """
    def decorator(fn: Callable) -> Callable:
        b = backend or _DEFAULT_BACKEND
        if b is None:
            raise RuntimeError(
                "No task backend configured. Pass `backend=` or call "
                "`set_default_backend(celery_or_arq_instance)`."
            )

        from vayuapi.tasks.celery_app import VayuCelery
        from vayuapi.tasks.arq_app import VayuARQ

        if isinstance(b, VayuCelery):
            return b.task(
                fn,
                name=name,
                queue=queue,
                max_retries=max_retries,
                time_limit=timeout,
                **kwargs,
            )
        elif isinstance(b, VayuARQ):
            return b.task(
                fn,
                name=name,
                timeout=timeout,
                max_tries=max_retries,
                **kwargs,
            )
        else:
            raise TypeError(
                f"Unsupported backend type: {type(b).__name__}. "
                "Expected VayuCelery or VayuARQ."
            )

    if func is not None:
        return decorator(func)
    return decorator


def periodic_task(
    func: Optional[Callable] = None,
    *,
    backend=None,
    crontab: Optional[str] = None,
    interval: Optional[int] = None,
    name: Optional[str] = None,
    queue: str = "default",
    **kwargs,
) -> Callable:
    """
    Backend-agnostic periodic/cron task decorator.

    Args:
        crontab: Cron expression, e.g. ``"0 8 * * *"``.
        interval: Run every N seconds (Celery beat only).
        backend: A ``VayuCelery`` or ``VayuARQ`` instance.

    Example::

        @periodic_task(crontab="0 0 * * *")
        def daily_cleanup():
            ...
    """
    def decorator(fn: Callable) -> Callable:
        b = backend or _DEFAULT_BACKEND
        if b is None:
            raise RuntimeError(
                "No task backend configured. Pass `backend=` or call "
                "`set_default_backend(celery_or_arq_instance)`."
            )

        from vayuapi.tasks.celery_app import VayuCelery
        from vayuapi.tasks.arq_app import VayuARQ

        if isinstance(b, VayuCelery):
            return b.periodic_task(
                fn,
                crontab=crontab,
                interval=interval,
                name=name,
                queue=queue,
                **kwargs,
            )
        elif isinstance(b, VayuARQ):
            if crontab is None:
                raise ValueError("VayuARQ periodic tasks require a 'crontab' expression.")
            return b.cron(
                crontab,
                name=name,
                **kwargs,
            )(fn)
        else:
            raise TypeError(
                f"Unsupported backend type: {type(b).__name__}. "
                "Expected VayuCelery or VayuARQ."
            )

    if func is not None:
        return decorator(func)
    return decorator


__all__ = ["task", "periodic_task", "set_default_backend"]
