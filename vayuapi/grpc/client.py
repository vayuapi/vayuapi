"""
GRPCClient — async gRPC client helper for VayuAPI services.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional, Tuple, Type, TypeVar

logger = logging.getLogger("vayuapi.grpc.client")
T = TypeVar("T")


def _require_grpc():
    try:
        import grpc
        import grpc.aio
        return grpc
    except ImportError:
        raise ImportError(
            "grpcio is required. Install with: pip install 'vayuapi[grpc]'"
        )


class GRPCClient:
    """
    Async gRPC client that manages a channel and provides a convenient
    stub factory.

    Example::

        from vayuapi.grpc import GRPCClient
        import my_service_pb2_grpc

        client = GRPCClient(host="localhost", port=50051)

        async with client:
            stub = client.stub(my_service_pb2_grpc.GreeterStub)
            reply = await stub.SayHello(HelloRequest(name="World"))

    Or with explicit lifecycle management::

        await client.connect()
        stub = client.stub(my_service_pb2_grpc.GreeterStub)
        reply = await stub.SayHello(HelloRequest(name="World"))
        await client.close()
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 50051,
        *,
        secure: bool = False,
        credentials=None,
        options: Optional[list] = None,
        compression=None,
        interceptors: Optional[list] = None,
    ):
        self.host = host
        self.port = port
        self.secure = secure
        self.credentials = credentials
        self.options = options or []
        self.compression = compression
        self.interceptors = interceptors or []

        self._channel = None

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    async def connect(self) -> None:
        grpc = _require_grpc()
        if self._channel is not None:
            return

        kwargs = {}
        if self.compression is not None:
            kwargs["compression"] = self.compression

        if self.interceptors:
            kwargs["interceptors"] = self.interceptors

        if self.secure:
            creds = self.credentials or grpc.ssl_channel_credentials()
            self._channel = grpc.aio.secure_channel(self.address, creds, options=self.options, **kwargs)
        else:
            self._channel = grpc.aio.insecure_channel(self.address, options=self.options, **kwargs)

        logger.debug(f"GRPCClient connected to {self.address}")

    async def close(self) -> None:
        if self._channel is not None:
            await self._channel.close()
            self._channel = None
            logger.debug(f"GRPCClient disconnected from {self.address}")

    def stub(self, stub_class: Type[T]) -> T:
        """
        Create a stub from a generated pb2_grpc stub class.

        Args:
            stub_class: The generated stub class, e.g. ``GreeterStub``.

        Returns:
            Stub bound to the internal channel.
        """
        if self._channel is None:
            raise RuntimeError(
                "GRPCClient is not connected. Call `await client.connect()` "
                "or use `async with client:` before creating stubs."
            )
        return stub_class(self._channel)

    async def __aenter__(self) -> "GRPCClient":
        await self.connect()
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    def __repr__(self) -> str:
        connected = self._channel is not None
        return f"GRPCClient(address={self.address!r}, connected={connected})"


__all__ = ["GRPCClient"]
