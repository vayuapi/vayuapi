"""
Worker launch helpers for Celery and ARQ.
"""

from __future__ import annotations

import sys
from typing import List, Optional


def run_celery_worker(
    celery_app,
    queues: Optional[List[str]] = None,
    concurrency: int = 4,
    loglevel: str = "info",
    beat: bool = False,
    extra_argv: Optional[List[str]] = None,
) -> None:
    """
    Start a Celery worker programmatically.

    This is a convenience wrapper around ``celery_app.celery.worker_main()``.
    For production, prefer running the Celery CLI directly::

        celery -A mymodule.celery worker -Q default --concurrency=4

    Args:
        celery_app: A ``VayuCelery`` instance.
        queues: List of queues to consume (default: all).
        concurrency: Number of worker processes/threads.
        loglevel: Log level ('debug', 'info', 'warning', 'error').
        beat: Also start the celery beat scheduler in the same process.
        extra_argv: Additional CLI arguments passed to the worker.

    Example::

        from vayuapi.tasks import VayuCelery, run_celery_worker

        celery = VayuCelery("myapp", broker="redis://localhost:6379/0")

        if __name__ == "__main__":
            run_celery_worker(celery, queues=["default", "high"])
    """
    from vayuapi.tasks.celery_app import VayuCelery

    if not isinstance(celery_app, VayuCelery):
        raise TypeError("celery_app must be a VayuCelery instance.")

    argv = ["worker", f"--loglevel={loglevel}", f"--concurrency={concurrency}"]
    if queues:
        argv += ["-Q", ",".join(queues)]
    if beat:
        argv.append("--beat")
    if extra_argv:
        argv += extra_argv

    celery_app.celery.worker_main(argv=argv)


def run_arq_worker(
    arq_app,
    *,
    burst: bool = False,
) -> None:
    """
    Start an ARQ worker programmatically.

    For production, prefer running the ARQ CLI::

        arq mymodule.WorkerSettings

    Args:
        arq_app: A ``VayuARQ`` instance.
        burst: If True the worker exits once the queue is empty.

    Example::

        from vayuapi.tasks import VayuARQ, ArqSettings, run_arq_worker

        settings = ArqSettings(redis_url="redis://localhost:6379")
        arq = VayuARQ(settings)

        if __name__ == "__main__":
            run_arq_worker(arq)
    """
    try:
        from arq import run_worker as _run_worker
        from arq.worker import Worker
    except ImportError:
        raise ImportError(
            "arq is required. Install with: pip install 'vayuapi[arq]'"
        )

    from vayuapi.tasks.arq_app import VayuARQ

    if not isinstance(arq_app, VayuARQ):
        raise TypeError("arq_app must be a VayuARQ instance.")

    worker_settings = arq_app.worker_settings()
    _run_worker(worker_settings, burst=burst)


__all__ = ["run_celery_worker", "run_arq_worker"]
