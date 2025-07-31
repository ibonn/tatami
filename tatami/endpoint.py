import inspect
import logging
from functools import wraps
from typing import (TYPE_CHECKING, Annotated, Any, Awaitable, Callable,
                    Literal, Optional, Type, TypeAlias, TypeVar, Union,
                    get_args, get_origin, overload)

from pydantic import BaseModel
from starlette.requests import Request
from starlette.routing import Route

from tatami._utils import (human_friendly_description_from_name,
                           serialize_json, wrap_response)
from tatami.core import TatamiObject
from tatami.di import (__TATAMI_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED,
                       Inject, Scope, is_injectable, is_tatami_object)
from tatami.param import Header, Path, Query
from tatami.responses import JSONResponse, Response
from tatami.validation import (ValidationException,
                               create_multiple_validation_errors_response,
                               create_validation_error_response,
                               validate_parameter)

Tag: TypeAlias = Union[str, dict[str, str]]
HTTPMethod: TypeAlias = Literal['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
F = TypeVar("F", bound=Callable)

logger = logging.getLogger('tatami.endpoint')


def _format_header_name(name: str) -> str:
    """Convert parameter name to HTTP header format (replace _ with -, title case)."""
    return name.replace('_', '-').title()


def _convert_and_validate_parameter(value: str, target_type, field_name: str) -> any:
    """
    Convert and validate string parameter value to target type using the validation system.
    
    Args:
        value: The string value from the request
        target_type: The target type to convert to
        field_name: Name of the field for error reporting
        
    Returns:
        The validated and converted value
        
    Raises:
        ValidationException: If validation fails
    """
    return validate_parameter(value, target_type, field_name)


def _extract_param_info(param_name: str, annotation, path: str) -> tuple[str, str, any]:
    """
    Extract parameter information from type annotation.
    
    Returns:
        tuple: (param_type, param_name, actual_type)
        where param_type is one of 'headers', 'query', 'path', 'body'
    """
    # Check if it's an Annotated type
    if get_origin(annotation) is Annotated:
        args = get_args(annotation)
        if len(args) >= 2:
            actual_type = args[0]
            metadata = args[1:]
            
            # Look for Header, Query, or Path in metadata
            for meta in metadata:
                if isinstance(meta, Header):
                    header_name = meta.name if meta.name is not None else _format_header_name(param_name)
                    return 'headers', header_name, actual_type
                elif isinstance(meta, Query):
                    query_name = meta.name if meta.name is not None else param_name
                    return 'query', query_name, actual_type
                elif isinstance(meta, Path):
                    path_name = meta.name if meta.name is not None else param_name
                    return 'path', path_name, actual_type
                elif isinstance(meta, Inject):
                    return 'injected', param_name, annotation
    
    # Check if it's a BaseModel (body parameter)
    try:
        if inspect.isclass(annotation) and issubclass(annotation, BaseModel):
            return 'body', param_name, annotation
    except TypeError:
        pass

    # Same for requests
    try:
        if inspect.isclass(annotation) and issubclass(annotation, Request):
            return 'injected', param_name, annotation
    except TypeError:
        pass

    # and more injectable objects
    if is_injectable(annotation):
        return 'injected', param_name, annotation
    
    # For unannotated parameters, infer based on path presence
    # If parameter name exists in path, it's a path parameter
    if f'{{{param_name}}}' in path:
        param_type = annotation if annotation != inspect.Parameter.empty else str
        return 'path', param_name, param_type
    else:
        # Otherwise, it's a query parameter
        param_type = annotation if annotation != inspect.Parameter.empty else str
        return 'query', param_name, param_type
    raise ValueError(f"Parameter '{param_name}' must be explicitly annotated with Query(), Header(), Path(), or be a BaseModel")


def _extract_parameters(func: Callable, path: str) -> dict:
    """
    Extract parameter information from function signature.
    
    Path and Query parameters can be inferred automatically:
    - If parameter name exists in path (e.g., {user_id}), it's a path parameter
    - Otherwise, it's a query parameter
    - Headers and body parameters must be explicitly annotated
    
    Returns:
        dict: Contains 'headers', 'query', 'path', and 'body' parameter mappings
        Each mapping contains param_name -> {'key': str, 'type': type}
    """
    sig = inspect.signature(func)
    params = {
        'headers': {},  # param_name -> {'key': header_name, 'type': type}
        'query': {},    # param_name -> {'key': query_name, 'type': type}  
        'path': {},     # param_name -> {'key': path_name, 'type': type}
        'body': {},     # param_name -> model_class
        'injected': {}, # param_name -> injected_object
    }
    
    for param_name, param in sig.parameters.items():
        # Skip 'self' parameter
        if param_name == 'self':
            continue
            
        annotation = param.annotation
        
        # Handle both annotated and unannotated parameters
        param_type, param_key, actual_type = _extract_param_info(param_name, annotation, path)
        
        if param_type == 'body':
            params['body'][param_name] = actual_type
        elif param_type == 'injected':
            params['injected'][param_name] = actual_type
        else:
            params[param_type][param_name] = {'key': param_key, 'type': actual_type}
    
    return params

async def _resolve_parameters(func: Callable, request: Request, path: Optional[str] = None):
    params_config = _extract_parameters(func, path)
    kwargs = {}
    validation_errors = []

    for param_name, param_type in params_config['injected'].items():
        if isinstance(param_type, type) and issubclass(param_type, Request):
            kwargs[param_name] = request
        
        elif get_origin(param_type) is Annotated:
            actual_type, inject_object = get_args(param_type)
            
            if inject_object.factory is None:
                if is_injectable(actual_type):
                    metadata = getattr(actual_type, __TATAMI_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED)
                    if metadata.scope == Scope.SINGLETON:
                        if metadata.singleton is None:
                            metadata.singleton = actual_type()
                        instance = metadata.singleton
                    else:
                        instance = actual_type()
                else:
                    raise TypeError(f'Cannot inject object of type {inject_object}')
            else:
                factory_kwargs, factory_validation_errors = await _resolve_parameters(inject_object.factory, request)
                if inject_object.metadata.scope == Scope.SINGLETON:
                    if inject_object.metadata.singleton is None:
                        inject_object.metadata.singleton = instance = inject_object.factory(**factory_kwargs)
                    instance = inject_object.metadata.singleton
                else:
                    instance = inject_object.factory(**factory_kwargs)
                
                validation_errors.extend(factory_validation_errors)

            kwargs[param_name] = instance

    # Extract and validate path parameters
    for param_name, param_info in params_config['path'].items():
        param_key = param_info['key']
        param_type = param_info['type']
        if param_key in request.path_params:
            raw_value = request.path_params[param_key]
            try:
                kwargs[param_name] = _convert_and_validate_parameter(raw_value, param_type, param_name)
            except ValidationException as e:
                validation_errors.append(e)
    
    # Extract and validate query parameters
    for param_name, param_info in params_config['query'].items():
        param_key = param_info['key']
        param_type = param_info['type']
        if param_key in request.query_params:
            raw_value = request.query_params[param_key]
            try:
                kwargs[param_name] = _convert_and_validate_parameter(raw_value, param_type, param_name)
            except ValidationException as e:
                validation_errors.append(e)
    
    # Extract and validate header parameters
    for param_name, param_info in params_config['headers'].items():
        param_key = param_info['key']
        param_type = param_info['type']
        if param_key.lower() in request.headers:
            raw_value = request.headers[param_key.lower()]
            try:
                kwargs[param_name] = _convert_and_validate_parameter(raw_value, param_type, param_name)
            except ValidationException as e:
                validation_errors.append(e)
        else:
            # TODO raise a bad request error (400), the header is missing. We will set it to None for now
            kwargs[param_name] = None
    
    # Extract and validate body parameters for POST, PUT, PATCH requests
    if request.method in ('POST', 'PUT', 'PATCH') and params_config['body']:
        try:
            body = await request.json()
            for param_name, model_class in params_config['body'].items():
                try:
                    kwargs[param_name] = validate_parameter(body, model_class, param_name)
                except ValidationException as e:
                    validation_errors.append(e)
        except Exception as e:
            # Failed to parse JSON body
            validation_errors.append(ValidationException(
                "request_body", 
                "invalid_json", 
                dict, 
                f"Failed to parse JSON body: {str(e)}"
            ))

    return kwargs, validation_errors

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
    
    @property
    def deprecated(self) -> bool:
        return hasattr(self.func, '__deprecated__')


class BoundEndpoint(TatamiObject):
    def __init__(self, endpoint: Endpoint, instance):
        self._endpoint = endpoint
        self._instance = instance
        self.method: str = endpoint.method
        self.path: str = endpoint.path
        self.include_in_schema = True

    @property
    def tags(self) -> list[str]:
        return self._endpoint.tags
    
    @property
    def summary(self) -> str:
        return human_friendly_description_from_name(self._endpoint.func.__name__)
    
    @property
    def docs(self) -> str:
        return self._endpoint.func.__doc__
    
    @property
    def signature(self) -> inspect.Signature:
        return inspect.signature(self._endpoint.func)
    
    @property
    def request_type(self) -> Union[Request, BaseModel, None]:
        return self._endpoint.request_type
    
    @property
    def response_type(self) -> Union[Type[Response], Type[BaseModel], None]:
        return self._endpoint.response_type
    
    @property
    def deprecated(self) -> bool:
        return self._endpoint.deprecated

    @property
    def endpoint_function(self):
        async def _ep_fn(*args, **kwargs):
            return await self.run(*args, **kwargs)
        return wraps(self._endpoint.func)(_ep_fn)

    async def run(self, request: Request) -> Union[Response, Awaitable[Response]]:
        """
        Handle an incoming HTTP request by extracting path parameters, query parameters,
        headers, and request body based on function annotations, invoking the endpoint 
        function, and returning an appropriate response.

        The method:
        - Extracts path parameters from the request URL.
        - Extracts query parameters from the request query string.
        - Extracts headers from the request headers.
        - For POST, PUT, or PATCH methods, attempts to parse the JSON body and
        instantiate Pydantic models defined in function annotations.
        - Validates all parameters against their type annotations.
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
        # Extract parameter configuration from function signature
        kwargs, validation_errors = await _resolve_parameters(self._endpoint.func, request, self.path)
        
        # Return validation errors if any occurred
        if validation_errors:
            if len(validation_errors) == 1:
                return create_validation_error_response(validation_errors[0])
            else:
                return create_multiple_validation_errors_response(validation_errors)
        
        # Call the endpoint function
        result = self(**kwargs)
        if inspect.isawaitable(result):
            result = await result

        if self._endpoint.response_type is None:
            return wrap_response(self._endpoint.func, result)
        
        return self._endpoint.response_type(result)

    def __call__(self, *args, **kwargs):
        if inspect.ismethod(self._endpoint.func):
            return self._endpoint.func(*args, **kwargs)
        else:
            return self._endpoint.func(self._instance, *args, **kwargs)
    
    def get_route(self) -> Route:
        return Route(self.path, self.run, name=self._endpoint.func.__name__, methods=[self.method])

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
        return wraps(fn)(Endpoint(method, fn, path_or_func if isinstance(path_or_func, str) else '', None, response_type))

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
