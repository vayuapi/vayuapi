"""
gRPC decorators for VayuAPI — @grpc_service, @grpc_method, @grpc_stream.
"""

from __future__ import annotations

import functools
import inspect
from typing import Any, Callable, Optional, Type, TypeVar

T = TypeVar("T")


def grpc_service(
    server_or_name=None,
    *,
    service_name: Optional[str] = None,
):
    """
    Decorator to mark a class as a gRPC service and optionally auto-register
    it with a VayuGRPCServer instance.

    Example::

        from vayuapi.grpc import VayuGRPCServer, grpc_service, grpc_method

        grpc_server = VayuGRPCServer(port=50051)

        @grpc_service(grpc_server)
        class GreeterService:
            @grpc_method
            async def SayHello(self, request, context):
                return {"message": f"Hello {request['name']}"}

    When ``server_or_name`` is a ``VayuGRPCServer`` instance the class is
    automatically registered. When it is a string it is used as the service
    name. When omitted the class name is used.
    """
    from vayuapi.grpc.server import VayuGRPCServer

    def _decorate(cls: Type[T]) -> Type[T]:
        name = (
            service_name
            or (server_or_name if isinstance(server_or_name, str) else None)
            or cls.__name__
        )
        cls.__grpc_service_name__ = name
        cls.__is_grpc_service__ = True

        if isinstance(server_or_name, VayuGRPCServer):
            server_or_name._register_dynamic_service(cls)

        return cls

    # Called as @grpc_service  (no parentheses, cls passed directly)
    if server_or_name is not None and isinstance(server_or_name, type):
        return _decorate(server_or_name)

    return _decorate


def grpc_method(
    func: Optional[Callable] = None,
    *,
    request_type: Optional[Any] = None,
    response_type: Optional[Any] = None,
):
    """
    Mark a method inside a ``@grpc_service`` class as a gRPC unary handler.

    Example::

        @grpc_service
        class UserService:
            @grpc_method
            async def GetUser(self, request, context):
                return {"id": request["id"], "name": "Alice"}
    """
    def decorator(fn: Callable) -> Callable:
        fn.__grpc_method__ = {
            "stream_request": False,
            "stream_response": False,
            "request_type": request_type,
            "response_type": response_type,
        }

        @functools.wraps(fn)
        async def wrapper(self, request, context):
            if inspect.iscoroutinefunction(fn):
                return await fn(self, request, context)
            return fn(self, request, context)

        wrapper.__grpc_method__ = fn.__grpc_method__
        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


def grpc_stream(
    func: Optional[Callable] = None,
    *,
    stream_request: bool = False,
    stream_response: bool = True,
    request_type: Optional[Any] = None,
    response_type: Optional[Any] = None,
):
    """
    Mark a method as a gRPC streaming handler.

    Args:
        stream_request: True if the client streams requests.
        stream_response: True if the server streams responses.

    Example — server-streaming::

        @grpc_service
        class NewsService:
            @grpc_stream(stream_response=True)
            async def Subscribe(self, request, context):
                for item in get_news_feed():
                    yield item

    Example — bidirectional streaming::

        @grpc_service
        class ChatService:
            @grpc_stream(stream_request=True, stream_response=True)
            async def Chat(self, request_iterator, context):
                async for msg in request_iterator:
                    yield {"reply": f"Echo: {msg['text']}"}
    """
    def decorator(fn: Callable) -> Callable:
        fn.__grpc_method__ = {
            "stream_request": stream_request,
            "stream_response": stream_response,
            "request_type": request_type,
            "response_type": response_type,
        }

        @functools.wraps(fn)
        async def wrapper(self, request_or_iterator, context):
            result = fn(self, request_or_iterator, context)
            if inspect.isasyncgen(result):
                async for item in result:
                    yield item
            elif inspect.iscoroutine(result):
                yield await result
            else:
                yield result

        wrapper.__grpc_method__ = fn.__grpc_method__
        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


__all__ = ["grpc_service", "grpc_method", "grpc_stream"]
