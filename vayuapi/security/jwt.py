"""
JWT (JSON Web Token) Authentication for VayuAPI

Provides JWT token generation, validation, and authentication.
Compatible with FastAPI-style dependencies.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import secrets
from starlette.requests import Request
from vayuapi.core.exceptions import HTTPException


class JWTHandler:
    """
    JWT token handler for authentication.

    Example:
        ```python
        from vayuapi.security import JWTHandler

        jwt_handler = JWTHandler(
            secret_key="your-secret-key-keep-it-secret",
            algorithm="HS256",
            access_token_expire_minutes=30
        )

        # Create token
        token = jwt_handler.create_access_token(
            data={"sub": "user@example.com", "user_id": 123}
        )

        # Decode token
        payload = jwt_handler.decode_token(token)
        ```
    """

    def __init__(
        self,
        secret_key: str = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ):
        """
        Initialize JWT handler.

        Args:
            secret_key: Secret key for signing tokens (generates random if not provided)
            algorithm: JWT algorithm (HS256, HS384, HS512, RS256, etc.)
            access_token_expire_minutes: Access token expiration time in minutes
            refresh_token_expire_days: Refresh token expiration time in days
        """
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT access token.

        Args:
            data: Dictionary of claims to include in token
            expires_delta: Custom expiration time (overrides default)

        Returns:
            Encoded JWT token string
        """
        try:
            import jwt
        except ImportError:
            raise ImportError(
                "PyJWT is required for JWT authentication. "
                "Install it with: pip install pyjwt"
            )

        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT refresh token.

        Args:
            data: Dictionary of claims to include in token
            expires_delta: Custom expiration time (overrides default)

        Returns:
            Encoded JWT refresh token string
        """
        try:
            import jwt
        except ImportError:
            raise ImportError(
                "PyJWT is required for JWT authentication. "
                "Install it with: pip install pyjwt"
            )

        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode and validate JWT token.

        Args:
            token: JWT token string to decode

        Returns:
            Decoded token payload

        Raises:
            jwt.ExpiredSignatureError: If token has expired
            jwt.InvalidTokenError: If token is invalid
        """
        try:
            import jwt
        except ImportError:
            raise ImportError(
                "PyJWT is required for JWT authentication. "
                "Install it with: pip install pyjwt"
            )

        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise jwt.ExpiredSignatureError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise jwt.InvalidTokenError(f"Invalid token: {str(e)}")

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token and return payload if valid.

        Args:
            token: JWT token string to verify

        Returns:
            Token payload if valid, None otherwise
        """
        try:
            return self.decode_token(token)
        except Exception:
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """
        Generate new access token from refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New access token if refresh token is valid, None otherwise
        """
        try:
            payload = self.decode_token(refresh_token)

            # Verify it's a refresh token
            if payload.get("type") != "refresh":
                return None

            # Create new access token with same data (minus exp, iat, type)
            data = {k: v for k, v in payload.items() if k not in ["exp", "iat", "type"]}
            return self.create_access_token(data)
        except Exception:
            return None


class JWTBearer:
    """
    JWT Bearer token authentication dependency.

    Use as a dependency to protect routes with JWT authentication.

    Example:
        ```python
        from vayuapi import Depends
        from vayuapi.security import JWTBearer, JWTHandler

        # Option 1: Pass JWTHandler
        jwt_handler = JWTHandler(secret_key="your-secret-key")
        jwt_auth = JWTBearer(jwt_handler)

        # Option 2: Pass secret_key directly
        jwt_auth = JWTBearer(secret_key="your-secret-key")

        @app.get("/protected/")
        async def protected_route(payload = Depends(jwt_auth)):
            return {"user": payload.get("sub"), "user_id": payload.get("user_id")}
        ```
    """

    def __init__(
        self,
        jwt_handler: JWTHandler = None,
        secret_key: str = None,
        algorithm: str = "HS256",
        auto_error: bool = True,
        scheme_name: Optional[str] = None
    ):
        """
        Initialize JWT Bearer authentication.

        Args:
            jwt_handler: JWTHandler instance for token validation (optional if secret_key provided)
            secret_key: Secret key for JWT validation (creates JWTHandler internally)
            algorithm: JWT algorithm (default: HS256)
            auto_error: Raise HTTP 401 on authentication failure
            scheme_name: Name for OpenAPI documentation
        """
        if jwt_handler is None and secret_key is None:
            raise ValueError("Either jwt_handler or secret_key must be provided")

        if jwt_handler is not None:
            self.jwt_handler = jwt_handler
        else:
            # Create JWTHandler from secret_key
            self.jwt_handler = JWTHandler(secret_key=secret_key, algorithm=algorithm)

        self.auto_error = auto_error
        self.scheme_name = scheme_name or "JWTBearer"

    async def __call__(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Extract and validate JWT token from request.

        Args:
            request: Starlette Request object

        Returns:
            Token payload if valid

        Raises:
            HTTPException: If auto_error is True and authentication fails
        """
        authorization = request.headers.get("Authorization")

        if not authorization:
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None

        scheme, _, token = authorization.partition(" ")

        if scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication scheme",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None

        if not token:
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None

        try:
            payload = self.jwt_handler.decode_token(token)
            return payload
        except Exception as e:
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail=f"Could not validate credentials: {str(e)}",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None


class JWTAuth:
    """
    Complete JWT authentication system with login and token management.

    Provides ready-to-use JWT authentication endpoints.

    Example:
        ```python
        from vayuapi import VayuAPI
        from vayuapi.security import JWTAuth

        app = VayuAPI()

        # Initialize JWT auth
        jwt_auth = JWTAuth(
            secret_key="your-secret-key",
            token_url="/auth/login"
        )

        # Access properties
        print(jwt_auth.algorithm)  # "HS256"
        print(jwt_auth.access_token_expire_minutes)  # 30

        # Add JWT routes
        jwt_auth.add_routes(app)

        # Protect routes
        @app.get("/protected/")
        async def protected(user = Depends(jwt_auth.get_current_user)):
            return {"user": user}
        ```

    Properties:
        secret_key: The secret key used for signing tokens
        algorithm: The JWT algorithm (e.g., "HS256")
        access_token_expire_minutes: Access token expiration time
        refresh_token_expire_days: Refresh token expiration time
    """

    def __init__(
        self,
        secret_key: str = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
        token_url: str = "/auth/token",
    ):
        """
        Initialize JWT authentication system.

        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm
            access_token_expire_minutes: Access token expiration
            refresh_token_expire_days: Refresh token expiration
            token_url: URL for token endpoint
        """
        self.jwt_handler = JWTHandler(
            secret_key=secret_key,
            algorithm=algorithm,
            access_token_expire_minutes=access_token_expire_minutes,
            refresh_token_expire_days=refresh_token_expire_days,
        )
        self.jwt_bearer = JWTBearer(self.jwt_handler)
        self.token_url = token_url
#--------------------------Added--------------------------------
    @property
    def secret_key(self) -> str:
        """Get the secret key from jwt_handler."""
        return self.jwt_handler.secret_key

    @property
    def algorithm(self) -> str:
        """Get the algorithm from jwt_handler."""
        return self.jwt_handler.algorithm

    @property
    def access_token_expire_minutes(self) -> int:
        """Get the access token expiration time."""
        return self.jwt_handler.access_token_expire_minutes

    @property
    def refresh_token_expire_days(self) -> int:
        """Get the refresh token expiration time."""
        return self.jwt_handler.refresh_token_expire_days
#------------------------------ended----------------------------------
    def get_current_user(self):
        """
        Dependency to get current authenticated user from JWT token.

        Returns:
            Dependency function for use with Depends()
        """
        return self.jwt_bearer

    def create_tokens(self, user_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Create access and refresh tokens for a user.

        Args:
            user_data: User information to include in token

        Returns:
            Dictionary with access_token and refresh_token
        """
        access_token = self.jwt_handler.create_access_token(user_data)
        refresh_token = self.jwt_handler.create_refresh_token(user_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token."""
        return self.jwt_handler.verify_token(token)


__all__ = [
    "JWTHandler",
    "JWTBearer",
    "JWTAuth",
]
