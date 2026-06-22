"""
VayuGRPCServer — runs a gRPC server in a background asyncio task,
side-by-side with the VayuAPI ASGI application.

Dependencies (install with `pip install vayuapi[grpc]`):
    grpcio>=1.60.0
    grpcio-tools>=1.60.0      (optional, for .proto compilation)
    grpcio-reflection>=1.60.0 (optional, for server reflection)
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Type

logger = logging.getLogger("vayuapi.grpc")


def _require_grpc():
    try:
        import grpc
        import grpc.aio
        return grpc
    except ImportError:
        raise ImportError(
            "grpcio is required for gRPC support. "
            "Install it with: pip install 'vayuapi[grpc]' or pip install grpcio"
        )


class ServiceRegistration:
    """Internal record of a registered gRPC service."""

    def __init__(
        self,
        servicer_class: Type,
        add_servicer_fn: Callable,
        instance: Optional[Any] = None,
    ):
        self.servicer_class = servicer_class
        self.add_servicer_fn = add_servicer_fn
        self.instance = instance or servicer_class()


class VayuGRPCServer:
    """
    Async gRPC server that integrates with VayuAPI.

    The server runs as a background asyncio task so the ASGI application
    and the gRPC server share the same event loop.

    Example::

        import vayuapi_pb2_grpc  # generated from your .proto

        grpc_server = VayuGRPCServer(port=50051)

        @app.on_event("startup")
        async def startup():
            grpc_server.add_service(
                GreeterServicer,
                vayuapi_pb2_grpc.add_GreeterServicer_to_server,
            )
            await grpc_server.start()

        @app.on_event("shutdown")
        async def shutdown():
            await grpc_server.stop()

    You can also use the ``@grpc_service`` decorator for auto-registration::

        from vayuapi.grpc import grpc_service, grpc_method, VayuGRPCServer

        grpc_server = VayuGRPCServer(port=50051)

        @grpc_service(grpc_server)
        class GreeterService:
            @grpc_method
            async def SayHello(self, request, context):
                return HelloReply(message=f"Hello, {request.name}")
    """

    def __init__(
        self,
        port: int = 50051,
        host: str = "[::]",
        max_workers: int = 10,
        max_concurrent_rpcs: Optional[int] = None,
        interceptors: Optional[Sequence] = None,
        options: Optional[List[Tuple[str, Any]]] = None,
        compression=None,
        enable_reflection: bool = False,
        reflection_service_names: Optional[List[str]] = None,
    ):
        self.port = port
        self.host = host
        self.max_workers = max_workers
        self.max_concurrent_rpcs = max_concurrent_rpcs
        self.interceptors = interceptors or []
        self.options = options or []
        self.compression = compression
        self.enable_reflection = enable_reflection
        self.reflection_service_names = reflection_service_names or []

        self._registrations: List[ServiceRegistration] = []
        self._server = None
        self._task: Optional[asyncio.Task] = None
        self._running = False

    # ------------------------------------------------------------------
    # Service registration
    # ------------------------------------------------------------------

    def add_service(
        self,
        servicer_class: Type,
        add_servicer_fn: Callable,
        instance: Optional[Any] = None,
    ) -> "VayuGRPCServer":
        """
        Register a gRPC servicer.

        Args:
            servicer_class: The servicer class (usually from generated pb2_grpc).
            add_servicer_fn: The generated ``add_XxxServicer_to_server`` function.
            instance: Optional pre-created instance; if None, the class is
                      instantiated with no arguments.
        """
        reg = ServiceRegistration(servicer_class, add_servicer_fn, instance)
        self._registrations.append(reg)
        return self

    def _register_dynamic_service(self, service_cls: Type) -> None:
        """Register a service class decorated with @grpc_service (no protobuf)."""
        self._registrations.append(
            ServiceRegistration.__new__(ServiceRegistration)
        )
        reg = self._registrations[-1]
        reg.servicer_class = service_cls
        reg.add_servicer_fn = None   # handled by generic handler
        reg.instance = service_cls()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the gRPC server in a background asyncio task."""
        grpc = _require_grpc()

        self._server = grpc.aio.server(
            interceptors=self.interceptors,
            options=self.options,
            maximum_concurrent_rpcs=self.max_concurrent_rpcs,
            compression=self.compression,
        )

        for reg in self._registrations:
            if reg.add_servicer_fn is not None:
                reg.add_servicer_fn(reg.instance, self._server)
            else:
                self._attach_generic_handler(reg.instance, self._server)

        if self.enable_reflection:
            try:
                from grpc_reflection.v1alpha import reflection
                reflection.enable_server_reflection(
                    self.reflection_service_names or [reflection.SERVICE_NAME],
                    self._server,
                )
            except ImportError:
                logger.warning(
                    "grpcio-reflection is not installed; server reflection disabled. "
                    "Install with: pip install grpcio-reflection"
                )

        listen_addr = f"{self.host}:{self.port}"
        self._server.add_insecure_port(listen_addr)

        await self._server.start()
        self._running = True
        logger.info(f"VayuGRPCServer listening on {listen_addr}")

    def _attach_generic_handler(self, instance: Any, server) -> None:
        """
        Attach methods from a ``@grpc_service`` decorated class as generic
        unary handlers without needing generated stub code.
        """
        try:
            import grpc
        except ImportError:
            return

        service_name = getattr(instance, "__grpc_service_name__", type(instance).__name__)
        handlers: Dict[str, Any] = {}

        for attr_name in dir(type(instance)):
            method = getattr(type(instance), attr_name, None)
            if method is None:
                continue
            meta = getattr(method, "__grpc_method__", None)
            if meta is None:
                continue

            rpc_name = f"/{service_name}/{attr_name}"
            bound = getattr(instance, attr_name)

            if meta.get("stream_response") or meta.get("stream_request"):
                handlers[rpc_name] = grpc.method_handlers.unary_stream_rpc_method_handler(
                    bound
                )
            else:
                handlers[rpc_name] = grpc.method_handlers.unary_unary_rpc_method_handler(
                    bound
                )

        if handlers:
            server.add_generic_rpc_handlers(
                [grpc.method_service_handler(service_name, handlers)]
            )

    async def stop(self, grace: float = 5.0) -> None:
        """Gracefully stop the gRPC server."""
        if self._server is not None:
            await self._server.stop(grace)
            self._running = False
            logger.info("VayuGRPCServer stopped")

    async def wait_for_termination(self, timeout: Optional[float] = None) -> None:
        """Block until the server terminates."""
        if self._server is not None:
            await self._server.wait_for_termination(timeout=timeout)

    @property
    def is_running(self) -> bool:
        return self._running

    def __repr__(self) -> str:
        return f"VayuGRPCServer(host={self.host!r}, port={self.port})"


__all__ = ["VayuGRPCServer", "ServiceRegistration"]
