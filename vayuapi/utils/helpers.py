"""
Helper utilities for VayuAPI
"""

import asyncio
import functools
from typing import Any, Callable, TypeVar, Union
import time

T = TypeVar('T')


def async_timed(func: Callable) -> Callable:
    """
    Decorator to measure async function execution time.

    Example:
        ```python
        @async_timed
        async def slow_operation():
            await asyncio.sleep(1)
        ```
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = await func(*args, **kwargs)
        end = time.perf_counter()
        print(f"{func.__name__} took {(end - start) * 1000:.2f}ms")
        return result
    return wrapper


def sync_to_async(func: Callable) -> Callable:
    """
    Convert sync function to async.

    Example:
        ```python
        def blocking_operation():
            time.sleep(1)
            return "done"

        async_op = sync_to_async(blocking_operation)
        result = await async_op()
        ```
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))
    return wrapper


def retry_async(max_attempts: int = 3, delay: float = 1.0):
    """
    Retry decorator for async functions.

    Example:
        ```python
        @retry_async(max_attempts=3, delay=1.0)
        async def unstable_api_call():
            response = await httpx.get("https://api.example.com")
            return response.json()
        ```
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay * (attempt + 1))
            raise last_exception
        return wrapper
    return decorator


def cached(ttl: int = 60):
    """
    Simple cache decorator with TTL.

    Args:
        ttl: Time to live in seconds

    Example:
        ```python
        @cached(ttl=300)
        async def expensive_operation(param: str):
            # Expensive computation
            return result
        ```
    """
    def decorator(func: Callable) -> Callable:
        cache = {}

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key
            key = str(args) + str(kwargs)

            # Check cache
            if key in cache:
                result, timestamp = cache[key]
                if time.time() - timestamp < ttl:
                    return result

            # Call function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Store in cache
            cache[key] = (result, time.time())

            return result
        return wrapper
    return decorator


class PerformanceMonitor:
    """
    Monitor application performance metrics.

    Example:
        ```python
        monitor = PerformanceMonitor()

        with monitor.track("database_query"):
            result = await db.query(...)

        stats = monitor.get_stats()
        ```
    """

    def __init__(self):
        self.metrics = {}

    def track(self, operation: str):
        """Context manager for tracking operations."""
        return OperationTracker(self, operation)

    def record(self, operation: str, duration: float):
        """Record operation duration."""
        if operation not in self.metrics:
            self.metrics[operation] = {
                "count": 0,
                "total_time": 0.0,
                "min": float('inf'),
                "max": 0.0,
                "avg": 0.0
            }

        metric = self.metrics[operation]
        metric["count"] += 1
        metric["total_time"] += duration
        metric["min"] = min(metric["min"], duration)
        metric["max"] = max(metric["max"], duration)
        metric["avg"] = metric["total_time"] / metric["count"]

    def get_stats(self) -> dict:
        """Get all performance statistics."""
        return self.metrics

    def reset(self):
        """Reset all metrics."""
        self.metrics.clear()


class OperationTracker:
    """Context manager for tracking operation time."""

    def __init__(self, monitor: PerformanceMonitor, operation: str):
        self.monitor = monitor
        self.operation = operation
        self.start_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.perf_counter() - self.start_time
        self.monitor.record(self.operation, duration)


def format_bytes(bytes: int) -> str:
    """
    Format bytes to human-readable string.

    Example:
        >>> format_bytes(1024)
        '1.00 KB'
        >>> format_bytes(1048576)
        '1.00 MB'
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} PB"


def format_duration(seconds: float) -> str:
    """
    Format duration to human-readable string.

    Example:
        >>> format_duration(65)
        '1m 5s'
        >>> format_duration(3665)
        '1h 1m 5s'
    """
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")

    return " ".join(parts)
