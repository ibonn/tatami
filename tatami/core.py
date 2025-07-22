import importlib
import inspect
import logging
import os
from types import MethodType
from typing import Awaitable, Callable, NoReturn, Optional, Self, Type, Union

import uvicorn
from pydantic import BaseModel
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route

from tatami._utils import (_human_friendly_description_from_name,
                           get_request_type, package_from_path, update_dict,
                           wrap_response)

logger = logging.getLogger('tatami.core')

def _none_if_dir_not_exists(path: str) -> Union[str, None]:
    return path if os.path.isdir(path) else None


def create_project(name: str, middleware_dir: str = 'middleware', routers_dir: str = 'routers', static_dir: str = 'static', templates_dir: str = 'templates', services_dir: str = 'services', tests_dir: str = 'tests') -> None:
    middleware_path = os.path.join(name, middleware_dir)
    routers_path = os.path.join(name, routers_dir)
    static_path = os.path.join(name, static_dir)
    templates_path = os.path.join(name, templates_dir)
    services_path = os.path.join(name, services_dir)
    tests_path = os.path.join(name, tests_dir)
    config_path = os.path.join(name, 'config.yaml')


    # Create the folders
    os.makedirs(middleware_path)
    os.makedirs(routers_path)
    os.makedirs(static_path)
    os.makedirs(templates_path)
    os.makedirs(services_path)
    os.makedirs(tests_path)

    # Create the config file
    open(config_path, 'w', encoding='utf-8').close()


class Router(Starlette):
    """Base class for routers. In general, you should use the :func:`~tatami.core.router` class factory to
    declare your routers
    """
    path: str

    def __init__(self, title: Optional[str] = None, description: Optional[str] = None, version: Optional[str] = None, debug = False, routes = None, middleware = None, exception_handlers = None, on_startup = None, on_shutdown = None, lifespan = None):
        super().__init__(debug, routes, middleware, exception_handlers, on_startup, on_shutdown, lifespan)
        self.title = title or 'Tatami'
        self.description = description
        self.version = version

    def _get_doc(self):
        if self.__doc__ == Router.__doc__:
            return None
        return self.__doc__

    def _get_base_openapi_spec(self) -> dict:
        return {
            'openapi': '3.0.0',
            'info': {
                'title': self.title or self.__class__.__name__,
                'version': self.version,
                'description': self.description or self._get_doc() or f'API for {self.__class__.__name__}',
            },
            'paths': {},
            'tags': [],
        }

    def get_openapi_spec(self) -> dict:
        """
        Generate the complete OpenAPI specification dictionary by aggregating
        the base specification with the OpenAPI specs from all registered endpoints.

        This method is usually called internally to generate the OpenAPI specification.

        This method calls a private method `_get_base_openapi_spec` to retrieve the
        base OpenAPI spec, then updates the `paths` section of the spec with
        endpoint-specific specifications.

        Returns:
            dict: A dictionary representing the full OpenAPI specification.

        Usage example:

        .. code-block:: python

            # Assume `router` is a Router instance
            openapi_spec = router.get_openapi_spec()
            print(openapi_spec['paths'])  # Outputs the combined paths of all endpoints
        
        """
        spec = self._get_base_openapi_spec()
        for ep in self.endpoints:
            update_dict(spec['paths'], ep.get_openapi_spec(self))
        return spec


    @property
    def endpoints(self) -> list['Endpoint']:
        eps = []
        for attr in dir(self):
            val = getattr(self.__class__, attr, None)
            if isinstance(val, Endpoint):
                eps.append(val)
        return eps

Tag = Union[str, dict[str, str]]

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

    def get_openapi_spec(self, parent_router: Router) -> dict:
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

    def __call__(self, ep_fn: Callable) -> 'Endpoint':
        self.ep_fn = ep_fn

        self.request_type = self.request_type or get_request_type(ep_fn)

        self._build_route = lambda base_path: Route(
            path=self.path,
            endpoint=self.run,
            methods=[self.method]
        )

        return self

    def __repr__(self) -> str:
        return f'<Endpoint for {self.path} ({self.method}) @ {hex(id(self))}>'

def router(p: str, title: Optional[str] = None, description: Optional[str] = None, version: Optional[str] = None) -> Type[Router]:
    """
    Factory function to create a Router subclass with a fixed base path and auto-discovered endpoints.

    This function defines and returns a subclass of `Router` with:
    - A fixed `path` attribute set to `p`.
    - An initializer that collects all `Endpoint` instances declared as class attributes,
      calls their `_build_route` method with the router path, and registers them as routes.
    - Optional metadata arguments (`title`, `description`, `version`) are accepted but currently unused.

    Args:
        p (str): The base path prefix for all routes registered under this router.
        title (Optional[str]): Optional router title metadata.
        description (Optional[str]): Optional router description metadata.
        version (Optional[str]): Optional router version metadata.

    Returns:
        Type[Router]: A subclass of `Router` customized with the specified base path and auto-registered endpoints.

    Usage example:
    
    .. code-block:: python

        # Define endpoints as class attributes inside the Router subclass
        class UserRouter(router('/users')):
            @get('/')
            def get_users(self):
                ...

            @get('/{user_id}')
            def get_user(self, id: int):
                ...

            @post('/')
            def create_user(self, user_data: dict):
                ...

        # Instantiate the router
        user_router = UserRouter()

        # The router now has routes for '/users/' (GET and POST), '/users/{user_id}', etc.
        print(user_router.routes)
    
    """
    class _Router(Router):
        path: str = p

        def __init__(self, *args, **kwargs):
            self._args = args
            self._kwargs = kwargs

            routes = []

            for attr in dir(self):
                val = getattr(self.__class__, attr, None)
                if isinstance(val, Endpoint) and hasattr(val, '_build_route'):
                    routes.append(val._build_route(self.path))

            super().__init__(title=title, description=description, version=version, routes=routes)

    return _Router


# Universal request helper
def request(method: str, path: str, response_type: Optional[Type[Response]] = None) -> Endpoint:
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
    return Endpoint(method, path, response_type=response_type)

# Convenience decorators for all HTTP verbs
def get(path: str, response_type: Optional[Type[Response]] = None) -> Callable:
    """
    Create an Endpoint for an HTTP GET request.

    Args:
        path (str): The URL path pattern for the GET endpoint.
        response_type (Optional[Type[Response]]): Optional Starlette Response subclass for the response.

    Returns:
        Callable: An Endpoint instance configured for GET requests.

    Usage example:
    
    .. code-block:: python

        @get('/items/{item_id}')
        def get_item(self, item_id: str):
            ...
    """
    return request('GET', path, response_type)
def post(path: str, response_type: Optional[Type[Response]] = None) -> Callable:
    """
    Create an Endpoint for an HTTP POST request.

    Args:
        path (str): The URL path pattern for the POST endpoint.
        response_type (Optional[Type[Response]]): Optional Starlette Response subclass for the response.

    Returns:
        Callable: An Endpoint instance configured for POST requests.

    Usage example:
    
    .. code-block:: python

        @post('/items/')
        def create_item(self):
            ...
    """
    return request('POST', path, response_type)
def put(path: str, response_type: Optional[Type[Response]] = None) -> Callable:
    """
    Create an Endpoint for an HTTP PUT request.

    Args:
        path (str): The URL path pattern for the PUT endpoint.
        response_type (Optional[Type[Response]]): Optional Starlette Response subclass for the response.

    Returns:
        Callable: An Endpoint instance configured for PUT requests.

    Usage example:
    
    .. code-block:: python

        @put('/items/{item_id}')
        def update_item(self, item_id: str, item: Item):
            ...
    """
    return request('PUT', path, response_type)
def patch(path: str, response_type: Optional[Type[Response]] = None) -> Callable:
    """
    Create an Endpoint for an HTTP PATCH request.

    Args:
        path (str): The URL path pattern for the PATCH endpoint.
        response_type (Optional[Type[Response]]): Optional Starlette Response subclass for the response.

    Returns:
        Callable: An Endpoint instance configured for PATCH requests.

    Usage example:
    
    .. code-block:: python

        @patch('/items/{item_id}')
        def update_item(self, item_id: str, item: Item):
            ...
    """
    return request('PATCH', path, response_type)
def delete(path: str, response_type: Optional[Type[Response]] = None) -> Callable:
    """
    Create an Endpoint for an HTTP DELETE request.

    Args:
        path (str): The URL path pattern for the DELETE endpoint.
        response_type (Optional[Type[Response]]): Optional Starlette Response subclass for the response.

    Returns:
        Callable: An Endpoint instance configured for DELETE requests.

    Usage example:
    
    .. code-block:: python

        @delete('/items/{item_id}')
        def delete_item(self, item_id: str):
            ...
    """
    return request('DELETE', path, response_type)
def head(path: str, response_type: Optional[Type[Response]] = None) -> Callable:
    """
    Create an Endpoint for an HTTP HEAD request.

    Args:
        path (str): The URL path pattern for the HEAD endpoint.
        response_type (Optional[Type[Response]]): Optional Starlette Response subclass for the response.

    Returns:
        Callable: An Endpoint instance configured for HEAD requests.

    Usage example:
    
    .. code-block:: python

        @put('/items/')
        def head_items(self):
            ...
    """
    return request('HEAD', path, response_type)
def options(path: str, response_type: Optional[Type[Response]] = None) -> Callable:
    """
    Create an Endpoint for an HTTP OPTIONS request.

    Args:
        path (str): The URL path pattern for the OPTIONS endpoint.
        response_type (Optional[Type[Response]]): Optional Starlette Response subclass for the response.

    Returns:
        Callable: An Endpoint instance configured for OPTIONS requests.

    Usage example:
    
    .. code-block:: python

        @options('/items/')
        def options_items(self):
            ...
    """
    return request('OPTIONS', path, response_type)

class Tatami(Router):
    """
    Main application class extending Router to provide additional features like
    OpenAPI spec aggregation and router inclusion.

    Args:
        title (Optional[str]): The API title.
        description (Optional[str]): The API description.
        version (Optional[str]): The API version.
        debug (bool): Enable debug mode.
        routes (Optional[List]): Initial routes to add.
        middleware (Optional[List]): Middleware to apply.
        exception_handlers (Optional[Dict]): Custom exception handlers.
        on_startup (Optional[Callable]): Callback for startup event.
        on_shutdown (Optional[Callable]): Callback for shutdown event.
        lifespan (Optional[Callable]): Lifespan context manager.

    Usage example:
    
    .. code-block:: python

        app = Tatami(title="My API", version="1.0")

        # Create a router and include it
        user_router = UserRouter()
        app.include_router(user_router)

        # Get combined OpenAPI spec
        spec = app.get_openapi_spec()
        print(spec)
    """
    def __init__(self, title: Optional[str] = None, description: Optional[str] = None, version: Optional[str] = None, debug = False, routes = None, middleware = None, exception_handlers = None, on_startup = None, on_shutdown = None, lifespan = None):
        super().__init__(title, description, version, debug, routes, middleware, exception_handlers, on_startup, on_shutdown, lifespan)

    def _get_doc(self):
        if self.__doc__ == Tatami.__doc__:
            return None
        return self.__doc__

    def include_router(self, router: Router) -> Self:
        """
        Mount another router instance under its configured path.

        Args:
            router (Router): A Router instance to include.

        Returns:
            Self: Returns self to allow chaining.

        Usage example:
        
        .. code-block:: python

            app.include_router(user_router)
        """
        self.mount(router.path, router)
        return self
    
    def get_openapi_spec(self):
        """
        Aggregate the OpenAPI specification from this app and all mounted routers.

        Returns:
            dict: The combined OpenAPI specification.

        Usage example:
        
        .. code-block:: python

            spec = app.get_openapi_spec()
            print(spec['paths'])
        """
        base = self._get_base_openapi_spec()

        for route in self.routes:
            if isinstance(route.app, Router):
                update_dict(base['paths'], route.app.get_openapi_spec()['paths'])
                base['tags'].append({
                    'name': route.app.__class__.__name__,
                    'description': route.app.__class__.__doc__ or ''
                })

        return base
    
    @classmethod
    def from_dir(cls, path: str, templates_dir_name: str = 'templates', static_dir_name: str = 'static', routes_dir_name: str = 'routes', middleware_dir_name: str = 'middleware', services_dir_name: str = 'services', config = None) -> 'Tatami':
        templates_dir = _none_if_dir_not_exists(os.path.join(path, templates_dir_name))
        static_dir = _none_if_dir_not_exists(os.path.join(path, static_dir_name))
        routes_dir = _none_if_dir_not_exists(os.path.join(path, routes_dir_name))
        middleware_dir = _none_if_dir_not_exists(os.path.join(path, middleware_dir_name))
        services_dir = _none_if_dir_not_exists(os.path.join(path, services_dir_name))

        instance = Tatami()

        if templates_dir is None:
            logger.debug('Templates dir not defined, skipping...')
            instance.templates_path = None
        else:
            logger.debug('Setting templates path to %s...', templates_dir)
            instance.templates_path = templates_dir

        if static_dir is None:
            logger.debug('Static dir not defined, skipping...')
        else:
            logger.debug('Building route for static files from %s...', static_dir)
            # TODO

        if services_dir is None:
            logger.debug('Services dir not defined, skipping...')
        else:
            logger.debug('Loading services from %s...', services_dir)

            for fn in os.listdir(services_dir):
                service_path = os.path.join(services_dir, fn)
                _, ext = os.path.splitext(service_path)
                if ext == '.py':
                    # TODO do something with this module?
                    service_module = importlib.import_module(package_from_path(service_path))

        if routes_dir is None:
            logger.debug('Routes dir not defined, skipping...')
        else:
            logger.debug('Loading routers from %s...', routes_dir)
            for fn in os.listdir(routes_dir):
                router_path = os.path.join(routes_dir, fn)
                _, ext = os.path.splitext(router_path)
                if ext == '.py':
                    router_module = importlib.import_module(package_from_path(router_path))
                    for elem_name in dir(router_module):
                        elem_value = getattr(router_module, elem_name)
                        if isinstance(elem_value, type) and issubclass(elem_value, Route):
                            logger.debug('Router found at "%s" (%s)', elem_name, router_path)

                            router_instance = elem_value()
                            instance.include_router(router_instance)

        if middleware_dir is None:
            logger.debug('Middleware dir not defined, skipping...')
        else:
            logger.debug('Loading middleware from %s...', middleware_dir)
            # TODO

        return instance

    

def run(app: Tatami, host: str = 'localhost', port: int = 8000, openapi_url: Optional[str] = '/openapi.json', swagger_url: Optional[str] = '/docs/swagger', redoc_url: Optional[str] = '/docs/redoc', rapidoc_url: Optional[str] = '/docs/rapidoc') -> NoReturn:
    """
    Run the Tatami application using Uvicorn, and optionally serve OpenAPI and documentation UIs.

    This function:
    - Sets the app root path to ''.
    - Adds routes to serve the OpenAPI JSON spec and interactive API docs (Swagger UI, ReDoc, RapiDoc)
      at the specified URLs.
    - Starts the Uvicorn server on the specified host and port.

    Args:
        app (Tatami): The Tatami application instance to run.
        host (str): Hostname to bind the server to. Defaults to 'localhost'.
        port (int): Port to bind the server to. Defaults to 8000.
        openapi_url (Optional[str]): URL path to serve OpenAPI JSON spec. Defaults to '/openapi.json'.
            Set to None to disable.
        swagger_url (Optional[str]): URL path to serve Swagger UI. Defaults to '/docs/swagger'.
            Set to None to disable.
        redoc_url (Optional[str]): URL path to serve ReDoc UI. Defaults to '/docs/redoc'.
            Set to None to disable.
        rapidoc_url (Optional[str]): URL path to serve RapiDoc UI. Defaults to '/docs/rapidoc'.
            Set to None to disable.

    Usage example:

    .. code-block:: python

        app = Tatami(title="My API")

        # Run the app with default docs URLs
        run(app, host="0.0.0.0", port=8080)

    Note:
        Requires `uvicorn` to be installed.
    """
    app.path = ''
    
    async def openapi_endpoint(request: Request):
        return JSONResponse(app.get_openapi_spec())

    async def redocs_endpoint(request: Request):
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{app.title} - ReDoc</title>
            <meta charset="utf-8"/>
        </head>
        <body>
            <redoc spec-url='{openapi_url}'></redoc>
            <script src="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"></script>
        </body>
        </html>
        """
        return HTMLResponse(html)

    async def swagger_endpoint(request: Request):
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{app.title} - Swagger UI</title>
            <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist/swagger-ui.css" />
            <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
            <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-standalone-preset.js"></script>
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script>
            SwaggerUIBundle({{
                url: '{openapi_url}',
                dom_id: '#swagger-ui',
                presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
                layout: "BaseLayout"
            }});
            </script>
        </body>
        </html>
        """
        return HTMLResponse(html)

    async def rapidoc_endpoint(request: Request):
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{app.title} - RapiDoc</title>
            <script type="module" src="https://unpkg.com/rapidoc/dist/rapidoc-min.js"></script>
        </head>
        <body>
            <rapi-doc spec-url="{openapi_url}" theme="dark" show-header="true" render-style="read"></rapi-doc>
        </body>
        </html>
        """
        return HTMLResponse(html)

    # Add the documentation routes to the root app
    if openapi_url is not None:
        app.routes.insert(0, Route(openapi_url, openapi_endpoint, methods=["GET"]))

        if redoc_url is not None:
            app.routes.insert(0, Route(redoc_url, redocs_endpoint, methods=["GET"]))
        
        if swagger_url is not None:
            app.routes.insert(0, Route(swagger_url, swagger_endpoint, methods=["GET"]))
        
        if rapidoc_url is not None:
            app.routes.insert(0, Route(rapidoc_url, rapidoc_endpoint, methods=["GET"]))

    uvicorn.run(app, host=host, port=port)
