import inspect
import logging
import re
import warnings
from typing import Any, NoReturn, Optional, Self, Type

import uvicorn
from jinja2 import Environment
from pydantic import BaseModel, Field
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Route

from tatami._utils import camel_to_snake, route_priority
from tatami.core import TatamiObject
from tatami.endpoint import BoundEndpoint, Endpoint
from tatami.openapi import (create_docs_landing_page, create_openapi_endpoint,
                            create_rapidoc_endpoint, create_redoc_endpoint,
                            create_swagger_endpoint, generate_openapi_spec)
from tatami.param import Path

logger = logging.getLogger('tatami.router')

_INTENTIONS_MAPPING = {
    'get': 'GET',
    'post': 'POST',
    'put': 'PUT',
    'patch': 'PATCH',
    'head': 'HEAD',
    'delete': 'DELETE',
    'options': 'OPTIONS',
    'update': 'PUT',
    'create': 'POST',
    'new': 'POST',
    'remove': 'DELETE',
}

class Summary(BaseModel):
    config_file: Optional[str] = Field(description='Path to the config file', default=None)
    routers: int = Field(description='Number of found routers', default=0)
    middleware: int = Field(description='Number of found middleware', default=0)
    models: int = Field(description='Number of found Pydantic models', default=0)
    static: Optional[str] = Field(description='path to the static files', default=None)
    templates: Optional[str] = Field(description='path to the directory containing the templates', default=None)


class ProjectIntrospection(BaseModel):
    """Comprehensive introspection data for a Tatami project."""
    config_file: Optional[str] = Field(description='Path to the config file', default=None)
    
    # Routers
    routers: list[dict] = Field(description='Discovered router classes and instances', default_factory=list)
    
    # Services
    services: list[dict] = Field(description='Discovered services (injectable classes)', default_factory=list)

    # Models
    models: dict[str, type] = Field(description='Discovered Pydantic models', default_factory=dict)
    models_source: Optional[str] = Field(description='Source of models (directory or file path)', default=None)
    
    # Middleware
    middleware: list[dict] = Field(description='Discovered middleware classes', default_factory=list)
    
    # Static resources
    static_path: Optional[str] = Field(description='Path to static files directory', default=None)
    templates_path: Optional[str] = Field(description='Path to templates directory', default=None)
    favicon_path: Optional[str] = Field(description='Path to favicon file', default=None)
    
    # Mounts
    mounts: list[dict] = Field(description='Mounted sub-applications', default_factory=list)
    
    # Summary counts
    @property
    def router_count(self) -> int:
        return len(self.routers)
    
    @property
    def model_count(self) -> int:
        return len(self.models)
    
    @property
    def middleware_count(self) -> int:
        return len(self.middleware)
    
    @property
    def mount_count(self) -> int:
        return len(self.mounts)


class BaseRouter(TatamiObject):
    def __init__(self, title: Optional[str] = None, description: Optional[str] = None, summary: Optional[str] = None, version: str = '0.0.1', path: Optional[str] = None, tags: Optional[list[str]] = None):
        super().__init__()
        self.title = title
        self.description = description
        self.summary = summary
        self.version = version
        self.path = path or '/'
        self.tags = tags or []

        self._routers: list[BaseRouter] = []
        self._routes: list[Route] = []
        self._middleware: list[BaseHTTPMiddleware] = []
        self._mounts: dict[str, Any] = {}
        self.templates: Optional[Environment] = None

    def include_router(self, incl_router: 'BaseRouter') -> Self:
        logger.debug('Including router %s on %s', incl_router, self)
        self._routers.append(incl_router)
        return self
    
    def mount(self, path: str, app: Any) -> Self:
        logger.debug('Mounting %s on %s', app, self)
        self._mounts[path] = app
        return self
    
    def add_route(self, route: Route) -> Self:
        logger.debug('Adding route %s to %s', route, self)
        self._routes.append(route)
        return self
    
    def add_middleware(self, middleware) -> Self:
        self._middleware.append(middleware)
        return self
    
    @property
    def routers(self) -> list['BaseRouter']:
        return self._routers

    def _collect_endpoints(self) -> list[BoundEndpoint]:
        return []

    def _collect_all_routes(self) -> list[Route]:
        routes = []
        
        # Add routes from this router
        endpoints = self._collect_endpoints()
        for endpoint in endpoints:
            # Join router path with endpoint path
            full_path = self._combine_paths(self.path, endpoint.path)
            # Create route with full path
            route = Route(full_path, endpoint.run, name=endpoint.endpoint_function.__name__, methods=[endpoint.method])
            routes.append(route)
        
        # Add additional routes
        routes.extend(self._routes)
        
        # Recursively collect routes from sub-routers
        for sub_router in self._routers:
            sub_routes = sub_router._collect_all_routes()
            routes.extend(sub_routes)
        
        return routes
    
    def _combine_paths(self, router_path: str, endpoint_path: str) -> str:
        # Normalize router path
        router_path = router_path.rstrip('/') if router_path != '/' else ''
        
        # Handle endpoint path
        if endpoint_path == '':
            # For @request with no args, use router path without trailing slash
            return router_path if router_path else '/'
        elif endpoint_path == '/':
            # Explicit '/' path gets trailing slash
            return router_path + '/'
        else:
            # Normal operation
            return router_path + endpoint_path

    def _starlette(self) -> Starlette:
        logger.debug('Building starlette app...')
        
        # Collect all routes with full paths (no mounting)
        all_routes = self._collect_all_routes()
        
        logger.debug('%s routes found', len(all_routes))
        app = Starlette(
            routes=all_routes, middleware=[Middleware(m) for m in self._middleware]
        )

        # Handle mounts separately  
        logger.debug('Mounting apps...')
        for mount_path, mount_app in self._mounts.items():
            app.mount(mount_path, mount_app)

        return app
    
    def get_openapi_spec(self) -> dict:
        """Get the OpenAPI specification for this router."""
        return generate_openapi_spec(self)

        
    def run(self, host: str = 'localhost', port: int = 8000, openapi_url: Optional[str] = '/openapi.json', swagger_url: Optional[str] = '/docs/swagger', redoc_url: Optional[str] = '/docs/redoc', rapidoc_url: Optional[str] = '/docs/rapidoc', docs_landing_page: bool = True) -> NoReturn:
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
        app = self._starlette()
        
        # Create documentation endpoints using the new OpenAPI module
        openapi_endpoint = create_openapi_endpoint(self)
        redoc_endpoint = create_redoc_endpoint(self, openapi_url)
        swagger_endpoint = create_swagger_endpoint(self, openapi_url)
        rapidoc_endpoint = create_rapidoc_endpoint(self, openapi_url)

        # Add the documentation routes to the root app
        if openapi_url is not None:
            app.routes.insert(0, Route(openapi_url, openapi_endpoint, methods=["GET"]))

            # Collect enabled documentation endpoints
            enabled_docs = []
            if redoc_url is not None:
                app.routes.insert(0, Route(redoc_url, redoc_endpoint, methods=["GET"]))
                enabled_docs.append(("ReDoc", redoc_url))
            
            if swagger_url is not None:
                app.routes.insert(0, Route(swagger_url, swagger_endpoint, methods=["GET"]))
                enabled_docs.append(("Swagger UI", swagger_url))
            
            if rapidoc_url is not None:
                app.routes.insert(0, Route(rapidoc_url, rapidoc_endpoint, methods=["GET"]))
                enabled_docs.append(("RapiDoc", rapidoc_url))

            # Add landing page if requested and more than 1 documentation endpoint is enabled
            if docs_landing_page and len(enabled_docs) > 1:
                docs_landing_endpoint = create_docs_landing_page(self, enabled_docs)
                app.routes.insert(0, Route("/docs", docs_landing_endpoint, methods=["GET"]))

        uvicorn.run(app, host=host, port=port)

class ConventionRouter(BaseRouter):
    def __init__(self):
        warnings.warn('You are using convention-based routing, which is discouraged. Use explicit decorators (@get, @post, etc.) with the router() class factory for clearer, more reliable routing.')
        snake_case_name = camel_to_snake(self.__class__.__name__)
        super().__init__(path=f'/{snake_case_name}')

        # Enhanced regex to support more flexible naming conventions
        # Pattern: [verb_][descriptive_words_]router_name[s][_by_criteria]
        verbs = 'get|post|put|patch|head|delete|options|update|create|new|remove'
        self._regex = (
            rf'^(?:({verbs})_)?'  # Optional HTTP verb prefix with exact match
            r'(?:[a-zA-Z0-9_]+_)*'  # Zero or more descriptive words (each ending with _)
            rf'({snake_case_name})s?'  # Match the router name with optional pluralization  
            r'(?:_by_[a-zA-Z0-9_]+)*$'  # Zero or more "by_<criteria>" suffixes, end of string
        )

    def _collect_endpoints(self) -> list[BoundEndpoint]:
        endpoints = []
        public_names = [x for x in dir(self) if not x.startswith('_')]

        for name in public_names:
            value = getattr(self, name)
            if callable(value) and (m := re.match(self._regex, name)):
                verb = m.group(1)
                
                # Additional validation to prevent invalid patterns
                # Check for cases like "gets_test_router" where "gets" looks like a verb but isn't exact
                if verb:
                    # Ensure the verb is at the exact start
                    if not name.startswith(f'{verb}_'):
                        continue
                else:
                    # For non-verb patterns, check if it starts with a partial verb
                    # This catches cases like "gets_test_router" where gets_ is treated as descriptive
                    verb_prefixes = ['get', 'post', 'put', 'patch', 'head', 'delete', 'options', 'update', 'create', 'new', 'remove']
                    starts_with_invalid_verb = False
                    for verb_prefix in verb_prefixes:
                        if name.startswith(verb_prefix) and not name.startswith(f'{verb_prefix}_'):
                            # This is something like "gets_test_router" - invalid
                            starts_with_invalid_verb = True
                            break
                    if starts_with_invalid_verb:
                        continue
                    
                http_verb = _INTENTIONS_MAPPING.get(verb, 'GET')  # Default to GET if no verb is specified

                # Get path params using parameter extraction system
                signature = inspect.signature(value)
                path_params = []
                
                for param_name, param in signature.parameters.items():
                    # TODO ignore first parameter instead of checking for param_name == 'self'?
                    if param_name == 'self':
                        continue
                    
                    # Only check for explicitly annotated path parameters
                    if hasattr(param.annotation, '__metadata__'):
                        for metadata in param.annotation.__metadata__:
                            if isinstance(metadata, Path):
                                braced_param = f'{{{param_name}}}'
                                path_params.append(braced_param)
                                break

                joined_path_params = '/' + '/'.join(path_params) if path_params else ''

                endpoints.append(
                    BoundEndpoint(
                        endpoint=Endpoint(
                            method=http_verb,
                            func=value,
                            path=joined_path_params,
                        ),
                        instance=self,
                    ),
                )

        return endpoints
    

class DecoratedRouter(BaseRouter):
    def _collect_endpoints(self):
        routes = []
        public_names = [x for x in dir(self) if not x.startswith('_')]

        for name in public_names:
            value = getattr(self, name)

            if callable(value) and isinstance(value, BoundEndpoint):
                routes.append(value)

        routes.sort(key=route_priority)

        return routes

def router(path: str) -> Type[DecoratedRouter]:
    class _DecoratedRouter(DecoratedRouter):
        def __init__(self):
            super().__init__(path=path)

    return _DecoratedRouter