"""
Decorators for VayuAPI
"""

from typing import Callable, List


def route(path: str, methods: List[str] = None, **kwargs):
    """Route decorator."""
    def decorator(func: Callable):
        func._route_path = path
        func._route_methods = methods or ["GET"]
        func._route_kwargs = kwargs
        return func
    return decorator


def get(path: str, **kwargs):
    """GET request decorator."""
    return route(path, methods=["GET"], **kwargs)


def post(path: str, **kwargs):
    """POST request decorator."""
    return route(path, methods=["POST"], **kwargs)


def put(path: str, **kwargs):
    """PUT request decorator."""
    return route(path, methods=["PUT"], **kwargs)


def delete(path: str, **kwargs):
    """DELETE request decorator."""
    return route(path, methods=["DELETE"], **kwargs)


def patch(path: str, **kwargs):
    """PATCH request decorator."""
    return route(path, methods=["PATCH"], **kwargs)


def websocket(path: str, **kwargs):
    """WebSocket decorator."""
    def decorator(func: Callable):
        func._websocket_path = path
        func._websocket_kwargs = kwargs
        return func
    return decorator
