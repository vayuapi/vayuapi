"""
VayuARQ — ARQ (Async Redis Queue) integration for VayuAPI.

ARQ is a fast, async Redis-based task queue by Samuel Colvin.
Install the extra: pip install 'vayuapi[arq]'
"""

from __future__ import annotations

import asyncio
import functools
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar

logger = logging.getLogger("vayuapi.tasks.arq")
T = TypeVar("T")


def _require_arq():
    try:
        import arq
        return arq
    except ImportError:
        raise ImportError(
            "arq is required for VayuARQ. "
            "Install it with: pip install 'vayuapi[arq]'"
        )


@dataclass
class ArqSettings:
    """
    ARQ worker settings dataclass.

    Mirrors arq's ``WorkerSettings`` but with VayuAPI-friendly defaults.

    Example::

        settings = ArqSettings(
            redis_url="redis://localhost:6379",
            queue_name="vayuapi:default",
            max_jobs=50,
        )
    """
    redis_url: str = "redis://localhost:6379"
    queue_name: str = "arq:queue"
    max_jobs: int = 10
    job_timeout: int = 300         # seconds
    keep_result: int = 3600        # seconds to keep job results
    max_tries: int = 5
    retry_jobs: bool = True
    health_check_interval: int = 60
    allow_abort_jobs: bool = False
    on_startup: Optional[Callable] = None
    on_shutdown: Optional[Callable] = None
    on_job_start: Optional[Callable] = None
    on_job_finish: Optional[Callable] = None
    # Extra functions registered directly on settings (populated by VayuARQ)
    _functions: List[Callable] = field(default_factory=list, repr=False)
    _cron_jobs: List[Any] = field(default_factory=list, repr=False)

    def to_worker_settings(self):
        """
        Build and return a ``WorkerSettings`` class suitable for arq.

        The returned class is used as ``WorkerSettings`` when running
        ``arq.worker.run_worker``.
        """
        arq = _require_arq()

        functions = list(self._functions)
        cron_jobs = list(self._cron_jobs)
        settings = self

        class _WorkerSettings:
            redis_settings = arq.connections.RedisSettings.from_dsn(settings.redis_url)
            queue_name = settings.queue_name
            max_jobs = settings.max_jobs
            job_timeout = settings.job_timeout
            keep_result = settings.keep_result
            max_tries = settings.max_tries
            retry_jobs = settings.retry_jobs
            health_check_interval = settings.health_check_interval
            allow_abort_jobs = settings.allow_abort_jobs
            on_startup = settings.on_startup
            on_shutdown = settings.on_shutdown
            on_job_start = settings.on_job_start
            on_job_finish = settings.on_job_finish

        _WorkerSettings.functions = functions
        _WorkerSettings.cron_jobs = cron_jobs
        return _WorkerSettings


class VayuARQ:
    """
    VayuAPI ARQ integration.

    Provides ``@arq_instance.task`` and ``@arq_instance.cron`` decorators
    and an ``enqueue`` helper for dispatching jobs from your ASGI application.

    Example::

        from vayuapi.tasks import VayuARQ, ArqSettings

        settings = ArqSettings(redis_url="redis://localhost:6379")
        arq = VayuARQ(settings)

        @arq.task
        async def resize_image(ctx, image_id: int, width: int, height: int):
            ...

        @arq.cron("0 3 * * *")
        async def nightly_cleanup(ctx):
            ...

        # In your ASGI handler:
        @app.post("/images")
        async def upload(request):
            job = await arq.enqueue("resize_image", image_id=1, width=800, height=600)
            return {"job_id": job.job_id}

        # In VayuAPI startup:
        @app.on_event("startup")
        async def startup():
            await arq.connect()

        @app.on_event("shutdown")
        async def shutdown():
            await arq.close()
    """

    def __init__(self, settings: Optional[ArqSettings] = None):
        self.settings = settings or ArqSettings()
        self._pool = None

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Connect to Redis and create the ARQ job pool."""
        arq = _require_arq()
        self._pool = await arq.create_pool(
            arq.connections.RedisSettings.from_dsn(self.settings.redis_url)
        )
        logger.info(f"VayuARQ connected to {self.settings.redis_url}")

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            logger.info("VayuARQ pool closed")

    # ------------------------------------------------------------------
    # Task decorator
    # ------------------------------------------------------------------

    def task(
        self,
        func: Optional[Callable] = None,
        *,
        name: Optional[str] = None,
        timeout: Optional[int] = None,
        keep_result: Optional[int] = None,
        max_tries: Optional[int] = None,
    ) -> Callable:
        """
        Register an async function as an ARQ task.

        The first argument of the function must be ``ctx`` (the ARQ context
        dict injected by the worker).

        Example::

            @arq.task
            async def send_notification(ctx, user_id: int, message: str):
                db = ctx["db"]
                await db.notify(user_id, message)

            @arq.task(timeout=120, max_tries=3)
            async def heavy_job(ctx, payload: dict):
                ...
        """
        def decorator(fn: Callable) -> Callable:
            if not asyncio.iscoroutinefunction(fn):
                raise TypeError(
                    f"ARQ tasks must be async functions. '{fn.__name__}' is not async."
                )

            task_name = name or fn.__name__

            # Attach metadata for the worker to pick up
            fn.__arq_task__ = True
            fn.__name__ = task_name
            if timeout is not None:
                fn.__timeout__ = timeout
            if keep_result is not None:
                fn.__keep_result__ = keep_result
            if max_tries is not None:
                fn.__max_tries__ = max_tries

            self.settings._functions.append(fn)
            logger.debug(f"Registered ARQ task: {task_name}")
            return fn

        if func is not None:
            return decorator(func)
        return decorator

    # ------------------------------------------------------------------
    # Cron decorator
    # ------------------------------------------------------------------

    def cron(
        self,
        expression: str,
        *,
        name: Optional[str] = None,
        timeout: Optional[int] = None,
        unique: bool = True,
        run_at_startup: bool = False,
    ) -> Callable:
        """
        Register a cron-scheduled ARQ job.

        Args:
            expression: Cron expression, e.g. ``"0 4 * * *"`` (04:00 daily).
            unique: Skip if a job with the same name is already enqueued.
            run_at_startup: Run the job immediately when the worker starts.

        Example::

            @arq.cron("*/10 * * * *")
            async def heartbeat(ctx):
                await ctx["db"].ping()
        """
        def decorator(fn: Callable) -> Callable:
            _require_arq()
            try:
                from arq.cron import cron as arq_cron
            except ImportError:
                raise ImportError("arq>=0.25 is required for cron support.")

            if not asyncio.iscoroutinefunction(fn):
                raise TypeError(
                    f"ARQ cron tasks must be async. '{fn.__name__}' is not async."
                )

            task_name = name or fn.__name__
            fn.__name__ = task_name

            parts = expression.split()
            if len(parts) != 5:
                raise ValueError(f"Invalid cron expression: {expression!r} (expected 5 parts)")

            minute, hour, day, month, weekday = parts

            cron_kwargs: Dict[str, Any] = dict(
                coroutine=fn,
                unique=unique,
                run_at_startup=run_at_startup,
            )
            if minute != "*":
                cron_kwargs["minute"] = {int(m) for m in minute.replace("*/", "").split(",")}
            if hour != "*":
                cron_kwargs["hour"] = {int(h) for h in hour.split(",")}
            if day != "*":
                cron_kwargs["day"] = {int(d) for d in day.split(",")}
            if month != "*":
                cron_kwargs["month"] = {int(m) for m in month.split(",")}
            if weekday != "*":
                cron_kwargs["weekday"] = {int(w) for w in weekday.split(",")}
            if timeout is not None:
                cron_kwargs["timeout"] = timeout

            cron_job = arq_cron(**cron_kwargs)
            self.settings._cron_jobs.append(cron_job)
            self.settings._functions.append(fn)
            logger.debug(f"Registered ARQ cron task: {task_name}")
            return fn

        return decorator

    # ------------------------------------------------------------------
    # Enqueue helper
    # ------------------------------------------------------------------

    async def enqueue(
        self,
        function: str,
        *args,
        _job_id: Optional[str] = None,
        _queue_name: Optional[str] = None,
        _defer_until=None,
        _defer_by=None,
        _expires=None,
        **kwargs,
    ):
        """
        Enqueue a job by function name.

        Returns the ``arq.jobs.Job`` object.

        Example::

            job = await arq.enqueue("send_email", "user@example.com", "Welcome!")
            print(job.job_id)
        """
        if self._pool is None:
            raise RuntimeError(
                "VayuARQ is not connected. Call `await arq.connect()` first "
                "or use the startup event handler."
            )
        return await self._pool.enqueue_job(
            function,
            *args,
            _job_id=_job_id,
            _queue_name=_queue_name or self.settings.queue_name,
            _defer_until=_defer_until,
            _defer_by=_defer_by,
            _expires=_expires,
            **kwargs,
        )

    async def get_job_result(self, job_id: str):
        """Fetch job result by job ID."""
        if self._pool is None:
            raise RuntimeError("VayuARQ is not connected.")
        arq = _require_arq()
        job = arq.jobs.Job(job_id, self._pool)
        return await job.result()

    async def abort_job(self, job_id: str, timeout: float = 5.0) -> bool:
        """Attempt to abort a running job. Returns True if aborted."""
        if self._pool is None:
            raise RuntimeError("VayuARQ is not connected.")
        arq = _require_arq()
        job = arq.jobs.Job(job_id, self._pool)
        return await job.abort(timeout=timeout)

    def worker_settings(self):
        """Return the ARQ WorkerSettings class for use with ``arq.worker.run_worker``."""
        return self.settings.to_worker_settings()

    def __repr__(self) -> str:
        connected = self._pool is not None
        return f"VayuARQ(redis={self.settings.redis_url!r}, connected={connected})"


__all__ = ["VayuARQ", "ArqSettings"]
