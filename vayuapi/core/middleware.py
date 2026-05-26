"""
Middleware system for VayuAPI
Supports both custom middleware and all Starlette middleware types
"""

import logging
from typing import Callable, List, Optional, Sequence
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
from starlette.datastructures import Headers, MutableHeaders

# Starlette Middleware Imports
from starlette.middleware.cors import CORSMiddleware as StarletteCORSMiddleware
from starlette.middleware.gzip import GZipMiddleware as StarletteGZipMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware as StarletteHTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware as StarletteTrustedHostMiddleware
from starlette.middleware.sessions import SessionMiddleware as StarletteSessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware as StarletteBase


class Middleware:
    """
    Base middleware class.

    Override process_request and/or process_response methods.

    Example:
        ```python
        class LoggingMiddleware(Middleware):
            async def process_request(self, request):
                print(f"Request: {request.method} {request.url}")

            async def process_response(self, request, response):
                print(f"Response: {response.status_code}")
                return response
        ```
    """

    async def process_request(self, request: Request):
        """
        Process request before it reaches the endpoint.
        Can modify request or return Response to short-circuit.
        """
        pass

    async def process_response(self, request: Request, response: Response) -> Response:
        """
        Process response before returning to client.
        Must return a Response object.
        """
        return response

    async def __call__(self, request: Request, call_next: Callable):
        """ASGI middleware interface."""
        # Process request
        result = await self.process_request(request)
        if isinstance(result, Response):
            return result

        # Call next middleware/endpoint
        response = await call_next(request)

        # Process response
        response = await self.process_response(request, response)

        return response


class MiddlewareStack:
    """
    Middleware stack manager.
    """

    def __init__(self):
        self.middleware: List[Middleware] = []

    def add(self, middleware: Middleware):
        """Add middleware to the stack."""
        self.middleware.append(middleware)

    def remove(self, middleware: Middleware):
        """Remove middleware from the stack."""
        if middleware in self.middleware:
            self.middleware.remove(middleware)

    async def process(self, request: Request, call_next: Callable) -> Response:
        """Process request through middleware stack."""
        async def dispatch(middleware_index: int):
            if middleware_index >= len(self.middleware):
                return await call_next(request)

            middleware = self.middleware[middleware_index]

            async def next_dispatch(req: Request):
                return await dispatch(middleware_index + 1)

            return await middleware(request, next_dispatch)

        return await dispatch(0)


class DjangoMiddlewareAdapter(Middleware):
    """
    Adapter for Django middleware.

    Allows using Django middleware in VayuAPI.

    Example:
        ```python
        from django.middleware.csrf import CsrfViewMiddleware

        app.add_middleware(DjangoMiddlewareAdapter(CsrfViewMiddleware))
        ```
    """

    def __init__(self, django_middleware_class):
        self.django_middleware_class = django_middleware_class
        self.middleware_instance = None

    def _get_instance(self, get_response):
        """Get or create Django middleware instance."""
        if self.middleware_instance is None:
            self.middleware_instance = self.django_middleware_class(get_response)
        return self.middleware_instance

    async def __call__(self, request: Request, call_next: Callable):
        """Process request through Django middleware."""
        # Convert Starlette request to Django request
        django_request = self._convert_to_django_request(request)

        # Get middleware instance
        def get_response(req):
            return None  # Will be replaced

        middleware = self._get_instance(get_response)

        # Process request
        if hasattr(middleware, 'process_request'):
            response = middleware.process_request(django_request)
            if response:
                return self._convert_to_starlette_response(response)

        # Call next
        response = await call_next(request)

        # Process response
        if hasattr(middleware, 'process_response'):
            django_response = self._convert_to_django_response(response)
            response = middleware.process_response(django_request, django_response)
            response = self._convert_to_starlette_response(response)

        return response

    def _convert_to_django_request(self, request: Request):
        """Convert Starlette request to Django request."""
        # This would require django.http.HttpRequest
        # Simplified for now
        return request

    def _convert_to_starlette_response(self, response):
        """Convert Django response to Starlette response."""
        return response

    def _convert_to_django_response(self, response: Response):
        """Convert Starlette response to Django response."""
        return response


class RateLimitMiddleware(Middleware):
    """
    Rate limiting middleware.
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # In production, use Redis

    async def process_request(self, request: Request):
        """Check rate limit."""
        # Simple in-memory rate limiting
        # In production, use Redis or similar
        client_ip = request.client.host

        # Implementation would track requests per IP
        # and return 429 if limit exceeded
        pass


# ============================================================================
# Starlette Middleware Wrappers - Compatible with all Starlette parameters
# ============================================================================


class CORSMiddleware:
    """
    CORS (Cross-Origin Resource Sharing) middleware wrapper.

    All parameters from starlette.middleware.cors.CORSMiddleware are supported.

    Example:
        ```python
        from vayuapi.middleware import CORSMiddleware

        app.add_starlette_middleware(
            CORSMiddleware,
            allow_origins=["https://example.com"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Custom-Header"],
            max_age=600,
        )
        ```

    Args:
        allow_origins: List of origins allowed to make cross-origin requests
        allow_origin_regex: Regex pattern for allowed origins
        allow_methods: HTTP methods allowed for cross-origin requests
        allow_headers: HTTP headers allowed in cross-origin requests
        allow_credentials: Whether to allow credentials (cookies, authorization headers)
        expose_headers: Headers exposed to the browser
        max_age: Maximum age (in seconds) for browsers to cache CORS responses
    """

    def __init__(
        self,
        app: ASGIApp,
        allow_origins: Sequence[str] = (),
        allow_methods: Sequence[str] = ("GET",),
        allow_headers: Sequence[str] = (),
        allow_credentials: bool = False,
        allow_origin_regex: Optional[str] = None,
        expose_headers: Sequence[str] = (),
        max_age: int = 600,
    ) -> None:
        self.middleware = StarletteCORSMiddleware(
            app=app,
            allow_origins=allow_origins,
            allow_methods=allow_methods,
            allow_headers=allow_headers,
            allow_credentials=allow_credentials,
            allow_origin_regex=allow_origin_regex,
            expose_headers=expose_headers,
            max_age=max_age,
        )

    async def __call__(self, scope, receive, send):
        return await self.middleware(scope, receive, send)


class GZipMiddleware:
    """
    GZip compression middleware wrapper.

    All parameters from starlette.middleware.gzip.GZipMiddleware are supported.

    Example:
        ```python
        from vayuapi.middleware import GZipMiddleware

        app.add_starlette_middleware(
            GZipMiddleware,
            minimum_size=1000,
            compresslevel=6,
        )
        ```

    Args:
        minimum_size: Minimum response size (in bytes) to enable compression
        compresslevel: Compression level (1-9, where 9 is maximum compression)
    """

    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 500,
        compresslevel: int = 9,
    ) -> None:
        self.middleware = StarletteGZipMiddleware(
            app=app,
            minimum_size=minimum_size,
            compresslevel=compresslevel,
        )

    async def __call__(self, scope, receive, send):
        return await self.middleware(scope, receive, send)


class HTTPSRedirectMiddleware:
    """
    HTTPS redirect middleware wrapper.

    All parameters from starlette.middleware.httpsredirect.HTTPSRedirectMiddleware are supported.

    Example:
        ```python
        from vayuapi.middleware import HTTPSRedirectMiddleware

        app.add_starlette_middleware(HTTPSRedirectMiddleware)
        ```

    Automatically redirects HTTP requests to HTTPS.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.middleware = StarletteHTTPSRedirectMiddleware(app=app)

    async def __call__(self, scope, receive, send):
        return await self.middleware(scope, receive, send)


class TrustedHostMiddleware:
    """
    Trusted host middleware wrapper.

    All parameters from starlette.middleware.trustedhost.TrustedHostMiddleware are supported.

    Example:
        ```python
        from vayuapi.middleware import TrustedHostMiddleware

        app.add_starlette_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["example.com", "*.example.com"],
            www_redirect=True,
        )
        ```

    Args:
        allowed_hosts: List of allowed host names (supports wildcards)
        www_redirect: Whether to redirect www prefix
    """

    def __init__(
        self,
        app: ASGIApp,
        allowed_hosts: Sequence[str] = None,
        www_redirect: bool = True,
    ) -> None:
        self.middleware = StarletteTrustedHostMiddleware(
            app=app,
            allowed_hosts=allowed_hosts or ["*"],
            www_redirect=www_redirect,
        )

    async def __call__(self, scope, receive, send):
        return await self.middleware(scope, receive, send)


class SessionMiddleware:
    """
    Session middleware wrapper.

    All parameters from starlette.middleware.sessions.SessionMiddleware are supported.

    Example:
        ```python
        from vayuapi.middleware import SessionMiddleware

        app.add_starlette_middleware(
            SessionMiddleware,
            secret_key="your-secret-key",
            session_cookie="session",
            max_age=14 * 24 * 60 * 60,  # 14 days
            same_site="lax",
            https_only=False,
        )
        ```

    Args:
        secret_key: Secret key for signing session cookies
        session_cookie: Name of the session cookie
        max_age: Session cookie max age in seconds (None for browser session)
        path: Cookie path
        same_site: Cookie same-site policy ("lax", "strict", or "none")
        https_only: Whether cookie should be HTTPS only
        domain: Cookie domain
    """

    def __init__(
        self,
        app: ASGIApp,
        secret_key: str,
        session_cookie: str = "session",
        max_age: Optional[int] = 14 * 24 * 60 * 60,
        path: str = "/",
        same_site: str = "lax",
        https_only: bool = False,
        domain: Optional[str] = None,
    ) -> None:
        self.middleware = StarletteSessionMiddleware(
            app=app,
            secret_key=secret_key,
            session_cookie=session_cookie,
            max_age=max_age,
            path=path,
            same_site=same_site,
            https_only=https_only,
            domain=domain,
        )

    async def __call__(self, scope, receive, send):
        return await self.middleware(scope, receive, send)


class AuthenticationMiddleware(Middleware):
    """
    Authentication middleware base class.

    Example:
        ```python
        from vayuapi.middleware import AuthenticationMiddleware

        class JWTAuthMiddleware(AuthenticationMiddleware):
            async def process_request(self, request):
                token = request.headers.get("Authorization")
                if token:
                    request.state.user = decode_jwt(token)
                else:
                    request.state.user = None

        app.add_middleware(JWTAuthMiddleware())
        ```
    """
    pass


class BaseHTTPMiddleware:
    """
    Base HTTP middleware for creating custom middleware.

    Example:
        ```python
        from vayuapi.middleware import BaseHTTPMiddleware
        from starlette.requests import Request

        class CustomMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                # Process request
                response = await call_next(request)
                # Process response
                response.headers["X-Custom-Header"] = "Value"
                return response

        app.add_middleware(CustomMiddleware())
        ```
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Override this method to implement custom middleware logic."""
        return await call_next(request)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        middleware = StarletteBase(self.app)
        middleware.dispatch = self.dispatch
        await middleware(scope, receive, send)


class RequestLoggingMiddleware(Middleware):
    """
    Request logging middleware.

    Example:
        ```python
        from vayuapi.middleware import RequestLoggingMiddleware

        app.add_middleware(RequestLoggingMiddleware())
        ```

    Logs all incoming requests with method, path, and response status.
    """

    async def process_request(self, request: Request):
        """Log incoming request."""
        logger = logging.getLogger("vayuapi")
        logger.info(f"Request: {request.method} {request.url.path}")

    async def process_response(self, request: Request, response: Response) -> Response:
        """Log response status."""
        logger = logging.getLogger("vayuapi")
        logger.info(f"Response: {response.status_code} for {request.method} {request.url.path}")
        return response
