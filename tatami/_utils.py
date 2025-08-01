import importlib.util
import inspect
import os
import re
from io import IOBase
from types import ModuleType
from typing import TYPE_CHECKING, Any, Callable, Mapping, MutableSequence, Type

from pydantic import BaseModel
from starlette.responses import Response, StreamingResponse

from tatami.responses import JSONResponse, TemplateResponse

if TYPE_CHECKING:
    from tatami.endpoint import BoundEndpoint


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


def human_friendly_description_from_name(name: str) -> str:
    return ' '.join(name.split('_')).capitalize()

def wrap_response(ep_fn: Callable, ep_result: Any) -> Response:
    try:
        if isinstance(ep_result, BaseModel):
            return JSONResponse(ep_result)
    except:
        pass
    
    for extension in ['jinja2', 'jinja', 'html']:
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

    return JSONResponse(ep_result)

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

def with_new_base(cls: Type, new_base: Type) -> Type:
    # Filter out special attributes that shouldn't be copied
    attrs = {}
    for key, value in cls.__dict__.items():
        # Skip special attributes that can cause issues
        if key not in ('__dict__', '__weakref__', '__module__', '__qualname__'):
            attrs[key] = value
    
    # Create new class with filtered attributes
    return type(cls.__name__, (new_base,), attrs)

def route_priority(endpoint: 'BoundEndpoint') -> tuple[int, int, int, str, str]:
        path = endpoint.path
        # Get number of segments
        path_segments = [s for s in path.split('/') if s]
        
        # Count different types of segments
        static_segments = sum(1 for s in path_segments if not s.startswith('{'))
        param_segments = sum(1 for s in path_segments if s.startswith('{'))
        
        # Determine the priority (lower values = higher priority)
        return (
            -static_segments,    # More static segments -> higher priority
            param_segments,      # Fewer parameters -> higher priority  
            -len(path_segments), # More total segments -> higher priority 
            path,                # Alphabetical order for consistency
            endpoint.method,     # HTTP method for even more consistency (I currently see no difference, but it makes sense in my head)
        )