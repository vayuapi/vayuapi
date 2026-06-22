# Changelog

All notable changes to VayuAPI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.6] - 2026-06-22

### Added
- **Dependency Injection subsystem** (`vayuapi/di/`) — IoC container with SINGLETON, TRANSIENT, and SCOPED lifetimes; `@injectable` decorator; `ServiceProvider` for request-scoped resolution
- **gRPC subsystem** (`vayuapi/grpc/`) — async `VayuGRPCServer`, `GRPCClient`, and `@grpc_service` / `@grpc_method` / `@grpc_stream` decorators
- **Distributed Tasks subsystem** (`vayuapi/tasks/`) — `VayuCelery`, `VayuARQ`, `ArqSettings`; backend-agnostic `@task` and `@periodic_task` decorators
- **`depends()` typed helper** — typed `@overload` signatures so IDEs infer the correct return type from the dependency function's annotation (fixes unresolved attribute warnings)
- **`Depends[T]` subscript support** — `__class_getitem__` added so `Depends[Session]` works as a type annotation without runtime error

### Fixed
- **[CORE-01]** Path parameters (`{id}`) returned `None` — now extracted from URL template via regex and resolved from `request.path_params`
- **[CORE-02]** Query parameters not type-coerced — string values from query string are now cast to the annotated type (`int`, `float`, etc.); invalid values return 422
- **[CORE-03]** Invalid path parameter type raised 500 — coercion errors now raise `RequestValidationError` → 422 Unprocessable Entity
- **[CORE-04]** Custom middleware not invoked — `middleware_stack` now wrapped in `BaseHTTPMiddleware` and wired into the Starlette app
- **[CORE-05]** `HTTPException` raised inside middleware produced 500 — `_VayuMiddlewareWrapper` now catches all HTTP exceptions and routes through the app's exception handler
- **[CORE-06]** Async callable instances (e.g. `JWTBearer`) not awaited — `asyncio.iscoroutinefunction` check now also inspects `__call__`; result is awaited if it is a coroutine
- **[CORE-07]** Callable instance defaults not treated as dependencies — parameters with non-`Param`, non-`Depends` callable defaults are automatically wrapped in `Depends()`
- **[CORE-08]** Generator dependencies not driven — sync/async generator results are now driven with `next()` / `__anext__()` to extract the yielded value
- **[DI-01]** DI container deadlock on async singleton resolution — `threading.Lock` inside async code replaced with a `_creating: set` cycle detector
- **[DI-02]** PEP-563 string annotations not resolved in `_autowire` — replaced `param.annotation` with `typing.get_type_hints()` for accurate type resolution
- **[SECURITY-01]** `datetime.utcnow()` deprecation in JWT generation — replaced with `datetime.now(timezone.utc)` throughout
- **[SECURITY-02]** JWT tokens not unique within the same second — `iat` claim changed from `datetime` (1-second resolution) to `time.time()` (float, sub-second precision)
- **[ADMIN-01]** `AdminPanel` created externally not mounted — `AdminPanel.__init__` now auto-registers with the passed VayuAPI app instance
- **[ADMIN-02]** `SessionMiddleware` missing for externally created admin panels — `AdminPanel.__init__` now inserts `SessionMiddleware` if not already present
- **[ADMIN-03]** `_check_auth` allowed unauthenticated access when Django not installed — `ImportError` fallback no longer returns `True` when session is empty
- **[ADMIN-04]** Auth redirect used 302, causing clients to follow and see 200 — changed to 307 Temporary Redirect so clients detect the redirect without following

### Tests
- Added `tests/test_di_grpc_tasks.py` — 32 tests covering DI, gRPC, and Tasks subsystems
- Added `tests/test_depends.py` — 25 tests covering `Depends`, `depends()`, `Security`, generators, and route-level resolution
- Fixed `tests/test_application.py` — CORS test now sends `Origin` header
- Fixed `tests/test_admin.py` — auth redirect test uses `follow_redirects=False`
- **Full suite: 144 passed · 0 failed · 25 skipped**

---

## [0.1.2] - 2026-05-26

### Fixed
- Django `makemigrations` and `migrate` support

## [0.1.0] - 2026-05-20

### Added
- Initial alpha release
- Core async framework built on Starlette
- Django ORM integration with async support
- Tortoise ORM integration
- SQLAlchemy async support
- Auto-generated admin panel (Django-style)
- Task scheduling system
- WebSocket support
- Middleware system
- Security features (AES, RSA encryption, hashing)
- Langchain integration
- RAG (Retrieval Augmented Generation) pipeline
- Pydantic AI support
- Vector database support (ChromaDB, Pinecone, Weaviate, Qdrant)
- Multiple database support (PostgreSQL, MySQL, SQLite, MongoDB, Redis)
- Performance monitoring utilities
- Comprehensive examples

[Unreleased]: https://github.com/vayuapi/vayuapi/compare/v0.2.0...HEAD
[0.1.6]: https://github.com/vayuapi/vayuapi/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/vayuapi/vayuapi/compare/v0.1.0...v0.1.2
[0.1.0]: https://github.com/vayuapi/vayuapi/releases/tag/v0.1.0
