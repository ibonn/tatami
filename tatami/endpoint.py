import inspect
import logging
from types import MethodType
from typing import (TYPE_CHECKING, Awaitable, Callable, Optional, Self, Type,
                    TypeAlias, TypeVar, Union, overload)

from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from tatami._utils import (_human_friendly_description_from_name,
                           get_request_type, wrap_response)

if TYPE_CHECKING:
    from tatami.router import Router

Tag: TypeAlias = Union[str, dict[str, str]]
F = TypeVar("F", bound=Callable)

logger = logging.getLogger('tatami.endpoint')

class Endpoint:
    """
    Represents an endpoint within the framework.

    This is an internal class and is not intended for general use. It should only be used when implementing advanced functionality or extending the framework.

    The class stores metadata associated with endpoints. It is also callable and can be used as a decorator. Invoking the `run()` method executes the endpoint's logic.
    """
    def __init__(self, method: str, path: str, request_type: Optional[BaseModel] = None, response_type: Optional[Type[Response]] = None, summary: Optional[str] = None, description: Optional[str] = None, tags: Optional[list[Tag]] = None):
        self.method = method.upper()
        self.path = path
        self.request_type = request_type
        self.response_type = response_type
        self.summary = summary
        self.description = description
        self.tags = tags or []
        self.ep_fn: Callable = None

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return MethodType(self.ep_fn, instance)

    def get_openapi_spec(self, parent_router: 'Router') -> dict:
        """
        Generate the OpenAPI specification fragment for this endpoint.

        This method inspects the endpoint function signature to determine:
        - Path parameters (parameters present in the URL path)
        - Request body schema (Pydantic models used as non-path parameters)

        It constructs the OpenAPI operation object with summary, description,
        parameters, tags, deprecated flag, and default 200 response.

        Args:
            parent_router (Router): The router instance that contains this endpoint,
                used to build the full path and tags.

        Returns:
            dict: A dictionary representing the OpenAPI path and method specification
            for this endpoint.

        Usage example:
        
        .. code-block:: python

            # Assume `endpoint` is an instance of the endpoint class and `router` is the parent router
            openapi_fragment = endpoint.get_openapi_spec(router)
            print(openapi_fragment)
            # Output example:
            # {
            #   "/users/{user_id}": {
            #       "get": {
            #           "summary": "Get user by ID",
            #           "description": "Retrieve a user by their unique identifier.",
            #           "parameters": [
            #               {
            #                   "name": "user_id",
            #                   "in": "path",
            #                   "required": True,
            #                   "schema": {"type": "string"}
            #               }
            #           ],
            #           "tags": ["UserRouter"],
            #           "deprecated": False,
            #           "responses": {
            #               "200": {
            #                   "description": "Successful response"
            #               }
            #           }
            #       }
            #   }
            # }
        """
        sig = inspect.signature(self.ep_fn)
        parameters = []
        request_body = None

        for name, param in sig.parameters.items():
            if name == 'self':
                continue
            annotation = param.annotation
            # Check if it's a path param
            if f"{{{name}}}" in self.path:
                parameters.append({
                    'name': name,
                    'in': 'path',
                    'required': True,
                    'schema': {
                        'type': 'string' if annotation == str else 'integer'
                    }
                })
            else:
                # Treat as body (Pydantic model)
                if inspect.isclass(annotation) and hasattr(annotation, 'schema'):
                    request_body = {
                        'content': {
                            'application/json': {
                                'schema': annotation.model_json_schema()
                            }
                        }
                    }

        op = {
            'summary': self.summary or _human_friendly_description_from_name(self.ep_fn.__name__),
            'description': self.description or self.ep_fn.__doc__ or _human_friendly_description_from_name(self.ep_fn.__name__),
            'parameters': parameters,
            'tags': self.tags or [parent_router.__class__.__name__],
            'deprecated': hasattr(self.ep_fn, '__deprecated__'),
            'responses': {
                '200': {
                    'description': 'Successful response'
                }
            }
        }

        if request_body:
            op['requestBody'] = request_body

        return {
            parent_router.path + self.path: {
                self.method.lower(): op
            }
        }
    
    async def run(self, request: Request) -> Union[Response, Awaitable[Response]]:
        """
        Handle an incoming HTTP request by extracting path parameters and request body,
        invoking the endpoint function, and returning an appropriate response.

        The method:
        - Extracts path parameters from the request URL.
        - For POST, PUT, or PATCH methods, attempts to parse the JSON body and
        instantiate Pydantic models defined in `self.request_type`.
        - Calls the endpoint function (`self.ep_fn`) with the app instance and
        all extracted parameters.
        - Awaits the result if it is awaitable.
        - Wraps the result in a response using `self.response_type` if defined,
        otherwise uses a default wrapper.

        Args:
            request (Request): The incoming HTTP request object.

        Returns:
            Union[Response, Awaitable[Response]]: A Starlette Response instance,
            either directly returned or awaited.

        Usage example:
        
        .. code-block:: python

            # Assume `endpoint` is an instance with `run` method,
            # and `request` is a Starlette Request object.

            response = await endpoint.run(request)
            # `response` is a Starlette Response object ready to be sent back to the client.
        """
        kwargs = dict(request.path_params)
        if request.method in ('POST', 'PUT', 'PATCH'):
            try:
                body = await request.json()
                if self.request_type is not None:
                    for param_name, model in self.request_type.items():
                        kwargs.update({param_name: model(**body)})
                
            except Exception:
                pass  # skip if body is not present
        result = self.ep_fn(request.app, **kwargs)
        if inspect.isawaitable(result):
            result = await result

        if self.response_type is None:
            return wrap_response(self.ep_fn, result)
        
        return self.response_type(result)

    def build_route(self, base_path: str) -> Route:
        path = base_path + self.path
        logger.debug('Building route: %s %s', self.method, path)
        return Route(
            path=self.path,
            endpoint=self.run,
            methods=[self.method]
        )

    def __call__(self, ep_fn: Callable) -> Self:
        self.ep_fn = ep_fn
        self.request_type = self.request_type or get_request_type(ep_fn)
        return self

    def __repr__(self) -> str:
        return f'<Endpoint for {self.path} ({self.method}) @ {hex(id(self))}>'


# Universal request helper
@overload
def request(method: str, func: F) -> F: ...
@overload
def request(method: str, path: str, *, response_type: Optional[str] = None) -> Callable[[F], F]: ...
@overload
def request(method: str, *, response_type: Optional[str] = None) -> Callable[[F], F]: ...

def request(method: str, path_or_func: Optional[Union[str, Callable]] = None, *, response_type: Optional[Type[Response]] = None) -> Endpoint:
    """
    Convenience factory function to create an `Endpoint` instance with the given HTTP method and path.
    Meant to be used as a decorator.

    Args:
        method (str): The HTTP method for the endpoint (e.g., 'GET', 'POST', 'PUT', etc.).
        path (str): The URL path pattern for the endpoint (e.g., '/users/{user_id}').
        response_type (Optional[Type[Response]]): Optional Starlette Response subclass to use for responses.

    Returns:
        Endpoint: An instance of `Endpoint` initialized with the specified method, path, and response type.

    Usage example:
    
    .. code-block:: python

        @request('GET', '/users/{user_id}', response_type=JSONResponse)
        def get_user_by_id(self, user_id):
            ...
    """
    decorator = Endpoint(method, path_or_func if isinstance(path_or_func, str) else '/', response_type=response_type)
    if callable(path_or_func):
        return decorator(path_or_func)
    return decorator



# Convenience decorators for all HTTP verbs

# GET
@overload
def get(func: F) -> F: ...
@overload
def get(path: str, *, response_type: Optional[str] = None) -> Callable[[F], F]: ...
@overload
def get(*, response_type: Optional[str] = None) -> Callable[[F], F]: ...
def get(path_or_func: Union[str, Callable, None] = None, **kwargs):
    return request("GET", path_or_func, **kwargs)

# POST
@overload
def post(func: F) -> F: ...
@overload
def post(path: str, *, response_type: Optional[str] = None) -> Callable[[F], F]: ...
@overload
def post(*, response_type: Optional[str] = None) -> Callable[[F], F]: ...
def post(path_or_func=None, **kwargs):
    return request("POST", path_or_func, **kwargs)

# PUT
@overload
def put(func: F) -> F: ...
@overload
def put(path: str, *, response_type: Optional[str] = None) -> Callable[[F], F]: ...
@overload
def put(*, response_type: Optional[str] = None) -> Callable[[F], F]: ...
def put(path_or_func=None, **kwargs):
    return request("PUT", path_or_func, **kwargs)

# PATCH
@overload
def patch(func: F) -> F: ...
@overload
def patch(path: str, *, response_type: Optional[str] = None) -> Callable[[F], F]: ...
@overload
def patch(*, response_type: Optional[str] = None) -> Callable[[F], F]: ...
def patch(path_or_func=None, **kwargs):
    return request("PATCH", path_or_func, **kwargs)

# DELETE
@overload
def delete(func: F) -> F: ...
@overload
def delete(path: str, *, response_type: Optional[str] = None) -> Callable[[F], F]: ...
@overload
def delete(*, response_type: Optional[str] = None) -> Callable[[F], F]: ...
def delete(path_or_func=None, **kwargs):
    return request("DELETE", path_or_func, **kwargs)

# HEAD
@overload
def head(func: F) -> F: ...
@overload
def head(path: str, *, response_type: Optional[str] = None) -> Callable[[F], F]: ...
@overload
def head(*, response_type: Optional[str] = None) -> Callable[[F], F]: ...
def head(path_or_func=None, **kwargs):
    return request("HEAD", path_or_func, **kwargs)

# OPTIONS
@overload
def options(func: F) -> F: ...
@overload
def options(path: str, *, response_type: Optional[str] = None) -> Callable[[F], F]: ...
@overload
def options(*, response_type: Optional[str] = None) -> Callable[[F], F]: ...
def options(path_or_func=None, **kwargs):
    return request("OPTIONS", path_or_func, **kwargs)
