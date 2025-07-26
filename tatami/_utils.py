import datetime
import decimal
import importlib.util
import inspect
import os
import re
from dataclasses import asdict, is_dataclass
from io import IOBase
from types import ModuleType
from typing import Any, Callable, Mapping, MutableSequence, Type
from uuid import UUID

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel
from starlette.responses import (HTMLResponse, JSONResponse, Response,
                                 StreamingResponse)


class TemplateResponse(HTMLResponse):
    def __init__(self, template_name: str, content = None, status_code = 200, headers = None, media_type = None, background = None):
        environment = Environment(loader=FileSystemLoader('templates'))
        template = environment.get_template(template_name)
        super().__init__(template.render(content), status_code, headers, media_type, background)


def get_request_type(fn: Callable) -> dict[str, Type[BaseModel]]:
    models = {}
    annotations = inspect.get_annotations(fn)
    for name, cls in annotations.items():
        if issubclass(cls, BaseModel):
            models[name] = cls
    return models

def update_dict(d: dict, update_with: dict):
    for k, v in update_with.items():
        if k in d:
            if isinstance(d[k], Mapping) and isinstance(v, Mapping):
                update_dict(d[k], v)
            elif isinstance(d[k], MutableSequence) and isinstance(v, MutableSequence):
                d[k].extend(v)
            else:
                d[k] = v
        else:
            d[k] = v


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
        
        return x
    finally:
        # Remove from visited set when done processing
        _visited.discard(obj_id)

def human_friendly_description_from_name(name: str) -> str:
    return ' '.join(name.split('_')).capitalize()

def wrap_response(ep_fn: Callable, ep_result: Any) -> Response:
    try:
        if isinstance(ep_result, BaseModel):
            return JSONResponse(serialize_json(ep_result))
    except:
        pass
    
    for extension in ['jinja2', 'html', 'jinja']:
        template_path = os.path.join('templates', f'{ep_fn.__name__}.{extension}')
        if os.path.isfile(template_path):
            return TemplateResponse(template_path, ep_result)
        
    try:
        if isinstance(ep_result, IOBase) and ep_result.readable():
            def file_iterator():
                with ep_result as f:
                    yield from f
            return StreamingResponse(file_iterator())
    except:
        pass

    return JSONResponse(serialize_json(ep_result))

def path_to_module(path: str) -> str:
    fn, _ = os.path.splitext(path)
    return fn.replace('/', '.').replace('\\', '.')

def import_from_path(path: str) -> ModuleType:
    module_name = path_to_module(path)
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def camel_to_snake(name: str) -> str:
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()

def is_path_param(t: Type) -> bool:
    if t in {int, str}:
        return True
    return False

def with_new_base(cls: Type, new_base: Type) -> Type:
    attrs = dict(cls.__dict__)
    attrs['__dict__'] = new_base.__dict__   # Used to avoid this -> TypeError: descriptor '__dict__' for 'X' objects doesn't apply to a 'X' object
    return type(cls.__name__, (new_base,), attrs)
