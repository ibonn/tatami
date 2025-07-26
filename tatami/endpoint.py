import inspect
import logging
from functools import wraps
from typing import (TYPE_CHECKING, Awaitable, Callable, Literal, Optional,
                    Type, TypeAlias, TypeVar, Union, overload)

from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from tatami._utils import wrap_response
from tatami.core import TatamiObject

if TYPE_CHECKING:
    from tatami.router import Router

Tag: TypeAlias = Union[str, dict[str, str]]
HTTPMethod: TypeAlias = Literal['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
F = TypeVar("F", bound=Callable)

logger = logging.getLogger('tatami.endpoint')


class Endpoint(TatamiObject):
    def __init__(self, method: str, func: Callable, path: str = None, request_type: Optional[Union[Type[Request], Type[BaseModel]]] = None, response_type: Optional[Type[Response]] = None, tags: Optional[list[str]] = None):
        self.func = func
        self.method = method
        self.path = '/' if path is None or path == '' else path
        self.request_type = request_type
        self.response_type = response_type or JSONResponse
        self.tags = tags or []
        self.__name__ = getattr(func, "__name__", None)
        self.__doc__ = getattr(func, "__doc__", None)

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return BoundEndpoint(self, instance)


class BoundEndpoint(TatamiObject):
    def __init__(self, routed_method: Endpoint, instance):
        self._routed_method = routed_method
        self._instance = instance
        self.method: str = routed_method.method
        self.path: str = routed_method.path
        self.include_in_schema = True

    @property
    def endpoint_function(self):
        async def _ep_fn(*args, **kwargs):
            return await self.run(*args, **kwargs)
        return wraps(self._routed_method.func)(_ep_fn)

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
                if self._routed_method.request_type is not None:
                    for param_name, model in self._routed_method.request_type.items():
                        kwargs.update({param_name: model(**body)})
                
            except Exception:
                pass  # skip if body is not present
        result = self(**kwargs)
        if inspect.isawaitable(result):
            result = await result

        if self._routed_method.response_type is None:
            return wrap_response(self._routed_method.func, result)
        
        return self._routed_method.response_type(result)

    def __call__(self, *args, **kwargs):
        return self._routed_method.func(self._instance, *args, **kwargs)
    
    def get_route(self) -> Route:
        return Route(self.path, self.run, name=self._routed_method.func.__name__, methods=[self.method])

# Universal request helper
@overload
def request(method: HTTPMethod, func: F) -> F: ...
@overload
def request(method: HTTPMethod, path: str, *, response_type: Optional[Type[Response]] = None) -> Callable[[F], F]: ...
@overload
def request(method: HTTPMethod, *, response_type: Optional[Type[Response]] = None) -> Callable[[F], F]: ...

def request(method: HTTPMethod, path_or_func: Optional[Union[str, Callable]] = None, *, response_type: Optional[Type[Response]] = None) -> Endpoint:
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
    def decorator(fn):
        return wraps(fn)(Endpoint(method, fn, path_or_func if isinstance(path_or_func, str) else '', response_type))

    if callable(path_or_func):
        return decorator(path_or_func)
    return decorator


# Convenience decorators for all HTTP verbs
# GET
@overload
def get(func: F) -> F:
    """
    Marks a function as a GET endpoint using the parent router's path.

    This is a shorthand for declaring a GET route without specifying an additional path.
    The endpoint will be mounted at the path defined by the class or router it belongs to.

    Example:
        @get
        def index(): ...

    Args:
        func: The endpoint function to register.

    Returns:
        The same function, unmodified.
    """
@overload
def get(path: str, *, response_type: Optional[Type[Response]] = None) -> Callable[[F], F]:
    """
    Marks a function as a GET endpoint at a given subpath of the parent router.

    The full path will be composed by joining the parent router's path with the provided one.

    Example:
        @get("/items")
        def list_items(): ...

    Args:
        path: Subpath relative to the parent router (must start with '/').
        response_type: Optional response format hint (e.g., "json", "html").

    Returns:
        A decorator that registers the function as a GET endpoint.
    """
@overload
def get(*, response_type: Optional[Type[Response]] = None) -> Callable[[F], F]:
    """
    Marks a function as a GET endpoint at the parent router's path,
    while allowing an optional response type.

    Example:
        @get(response_type="json")
        def index(): ...

    Args:
        response_type: Optional response format hint (e.g., "json", "html").

    Returns:
        A decorator that registers the function as a GET endpoint.
    """
def get(path_or_func: Union[str, Callable, None] = None, **kwargs):
    """
    Registers a function as a GET endpoint. This decorator supports multiple forms:

    - `@get`: Registers the endpoint at the parent router's path.
    - `@get("/subpath")`: Registers the endpoint at a subpath relative to the parent router.
    - `@get(response_type="json")`: Registers at the parent path with a specified response type.
    - `@get("/subpath", response_type="json")`: Registers at a subpath with response type metadata.

    The full route is composed by joining the parent router's path with the provided subpath.

    Args:
        path_or_func: A subpath string (starting with '/') or the function to decorate.
                      If omitted, the endpoint is registered at the parent router’s path.
        **kwargs: Optional metadata such as `response_type`.

    Returns:
        Either the original function or a decorator that wraps it.
    """
    return request("GET", path_or_func, **kwargs)

# POST
@overload
def post(func: F) -> F: ...
@overload
def post(path: str, *, response_type: Optional[Type[Response]] = None) -> Callable[[F], F]: ...
@overload
def post(*, response_type: Optional[Type[Response]] = None) -> Callable[[F], F]: ...
def post(path_or_func=None, **kwargs):
    return request("POST", path_or_func, **kwargs)

# PUT
@overload
def put(func: F) -> F: ...
@overload
def put(path: str, *, response_type: Optional[Type[Response]] = None) -> Callable[[F], F]: ...
@overload
def put(*, response_type: Optional[Type[Response]] = None) -> Callable[[F], F]: ...
def put(path_or_func=None, **kwargs):
    return request("PUT", path_or_func, **kwargs)

# PATCH
@overload
def patch(func: F) -> F: ...
@overload
def patch(path: str, *, response_type: Optional[Type[Response]] = None) -> Callable[[F], F]: ...
@overload
def patch(*, response_type: Optional[Type[Response]] = None) -> Callable[[F], F]: ...
def patch(path_or_func=None, **kwargs):
    return request("PATCH", path_or_func, **kwargs)

# DELETE
@overload
def delete(func: F) -> F: ...
@overload
def delete(path: str, *, response_type: Optional[Type[Response]] = None) -> Callable[[F], F]: ...
@overload
def delete(*, response_type: Optional[Type[Response]] = None) -> Callable[[F], F]: ...
def delete(path_or_func=None, **kwargs):
    return request("DELETE", path_or_func, **kwargs)

# HEAD
@overload
def head(func: F) -> F: ...
@overload
def head(path: str, *, response_type: Optional[Type[Response]] = None) -> Callable[[F], F]: ...
@overload
def head(*, response_type: Optional[Type[Response]] = None) -> Callable[[F], F]: ...
def head(path_or_func=None, **kwargs):
    return request("HEAD", path_or_func, **kwargs)

# OPTIONS
@overload
def options(func: F) -> F: ...
@overload
def options(path: str, *, response_type: Optional[Type[Response]] = None) -> Callable[[F], F]: ...
@overload
def options(*, response_type: Optional[Type[Response]] = None) -> Callable[[F], F]: ...
def options(path_or_func=None, **kwargs):
    return request("OPTIONS", path_or_func, **kwargs)
