"""
Exception handling for VayuAPI

Compatible with FastAPI/Starlette exception handling.
"""

from typing import Any, Callable, Dict, Optional
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR


class HTTPException(StarletteHTTPException):
    """
    HTTP exception that can be raised to return an HTTP error response.

    Example:
        ```python
        from vayuapi import HTTPException

        @app.get("/items/{item_id}")
        async def get_item(item_id: int):
            if item_id not in items:
                raise HTTPException(status_code=404, detail="Item not found")
            return items[item_id]
        ```

    Args:
        status_code: HTTP status code
        detail: Error detail message
        headers: Optional response headers
    """

    def __init__(
            self,
            status_code: int,
            detail: Any = None,
            headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class RequestValidationError(Exception):
    """
    Raised when request validation fails.

    Example:
        ```python
        from vayuapi import RequestValidationError

        @app.post("/users")
        async def create_user(user: UserModel):
            if not user.email:
                raise RequestValidationError("Email is required")
            return user
        ```
    """

    def __init__(self, errors: Any):
        self.errors = errors
        super().__init__(str(errors))


class WebSocketException(Exception):
    """
    Exception that can be raised in WebSocket endpoints.

    Example:
        ```python
        from vayuapi import WebSocketException

        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            if not is_authenticated(websocket):
                raise WebSocketException(code=1008, reason="Unauthorized")
        ```

    Args:
        code: WebSocket close code
        reason: Close reason
    """

    def __init__(self, code: int = 1000, reason: str = ""):
        self.code = code
        self.reason = reason
        super().__init__(reason)


class ExceptionHandler:
    """
    Exception handler manager for VayuAPI.

    Manages custom exception handlers for different exception types.
    """

    def __init__(self):
        self.handlers: Dict[type, Callable] = {}
        self._setup_default_handlers()

    def _setup_default_handlers(self):
        """Setup default exception handlers."""

        # HTTP Exception handler
        async def http_exception_handler(request: Request, exc: HTTPException) -> Response:
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=getattr(exc, "headers", None),
            )

        # Validation error handler
        async def validation_exception_handler(request: Request, exc: RequestValidationError) -> Response:
            return JSONResponse(
                status_code=422,
                content={"detail": exc.errors},
            )

        # Generic exception handler
        async def generic_exception_handler(request: Request, exc: Exception) -> Response:
            return JSONResponse(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error", "error": str(exc)},
            )

        self.handlers[HTTPException] = http_exception_handler
        self.handlers[StarletteHTTPException] = http_exception_handler
        self.handlers[RequestValidationError] = validation_exception_handler
        self.handlers[Exception] = generic_exception_handler

    def add_handler(self, exc_class: type, handler: Callable):
        """
        Add a custom exception handler.

        Args:
            exc_class: Exception class to handle
            handler: Async function that handles the exception

        Example:
            ```python
            async def custom_handler(request: Request, exc: CustomException):
                return JSONResponse(
                    status_code=400,
                    content={"error": str(exc)}
                )

            app.add_exception_handler(CustomException, custom_handler)
            ```
        """
        self.handlers[exc_class] = handler

    def get_handler(self, exc_class: type) -> Optional[Callable]:
        """Get handler for exception class."""
        # Try exact match first
        if exc_class in self.handlers:
            return self.handlers[exc_class]

        # Try parent classes
        for exc_type, handler in self.handlers.items():
            if issubclass(exc_class, exc_type):
                return handler

        # Return generic handler
        return self.handlers.get(Exception)

    async def handle(self, request: Request, exc: Exception) -> Response:
        """
        Handle an exception.

        Args:
            request: The request that caused the exception
            exc: The exception to handle

        Returns:
            Response object
        """
        handler = self.get_handler(type(exc))
        if handler:
            return await handler(request, exc)

        # Fallback to generic error
        return JSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )


# Common HTTP exceptions for convenience
class BadRequestException(HTTPException):
    """400 Bad Request"""

    def __init__(self, detail: str = "Bad Request", headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=400, detail=detail, headers=headers)


class UnauthorizedException(HTTPException):
    """401 Unauthorized"""

    def __init__(self, detail: str = "Unauthorized", headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=401, detail=detail, headers=headers)


class ForbiddenException(HTTPException):
    """403 Forbidden"""

    def __init__(self, detail: str = "Forbidden", headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=403, detail=detail, headers=headers)


class NotFoundException(HTTPException):
    """404 Not Found"""

    def __init__(self, detail: str = "Not Found", headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=404, detail=detail, headers=headers)


class MethodNotAllowedException(HTTPException):
    """405 Method Not Allowed"""

    def __init__(self, detail: str = "Method Not Allowed", headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=405, detail=detail, headers=headers)


class ConflictException(HTTPException):
    """409 Conflict"""

    def __init__(self, detail: str = "Conflict", headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=409, detail=detail, headers=headers)


class UnprocessableEntityException(HTTPException):
    """422 Unprocessable Entity"""

    def __init__(self, detail: str = "Unprocessable Entity", headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=422, detail=detail, headers=headers)


class InternalServerErrorException(HTTPException):
    """500 Internal Server Error"""

    def __init__(self, detail: str = "Internal Server Error", headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=500, detail=detail, headers=headers)


class ServiceUnavailableException(HTTPException):
    """503 Service Unavailable"""

    def __init__(self, detail: str = "Service Unavailable", headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=503, detail=detail, headers=headers)
