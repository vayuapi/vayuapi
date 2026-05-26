"""
FastAPI-style parameter types for VayuAPI

Includes Path, Query, Header, Cookie, Body, Form, File parameters
with validation and documentation support.
"""

from typing import Any, Optional, Type
from enum import Enum


class ParamType(str, Enum):
    """Parameter type enum."""
    PATH = "path"
    QUERY = "query"
    HEADER = "header"
    COOKIE = "cookie"
    BODY = "body"
    FORM = "form"
    FILE = "file"


class Param:
    """
    Base parameter class.

    Used internally by Path, Query, Header, etc.
    """

    def __init__(
            self,
            default: Any = ...,
            *,
            alias: Optional[str] = None,
            title: Optional[str] = None,
            description: Optional[str] = None,
            gt: Optional[float] = None,
            ge: Optional[float] = None,
            lt: Optional[float] = None,
            le: Optional[float] = None,
            min_length: Optional[int] = None,
            max_length: Optional[int] = None,
            regex: Optional[str] = None,
            example: Any = None,
            examples: Optional[dict] = None,
            deprecated: bool = False,
            include_in_schema: bool = True,
            param_type: ParamType = ParamType.QUERY,
            **extra: Any,
    ):
        self.default = default
        self.alias = alias
        self.title = title
        self.description = description
        self.gt = gt
        self.ge = ge
        self.lt = lt
        self.le = le
        self.min_length = min_length
        self.max_length = max_length
        self.regex = regex
        self.example = example
        self.examples = examples
        self.deprecated = deprecated
        self.include_in_schema = include_in_schema
        self.param_type = param_type
        self.extra = extra

    def __repr__(self):
        return f"{self.__class__.__name__}(default={self.default})"


def Path(
        default: Any = ...,
        *,
        alias: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        gt: Optional[float] = None,
        ge: Optional[float] = None,
        lt: Optional[float] = None,
        le: Optional[float] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        regex: Optional[str] = None,
        example: Any = None,
        examples: Optional[dict] = None,
        deprecated: bool = False,
        include_in_schema: bool = True,
        **extra: Any,
) -> Any:
    """
    Path parameter declaration.

    Example:
        ```python
        from vayuapi import Path

        @app.get("/items/{item_id}")
        async def get_item(
            item_id: int = Path(..., description="The item ID", gt=0)
        ):
            return {"item_id": item_id}
        ```

    Args:
        default: Default value (use ... for required)
        alias: Alternative name for the parameter
        title: Title for documentation
        description: Description for documentation
        gt: Greater than validation
        ge: Greater than or equal validation
        lt: Less than validation
        le: Less than or equal validation
        min_length: Minimum length for strings
        max_length: Maximum length for strings
        regex: Regex pattern for strings
        example: Example value
        examples: Multiple examples
        deprecated: Mark as deprecated
        include_in_schema: Include in OpenAPI schema
    """
    return Param(
        default=default,
        alias=alias,
        title=title,
        description=description,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        min_length=min_length,
        max_length=max_length,
        regex=regex,
        example=example,
        examples=examples,
        deprecated=deprecated,
        include_in_schema=include_in_schema,
        param_type=ParamType.PATH,
        **extra,
    )


def Query(
        default: Any = ...,
        *,
        alias: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        gt: Optional[float] = None,
        ge: Optional[float] = None,
        lt: Optional[float] = None,
        le: Optional[float] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        regex: Optional[str] = None,
        example: Any = None,
        examples: Optional[dict] = None,
        deprecated: bool = False,
        include_in_schema: bool = True,
        **extra: Any,
) -> Any:
    """
    Query parameter declaration.

    Example:
        ```python
        from vayuapi import Query

        @app.get("/items/")
        async def list_items(
            skip: int = Query(0, ge=0),
            limit: int = Query(10, ge=1, le=100),
            q: Optional[str] = Query(None, max_length=50)
        ):
            return {"skip": skip, "limit": limit, "q": q}
        ```

    Args:
        default: Default value (use ... for required)
        alias: Alternative name for the parameter
        title: Title for documentation
        description: Description for documentation
        gt: Greater than validation
        ge: Greater than or equal validation
        lt: Less than validation
        le: Less than or equal validation
        min_length: Minimum length for strings
        max_length: Maximum length for strings
        regex: Regex pattern for strings
        example: Example value
        examples: Multiple examples
        deprecated: Mark as deprecated
        include_in_schema: Include in OpenAPI schema
    """
    return Param(
        default=default,
        alias=alias,
        title=title,
        description=description,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        min_length=min_length,
        max_length=max_length,
        regex=regex,
        example=example,
        examples=examples,
        deprecated=deprecated,
        include_in_schema=include_in_schema,
        param_type=ParamType.QUERY,
        **extra,
    )


def Header(
        default: Any = ...,
        *,
        alias: Optional[str] = None,
        convert_underscores: bool = True,
        title: Optional[str] = None,
        description: Optional[str] = None,
        gt: Optional[float] = None,
        ge: Optional[float] = None,
        lt: Optional[float] = None,
        le: Optional[float] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        regex: Optional[str] = None,
        example: Any = None,
        examples: Optional[dict] = None,
        deprecated: bool = False,
        include_in_schema: bool = True,
        **extra: Any,
) -> Any:
    """
    Header parameter declaration.

    Example:
        ```python
        from vayuapi import Header

        @app.get("/items/")
        async def get_items(
            user_agent: Optional[str] = Header(None),
            x_token: str = Header(..., alias="X-Token")
        ):
            return {"user_agent": user_agent, "token": x_token}
        ```

    Args:
        default: Default value (use ... for required)
        alias: Alternative name for the header
        convert_underscores: Convert underscores to hyphens in header names
        title: Title for documentation
        description: Description for documentation
        example: Example value
        deprecated: Mark as deprecated
        include_in_schema: Include in OpenAPI schema
    """
    param = Param(
        default=default,
        alias=alias,
        title=title,
        description=description,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        min_length=min_length,
        max_length=max_length,
        regex=regex,
        example=example,
        examples=examples,
        deprecated=deprecated,
        include_in_schema=include_in_schema,
        param_type=ParamType.HEADER,
        **extra,
    )
    param.convert_underscores = convert_underscores
    return param


def Cookie(
        default: Any = ...,
        *,
        alias: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        gt: Optional[float] = None,
        ge: Optional[float] = None,
        lt: Optional[float] = None,
        le: Optional[float] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        regex: Optional[str] = None,
        example: Any = None,
        examples: Optional[dict] = None,
        deprecated: bool = False,
        include_in_schema: bool = True,
        **extra: Any,
) -> Any:
    """
    Cookie parameter declaration.

    Example:
        ```python
        from vayuapi import Cookie

        @app.get("/items/")
        async def get_items(
            session_id: Optional[str] = Cookie(None)
        ):
            return {"session_id": session_id}
        ```

    Args:
        default: Default value (use ... for required)
        alias: Alternative name for the cookie
        title: Title for documentation
        description: Description for documentation
        example: Example value
        deprecated: Mark as deprecated
        include_in_schema: Include in OpenAPI schema
    """
    return Param(
        default=default,
        alias=alias,
        title=title,
        description=description,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        min_length=min_length,
        max_length=max_length,
        regex=regex,
        example=example,
        examples=examples,
        deprecated=deprecated,
        include_in_schema=include_in_schema,
        param_type=ParamType.COOKIE,
        **extra,
    )


def Body(
        default: Any = ...,
        *,
        embed: bool = False,
        media_type: str = "application/json",
        alias: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        gt: Optional[float] = None,
        ge: Optional[float] = None,
        lt: Optional[float] = None,
        le: Optional[float] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        regex: Optional[str] = None,
        example: Any = None,
        examples: Optional[dict] = None,
        deprecated: bool = False,
        include_in_schema: bool = True,
        **extra: Any,
) -> Any:
    """
    Body parameter declaration.

    Example:
        ```python
        from vayuapi import Body
        from pydantic import BaseModel

        @app.post("/items/")
        async def create_item(
            item: Item,
            importance: int = Body(...)
        ):
            return {"item": item, "importance": importance}
        ```

    Args:
        default: Default value (use ... for required)
        embed: Embed single value in JSON object
        media_type: Media type for the body
        alias: Alternative name for the parameter
        title: Title for documentation
        description: Description for documentation
        example: Example value
        deprecated: Mark as deprecated
        include_in_schema: Include in OpenAPI schema
    """
    param = Param(
        default=default,
        alias=alias,
        title=title,
        description=description,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        min_length=min_length,
        max_length=max_length,
        regex=regex,
        example=example,
        examples=examples,
        deprecated=deprecated,
        include_in_schema=include_in_schema,
        param_type=ParamType.BODY,
        **extra,
    )
    param.embed = embed
    param.media_type = media_type
    return param


def Form(
        default: Any = ...,
        *,
        alias: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        gt: Optional[float] = None,
        ge: Optional[float] = None,
        lt: Optional[float] = None,
        le: Optional[float] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        regex: Optional[str] = None,
        example: Any = None,
        examples: Optional[dict] = None,
        deprecated: bool = False,
        include_in_schema: bool = True,
        **extra: Any,
) -> Any:
    """
    Form data parameter declaration.

    Example:
        ```python
        from vayuapi import Form

        @app.post("/login/")
        async def login(
            username: str = Form(...),
            password: str = Form(...)
        ):
            return {"username": username}
        ```

    Args:
        default: Default value (use ... for required)
        alias: Alternative name for the field
        title: Title for documentation
        description: Description for documentation
        example: Example value
        deprecated: Mark as deprecated
        include_in_schema: Include in OpenAPI schema
    """
    return Param(
        default=default,
        alias=alias,
        title=title,
        description=description,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        min_length=min_length,
        max_length=max_length,
        regex=regex,
        example=example,
        examples=examples,
        deprecated=deprecated,
        include_in_schema=include_in_schema,
        param_type=ParamType.FORM,
        **extra,
    )


def File(
        default: Any = ...,
        *,
        alias: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        gt: Optional[float] = None,
        ge: Optional[float] = None,
        lt: Optional[float] = None,
        le: Optional[float] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        example: Any = None,
        examples: Optional[dict] = None,
        deprecated: bool = False,
        include_in_schema: bool = True,
        **extra: Any,
) -> Any:
    """
    File upload parameter declaration.

    Example:
        ```python
        from vayuapi import File, UploadFile

        @app.post("/upload/")
        async def upload_file(
            file: UploadFile = File(...)
        ):
            return {"filename": file.filename}
        ```

    Args:
        default: Default value (use ... for required)
        alias: Alternative name for the field
        title: Title for documentation
        description: Description for documentation
        example: Example value
        deprecated: Mark as deprecated
        include_in_schema: Include in OpenAPI schema
    """
    return Param(
        default=default,
        alias=alias,
        title=title,
        description=description,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        min_length=min_length,
        max_length=max_length,
        example=example,
        examples=examples,
        deprecated=deprecated,
        include_in_schema=include_in_schema,
        param_type=ParamType.FILE,
        **extra,
    )


# Re-export for convenience
__all__ = [
    "Param",
    "ParamType",
    "Path",
    "Query",
    "Header",
    "Cookie",
    "Body",
    "Form",
    "File",
]
