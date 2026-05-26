"""
VayuAPI Native Concurrency & Low Overhead Features

Provides native concurrency primitives and low-overhead optimizations:
- Async context managers
- Thread pool executors for CPU-bound tasks
- Semaphores for rate limiting
- Connection pooling utilities
- Background task management
- Zero-copy operations where possible
"""

import asyncio
import functools
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from contextlib import asynccontextmanager
from typing import Any, Callable, Optional, TypeVar, Dict, List
from collections import deque
import weakref


# Type variables
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


# ==============================================================================
# Global Executors (Low Overhead - Shared Pools)
# ==============================================================================

_thread_pool: Optional[ThreadPoolExecutor] = None
_process_pool: Optional[ProcessPoolExecutor] = None


def get_thread_pool(max_workers: int = None) -> ThreadPoolExecutor:
    """
    Get or create global thread pool executor.

    Shared pool reduces overhead from creating multiple executors.

    Args:
        max_workers: Maximum workers (default: CPU count * 5)

    Returns:
        ThreadPoolExecutor instance

    Example:
        ```python
        from vayuapi.concurrency import get_thread_pool, run_in_thread

        @app.get("/sync-task")
        async def handle():
            result = await run_in_thread(cpu_intensive_task, arg1, arg2)
            return {"result": result}
        ```
    """
    global _thread_pool
    if _thread_pool is None:
        _thread_pool = ThreadPoolExecutor(max_workers=max_workers)
    return _thread_pool


def get_process_pool(max_workers: int = None) -> ProcessPoolExecutor:
    """
    Get or create global process pool executor.

    For CPU-intensive tasks that benefit from multiple processes.

    Args:
        max_workers: Maximum workers (default: CPU count)

    Returns:
        ProcessPoolExecutor instance
    """
    global _process_pool
    if _process_pool is None:
        _process_pool = ProcessPoolExecutor(max_workers=max_workers)
    return _process_pool


async def run_in_thread(func: Callable, *args, **kwargs) -> Any:
    """
    Run blocking function in thread pool without blocking event loop.

    Low overhead - uses shared thread pool.

    Args:
        func: Blocking function to run
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Function result

    Example:
        ```python
        # Run blocking database query
        result = await run_in_thread(db.execute, query)

        # Run CPU-intensive calculation
        computed = await run_in_thread(calculate_hash, data)
        ```
    """
    loop = asyncio.get_event_loop()
    executor = get_thread_pool()
    return await loop.run_in_executor(executor, functools.partial(func, *args, **kwargs))


async def run_in_process(func: Callable, *args, **kwargs) -> Any:
    """
    Run CPU-intensive function in process pool.

    Use for truly CPU-bound tasks (image processing, ML inference, etc.)

    Args:
        func: CPU-intensive function
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Function result

    Example:
        ```python
        # Run ML model inference
        prediction = await run_in_process(model.predict, image_data)

        # Process large dataset
        result = await run_in_process(process_data, big_dataset)
        ```
    """
    loop = asyncio.get_event_loop()
    executor = get_process_pool()
    return await loop.run_in_executor(executor, functools.partial(func, *args, **kwargs))


def to_thread(func: F) -> F:
    """
    Decorator to run blocking function in thread pool.

    Low overhead - automatically offloads to thread pool when called.

    Example:
        ```python
        from vayuapi.concurrency import to_thread

        @to_thread
        def blocking_operation(data):
            # This will run in thread pool
            return expensive_computation(data)

        @app.get("/compute")
        async def endpoint():
            # Automatically runs in thread pool
            result = await blocking_operation(data)
            return {"result": result}
        ```
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await run_in_thread(func, *args, **kwargs)
    return wrapper


# ==============================================================================
# Semaphores & Rate Limiting (Native Concurrency Control)
# ==============================================================================

class Semaphore:
    """
    Async semaphore for limiting concurrent operations.

    Low overhead - native asyncio semaphore wrapper.

    Example:
        ```python
        from vayuapi.concurrency import Semaphore

        # Limit to 10 concurrent database connections
        db_semaphore = Semaphore(10)

        @app.get("/data")
        async def get_data():
            async with db_semaphore:
                result = await db.query()
            return result
        ```
    """

    def __init__(self, value: int = 1):
        """
        Create semaphore.

        Args:
            value: Maximum concurrent operations
        """
        self._semaphore = asyncio.Semaphore(value)

    async def __aenter__(self):
        await self._semaphore.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._semaphore.release()

    async def acquire(self):
        """Acquire semaphore."""
        await self._semaphore.acquire()

    def release(self):
        """Release semaphore."""
        self._semaphore.release()

    @property
    def locked(self) -> bool:
        """Check if semaphore is locked."""
        return self._semaphore.locked()


class RateLimiter:
    """
    Simple rate limiter using sliding window.

    Low overhead - in-memory counter.

    Example:
        ```python
        from vayuapi.concurrency import RateLimiter

        # 100 requests per minute per user
        limiter = RateLimiter(rate=100, per=60)

        @app.get("/api")
        async def api_endpoint(request):
            user_id = request.headers.get("user-id")

            if not await limiter.check(user_id):
                return JSONResponse(
                    {"error": "Rate limit exceeded"},
                    status_code=429
                )

            return {"data": "..."}
        ```
    """

    def __init__(self, rate: int, per: float):
        """
        Create rate limiter.

        Args:
            rate: Number of requests allowed
            per: Time period in seconds
        """
        self.rate = rate
        self.per = per
        self._requests: Dict[str, deque] = {}
        self._lock = asyncio.Lock()

    async def check(self, key: str) -> bool:
        """
        Check if request is allowed.

        Args:
            key: Unique identifier (user_id, IP, etc.)

        Returns:
            True if allowed, False if rate limit exceeded
        """
        now = time.time()

        async with self._lock:
            if key not in self._requests:
                self._requests[key] = deque()

            # Remove old requests
            requests = self._requests[key]
            while requests and requests[0] < now - self.per:
                requests.popleft()

            # Check rate limit
            if len(requests) >= self.rate:
                return False

            # Add current request
            requests.append(now)
            return True

    async def reset(self, key: str):
        """Reset rate limit for key."""
        async with self._lock:
            if key in self._requests:
                del self._requests[key]


# ==============================================================================
# Connection Pooling (Low Overhead Resource Management)
# ==============================================================================

class ConnectionPool:
    """
    Generic async connection pool for any resource.

    Low overhead - reuses connections, minimizes creation cost.

    Example:
        ```python
        from vayuapi.concurrency import ConnectionPool
        import aiohttp

        # HTTP client pool
        http_pool = ConnectionPool(
            create_func=lambda: aiohttp.ClientSession(),
            max_size=20,
            timeout=30
        )

        @app.get("/fetch")
        async def fetch_data():
            async with http_pool.acquire() as session:
                async with session.get("https://api.example.com") as resp:
                    return await resp.json()
        ```
    """

    def __init__(
        self,
        create_func: Callable,
        max_size: int = 10,
        timeout: float = 30.0,
        max_lifetime: float = 3600.0
    ):
        """
        Create connection pool.

        Args:
            create_func: Function to create new connection
            max_size: Maximum connections in pool
            timeout: Timeout for acquiring connection
            max_lifetime: Maximum connection lifetime (seconds)
        """
        self._create_func = create_func
        self._max_size = max_size
        self._timeout = timeout
        self._max_lifetime = max_lifetime

        self._pool: deque = deque()
        self._in_use: set = set()
        self._created_at: Dict[Any, float] = {}
        self._semaphore = asyncio.Semaphore(max_size)
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def acquire(self):
        """
        Acquire connection from pool.

        Yields:
            Connection object
        """
        # Wait for available slot
        await asyncio.wait_for(
            self._semaphore.acquire(),
            timeout=self._timeout
        )

        try:
            # Get or create connection
            conn = await self._get_connection()
            self._in_use.add(id(conn))

            yield conn

        finally:
            # Return connection to pool
            self._in_use.discard(id(conn))
            await self._return_connection(conn)
            self._semaphore.release()

    async def _get_connection(self):
        """Get connection from pool or create new one."""
        async with self._lock:
            # Try to get from pool
            while self._pool:
                conn = self._pool.popleft()
                created_at = self._created_at.get(id(conn), 0)

                # Check if connection is still valid
                if time.time() - created_at < self._max_lifetime:
                    return conn

                # Connection too old, remove it
                del self._created_at[id(conn)]

            # Create new connection
            conn = await asyncio.to_thread(self._create_func)
            self._created_at[id(conn)] = time.time()
            return conn

    async def _return_connection(self, conn):
        """Return connection to pool."""
        async with self._lock:
            if len(self._pool) < self._max_size:
                self._pool.append(conn)
            else:
                # Pool full, close connection
                if hasattr(conn, 'close'):
                    await conn.close()
                del self._created_at[id(conn)]

    async def close(self):
        """Close all connections in pool."""
        async with self._lock:
            while self._pool:
                conn = self._pool.popleft()
                if hasattr(conn, 'close'):
                    await conn.close()
                if id(conn) in self._created_at:
                    del self._created_at[id(conn)]


# ==============================================================================
# Background Tasks (Native Async Task Management)
# ==============================================================================

class BackgroundTasks:
    """
    Manage background tasks with low overhead.

    Tasks run concurrently without blocking the response.

    Example:
        ```python
        from vayuapi.concurrency import BackgroundTasks

        @app.post("/process")
        async def process_data(data: dict):
            tasks = BackgroundTasks()
            tasks.add(send_email, data["email"])
            tasks.add(update_analytics, data["user_id"])
            tasks.add(generate_report, data)

            # Execute all tasks in background
            await tasks.execute()

            return {"status": "processing"}
        ```
    """

    def __init__(self):
        self._tasks: List[Callable] = []

    def add(self, func: Callable, *args, **kwargs):
        """
        Add background task.

        Args:
            func: Async or sync function to run
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        self._tasks.append((func, args, kwargs))

    async def execute(self):
        """Execute all background tasks concurrently."""
        tasks = []

        for func, args, kwargs in self._tasks:
            if asyncio.iscoroutinefunction(func):
                # Async function
                tasks.append(func(*args, **kwargs))
            else:
                # Sync function - run in thread pool
                tasks.append(run_in_thread(func, *args, **kwargs))

        # Run all tasks concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


# ==============================================================================
# Async Caching (Low Overhead Memoization)
# ==============================================================================

class AsyncLRUCache:
    """
    LRU cache for async functions with low overhead.

    Example:
        ```python
        from vayuapi.concurrency import AsyncLRUCache

        cache = AsyncLRUCache(max_size=1000, ttl=300)

        @cache.cached
        async def expensive_query(user_id: int):
            return await db.query(user_id)

        # First call - hits database
        result = await expensive_query(123)

        # Second call - returns cached result
        result = await expensive_query(123)
        ```
    """

    def __init__(self, max_size: int = 128, ttl: Optional[float] = None):
        """
        Create async LRU cache.

        Args:
            max_size: Maximum cache entries
            ttl: Time to live in seconds (None = no expiration)
        """
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, tuple] = {}  # key -> (value, timestamp)
        self._access_order: deque = deque()
        self._lock = asyncio.Lock()

    def cached(self, func: Callable) -> Callable:
        """
        Decorator to cache async function results.

        Args:
            func: Async function to cache

        Returns:
            Cached function
        """
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key = f"{func.__name__}:{args}:{kwargs}"

            async with self._lock:
                # Check cache
                if key in self._cache:
                    value, timestamp = self._cache[key]

                    # Check TTL
                    if self.ttl is None or time.time() - timestamp < self.ttl:
                        # Move to end (most recently used)
                        self._access_order.remove(key)
                        self._access_order.append(key)
                        return value
                    else:
                        # Expired
                        del self._cache[key]
                        self._access_order.remove(key)

            # Cache miss - execute function
            result = await func(*args, **kwargs)

            async with self._lock:
                # Add to cache
                self._cache[key] = (result, time.time())
                self._access_order.append(key)

                # Evict oldest if over limit
                while len(self._cache) > self.max_size:
                    oldest_key = self._access_order.popleft()
                    del self._cache[oldest_key]

            return result

        return wrapper

    async def clear(self):
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            self._access_order.clear()


# ==============================================================================
# Batch Processing (Low Overhead Request Batching)
# ==============================================================================

class BatchProcessor:
    """
    Batch multiple requests together for efficient processing.

    Reduces overhead by processing multiple items at once.

    Example:
        ```python
        from vayuapi.concurrency import BatchProcessor

        # Batch database queries
        db_batcher = BatchProcessor(
            process_func=fetch_users_batch,
            max_batch_size=100,
            max_wait_time=0.01  # 10ms
        )

        @app.get("/user/{user_id}")
        async def get_user(user_id: int):
            # Requests are automatically batched
            user = await db_batcher.add(user_id)
            return user
        ```
    """

    def __init__(
        self,
        process_func: Callable,
        max_batch_size: int = 100,
        max_wait_time: float = 0.01
    ):
        """
        Create batch processor.

        Args:
            process_func: Function to process batch (receives list of items)
            max_batch_size: Maximum items in batch
            max_wait_time: Maximum time to wait (seconds)
        """
        self.process_func = process_func
        self.max_batch_size = max_batch_size
        self.max_wait_time = max_wait_time

        self._batch: List[tuple] = []
        self._lock = asyncio.Lock()
        self._process_task: Optional[asyncio.Task] = None

    async def add(self, item: Any) -> Any:
        """
        Add item to batch for processing.

        Args:
            item: Item to process

        Returns:
            Processed result
        """
        future = asyncio.Future()

        async with self._lock:
            self._batch.append((item, future))

            # Check if batch is full
            if len(self._batch) >= self.max_batch_size:
                await self._process_batch()
            elif self._process_task is None:
                # Schedule batch processing
                self._process_task = asyncio.create_task(
                    self._wait_and_process()
                )

        return await future

    async def _wait_and_process(self):
        """Wait for max_wait_time then process batch."""
        await asyncio.sleep(self.max_wait_time)
        async with self._lock:
            if self._batch:
                await self._process_batch()

    async def _process_batch(self):
        """Process current batch."""
        if not self._batch:
            return

        # Get batch
        batch = self._batch
        self._batch = []
        self._process_task = None

        # Extract items and futures
        items = [item for item, _ in batch]
        futures = [future for _, future in batch]

        try:
            # Process batch
            results = await self.process_func(items)

            # Set results
            for future, result in zip(futures, results):
                future.set_result(result)
        except Exception as e:
            # Set exception on all futures
            for future in futures:
                future.set_exception(e)


# Clean up on module unload
def cleanup():
    """Clean up global resources."""
    global _thread_pool, _process_pool

    if _thread_pool:
        _thread_pool.shutdown(wait=False)
    if _process_pool:
        _process_pool.shutdown(wait=False)


import atexit
atexit.register(cleanup)


__all__ = [
    'get_thread_pool',
    'get_process_pool',
    'run_in_thread',
    'run_in_process',
    'to_thread',
    'Semaphore',
    'RateLimiter',
    'ConnectionPool',
    'BackgroundTasks',
    'AsyncLRUCache',
    'BatchProcessor',
]
