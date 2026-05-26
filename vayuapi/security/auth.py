"""
Authentication and security schemes for VayuAPI

FastAPI-compatible security schemes.
"""

from typing import Optional
from starlette.requests import Request
from vayuapi.core.exceptions import HTTPException
import base64


class HTTPBasic:
    """
    HTTP Basic authentication.

    Example:
        ```python
        from vayuapi import Depends
        from vayuapi.security import HTTPBasic

        security = HTTPBasic()

        @app.get("/protected/")
        async def protected_route(credentials = Depends(security)):
            return {"username": credentials.username}
        ```
    """

    def __init__(
        self,
        *,
        scheme_name: Optional[str] = None,
        realm: Optional[str] = None,
        auto_error: bool = True,
    ):
        self.scheme_name = scheme_name or "HTTPBasic"
        self.realm = realm
        self.auto_error = auto_error

    async def __call__(self, request: Request):
        """Extract Basic authentication credentials."""
        authorization = request.headers.get("Authorization")

        if not authorization:
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Basic"},
                )
            return None

        scheme, _, param = authorization.partition(" ")

        if scheme.lower() != "basic":
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Basic"},
                )
            return None

        try:
            data = base64.b64decode(param).decode("utf-8")
            username, _, password = data.partition(":")
            return HTTPBasicCredentials(username=username, password=password)
        except Exception:
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Basic"},
                )
            return None


class HTTPBearer:
    """
    HTTP Bearer token authentication.

    Example:
        ```python
        from vayuapi import Depends
        from vayuapi.security import HTTPBearer

        security = HTTPBearer()

        @app.get("/protected/")
        async def protected_route(token = Depends(security)):
            return {"token": token.credentials}
        ```
    """

    def __init__(
        self,
        *,
        scheme_name: Optional[str] = None,
        auto_error: bool = True,
    ):
        self.scheme_name = scheme_name or "HTTPBearer"
        self.auto_error = auto_error

    async def __call__(self, request: Request):
        """Extract Bearer token."""
        authorization = request.headers.get("Authorization")

        if not authorization:
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None

        scheme, _, param = authorization.partition(" ")

        if scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None

        return HTTPAuthorizationCredentials(scheme=scheme, credentials=param)


class HTTPDigest:
    """
    HTTP Digest authentication.

    Example:
        ```python
        from vayuapi import Depends
        from vayuapi.security import HTTPDigest

        security = HTTPDigest()

        @app.get("/protected/")
        async def protected_route(credentials = Depends(security)):
            return {"auth": "digest"}
        ```
    """

    def __init__(
        self,
        *,
        scheme_name: Optional[str] = None,
        auto_error: bool = True,
    ):
        self.scheme_name = scheme_name or "HTTPDigest"
        self.auto_error = auto_error

    async def __call__(self, request: Request):
        """Extract Digest authentication."""
        authorization = request.headers.get("Authorization")

        if not authorization:
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Digest"},
                )
            return None

        scheme, _, param = authorization.partition(" ")

        if scheme.lower() != "digest":
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Digest"},
                )
            return None

        return HTTPAuthorizationCredentials(scheme=scheme, credentials=param)


class APIKeyHeader:
    """
    API Key in header authentication.

    Example:
        ```python
        from vayuapi import Depends
        from vayuapi.security import APIKeyHeader

        api_key_header = APIKeyHeader(name="X-API-Key")

        @app.get("/protected/")
        async def protected_route(api_key = Depends(api_key_header)):
            return {"api_key": api_key}
        ```
    """

    def __init__(
        self,
        *,
        name: str,
        scheme_name: Optional[str] = None,
        auto_error: bool = True,
    ):
        self.name = name
        self.scheme_name = scheme_name or "APIKeyHeader"
        self.auto_error = auto_error

    async def __call__(self, request: Request):
        """Extract API key from header."""
        api_key = request.headers.get(self.name)

        if not api_key:
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Not authenticated"
                )
            return None

        return api_key


class APIKeyQuery:
    """
    API Key in query parameter authentication.

    Example:
        ```python
        from vayuapi import Depends
        from vayuapi.security import APIKeyQuery

        api_key_query = APIKeyQuery(name="api_key")

        @app.get("/protected/")
        async def protected_route(api_key = Depends(api_key_query)):
            return {"api_key": api_key}
        ```
    """

    def __init__(
        self,
        *,
        name: str,
        scheme_name: Optional[str] = None,
        auto_error: bool = True,
    ):
        self.name = name
        self.scheme_name = scheme_name or "APIKeyQuery"
        self.auto_error = auto_error

    async def __call__(self, request: Request):
        """Extract API key from query parameter."""
        api_key = request.query_params.get(self.name)

        if not api_key:
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Not authenticated"
                )
            return None

        return api_key


class APIKeyCookie:
    """
    API Key in cookie authentication.

    Example:
        ```python
        from vayuapi import Depends
        from vayuapi.security import APIKeyCookie

        api_key_cookie = APIKeyCookie(name="session")

        @app.get("/protected/")
        async def protected_route(session = Depends(api_key_cookie)):
            return {"session": session}
        ```
    """

    def __init__(
        self,
        *,
        name: str,
        scheme_name: Optional[str] = None,
        auto_error: bool = True,
    ):
        self.name = name
        self.scheme_name = scheme_name or "APIKeyCookie"
        self.auto_error = auto_error

    async def __call__(self, request: Request):
        """Extract API key from cookie."""
        api_key = request.cookies.get(self.name)

        if not api_key:
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Not authenticated"
                )
            return None

        return api_key


class OAuth2PasswordBearer:
    """
    OAuth2 password bearer flow.

    Example:
        ```python
        from vayuapi import Depends
        from vayuapi.security import OAuth2PasswordBearer

        # Both tokenUrl and token_url are supported
        oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
        # or
        oauth2_scheme = OAuth2PasswordBearer(token_url="/token")

        @app.get("/users/me")
        async def read_users_me(token = Depends(oauth2_scheme)):
            return decode_token(token)
        ```
    """

    def __init__(
        self,
        tokenUrl: str = None,
        token_url: str = None,
        *,
        scheme_name: Optional[str] = None,
        scopes: Optional[dict] = None,
        auto_error: bool = True,
    ):
        # Support both tokenUrl (FastAPI style) and token_url (Python style)
        if tokenUrl is None and token_url is None:
            raise ValueError("Either tokenUrl or token_url must be provided")

        self.tokenUrl = token_url if token_url is not None else tokenUrl
        self.scheme_name = scheme_name or "OAuth2PasswordBearer"
        self.scopes = scopes or {}
        self.auto_error = auto_error

    async def __call__(self, request: Request):
        """Extract OAuth2 token."""
        authorization = request.headers.get("Authorization")

        if not authorization:
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None

        scheme, _, param = authorization.partition(" ")

        if scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None

        return param


# Credentials models
class HTTPBasicCredentials:
    """HTTP Basic authentication credentials."""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password


class HTTPAuthorizationCredentials:
    """HTTP authorization credentials."""

    def __init__(self, scheme: str, credentials: str):
        self.scheme = scheme
        self.credentials = credentials


__all__ = [
    "HTTPBasic",
    "HTTPBearer",
    "HTTPDigest",
    "APIKeyHeader",
    "APIKeyQuery",
    "APIKeyCookie",
    "OAuth2PasswordBearer",
    "HTTPBasicCredentials",
    "HTTPAuthorizationCredentials",
]
