"""
Custom response classes for VayuAPI
"""

import json
from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID
from typing import Any
from enum import Enum

from starlette.responses import JSONResponse as StarletteJSONResponse
from pydantic import BaseModel


class AgniJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles common Python types.

    Supports serialization of:
    - datetime, date, time objects (to ISO format strings)
    - Decimal (to float)
    - UUID (to string)
    - Enum (to value)
    - Pydantic BaseModel (to dict)
    """

    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, time):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, BaseModel):
            return obj.model_dump()
        return super().default(obj)


class JSONResponse(StarletteJSONResponse):
    """
    Custom JSONResponse that uses AgniJSONEncoder for proper serialization.

    This automatically handles datetime, UUID, Decimal, Enum, and other
    Python types that aren't natively JSON serializable.

    Example:
        ```python
        from vayuapi import JSONResponse
        from datetime import datetime

        @app.get("/now")
        async def get_time():
            return JSONResponse({
                "timestamp": datetime.now(),
                "message": "Current time"
            })
        ```
    """

    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            cls=AgniJSONEncoder,
        ).encode("utf-8")
