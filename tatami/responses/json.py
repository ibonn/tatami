import datetime
import decimal
import json
from dataclasses import asdict, is_dataclass
from typing import Any, Mapping, Optional
from uuid import UUID

from pydantic import BaseModel
from pydantic_core import PydanticUndefinedType
from starlette.background import BackgroundTask
from starlette.responses import Response


def serialize_json(x: Any, _visited: set = None) -> Any:
    if _visited is None:
        _visited = set()
    
    # Check for circular references
    obj_id = id(x)
    if obj_id in _visited:
        return None  # JSON-compatible way to handle circular references
    
    # For primitive types, return as-is without adding to visited
    if x is None or isinstance(x, (str, int, float, bool)):
        return x
    
    # Add to visited set for complex objects
    _visited.add(obj_id)
    
    try:
        if isinstance(x, BaseModel):
            return x.model_dump()
        
        if isinstance(x, (list, tuple, set)):
            return [serialize_json(y, _visited) for y in x]
        
        if isinstance(x, Mapping):
            return {a: serialize_json(b, _visited) for a, b in x.items()}
        
        if isinstance(x, UUID):
            return str(x)
        
        if isinstance(x, decimal.Decimal):
            return float(x)
        
        if is_dataclass(x):
            return serialize_json(asdict(x), _visited)
        
        if isinstance(x, (datetime.datetime, datetime.date, datetime.time)):
            return x.isoformat()
        
        # Special handling for Pydantic model classes
        if isinstance(x, type) and issubclass(x, BaseModel):
            return x.model_json_schema()
        
        if hasattr(x, '__slots__'):
            return {slot: serialize_json(getattr(x, slot), _visited) for slot in x.__slots__ if hasattr(x, slot)}
        
        if hasattr(x, '__dict__'):
            return serialize_json(vars(x), _visited)
        
        if isinstance(x, PydanticUndefinedType):
            return None
        
        return x
    finally:
        # Remove from visited set when done processing
        _visited.discard(obj_id)


class JSONResponse(Response):
    def __init__(self, content: Any, status_code: int = 200, headers: Optional[Mapping[str, str]] = None, media_type: Optional[str] = None, background: Optional[BackgroundTask] = None):
        headers = headers or {}
        headers['content-type'] = 'application/json'
        serialized = serialize_json(content)
        json_encoded = json.dumps(serialized)
        super().__init__(json_encoded, status_code, headers, media_type, background)