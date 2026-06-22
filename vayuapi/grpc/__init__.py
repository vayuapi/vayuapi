"""
VayuAPI gRPC integration.
Provides a gRPC server that can run alongside the ASGI application.
"""

from vayuapi.grpc.server import VayuGRPCServer
from vayuapi.grpc.decorators import grpc_service, grpc_method, grpc_stream
from vayuapi.grpc.client import GRPCClient

__all__ = [
    "VayuGRPCServer",
    "GRPCClient",
    "grpc_service",
    "grpc_method",
    "grpc_stream",
]
