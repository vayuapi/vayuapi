#__init__
"""
VayuAPI - The fastest Python async API framework
"""

__version__ = "0.1.0"
__author__ = "VayuAPI Team"
__license__ = "MIT"

from vayuapi.core.application import VayuAPI
from vayuapi.core.responses import JSONResponse
from vayuapi.core.routing import Router, Route
from vayuapi.core.middleware import Middleware
from vayuapi.core.websocket import WebSocket, WebSocketManager
from vayuapi.core.templating import Jinja2Templates
from vayuapi.core.staticfiles import StaticFiles

# Parameter types
from vayuapi.core.params import (
    Path,
    Query,
    Header,
    Cookie,
    Body,
    Form,
    File,
)

# Dependency injection (basic Depends/Security)
from vayuapi.core.dependencies import Depends, Security

# IoC / DI Container
from vayuapi.di import (
    DIContainer,
    ServiceLifetime,
    ServiceDescriptor,
    ServiceScope,
    ServiceProvider,
    injectable,
    inject,
)
from vayuapi.di.injectable import register_injectables

# File uploads
from vayuapi.core.uploads import UploadFile

# Native Concurrency & Low Overhead
from vayuapi.core.concurrency import (
    run_in_thread,
    run_in_process,
    to_thread,
    Semaphore,
    RateLimiter,
    ConnectionPool,
    BackgroundTasks,
    AsyncLRUCache,
    BatchProcessor,
)

# Exception handling
from vayuapi.core.exceptions import (
    HTTPException,
    RequestValidationError,
    WebSocketException,
    BadRequestException,
    UnauthorizedException,
    ForbiddenException,
    NotFoundException,
    MethodNotAllowedException,
    ConflictException,
    UnprocessableEntityException,
    InternalServerErrorException,
    ServiceUnavailableException,
)

# Request/Response types
from starlette.requests import Request
from starlette.responses import (
    Response,
    HTMLResponse,
    StreamingResponse,
    FileResponse,
)

# Decorators
from vayuapi.core.decorators import (
    route,
    get,
    post,
    put,
    delete,
    patch,
    websocket,
)

# HTTP Status codes
from vayuapi import status

__all__ = [
    "VayuAPI",
    "Router",
    "Route",
    "Middleware",
    "WebSocket",
    "WebSocketManager",
    "Jinja2Templates",
    "StaticFiles",
    "Request",
    "Response",
    "JSONResponse",
    "HTMLResponse",
    "StreamingResponse",
    "FileResponse",
    # Parameters
    "Path",
    "Query",
    "Header",
    "Cookie",
    "Body",
    "Form",
    "File",
    # Dependency injection (basic)
    "Depends",
    "Security",
    # IoC DI Container
    "DIContainer",
    "ServiceLifetime",
    "ServiceDescriptor",
    "ServiceScope",
    "ServiceProvider",
    "injectable",
    "inject",
    "register_injectables",
    # File uploads
    "UploadFile",
    # Concurrency & Low Overhead
    "run_in_thread",
    "run_in_process",
    "to_thread",
    "Semaphore",
    "RateLimiter",
    "ConnectionPool",
    "BackgroundTasks",
    "AsyncLRUCache",
    "BatchProcessor",
    # Exceptions
    "HTTPException",
    "RequestValidationError",
    "WebSocketException",
    "BadRequestException",
    "UnauthorizedException",
    "ForbiddenException",
    "NotFoundException",
    "MethodNotAllowedException",
    "ConflictException",
    "UnprocessableEntityException",
    "InternalServerErrorException",
    "ServiceUnavailableException",
    # Decorators
    "route",
    "get",
    "post",
    "put",
    "delete",
    "patch",
    "websocket",
    # Status codes
    "status",
    "__version__",
]
