import inspect
import logging
import re
from typing import Any, NoReturn, Optional, Self, Type

import uvicorn
from pydantic import BaseModel, Field
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from tatami._utils import camel_to_snake, update_dict
from tatami.core import TatamiObject
from tatami.endpoint import BoundEndpoint, Endpoint, _extract_parameters
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
    def __init__(self, title: Optional[str] = None, description: Optional[str] = None, version: str = '0.0.1', path: Optional[str] = None, tags: Optional[list[str]] = None):
        super().__init__()
        self.title = title
        self.description = description
        self.version = version
        self.path = path or '/'
        self.tags = tags or []

        self._routers: list[BaseRouter] = []
        self._routes: list[Route] = []
        self._mounts: dict[str, Any] = {}
        self._summary = None

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
    
    @property
    def summary(self) -> Optional[Summary]:
        return self._summary
    
    @property
    def routers(self) -> list['BaseRouter']:
        return self._routers

    def _collect_endpoints(self) -> list[BoundEndpoint]:
        return []

    def _starlette(self) -> Starlette:
        logger.debug('Building starlette app...')
        endpoints = self._collect_endpoints()
        routes = [endpoint.get_route() for endpoint in endpoints]

        logger.debug('%s + %s additional routes found', len(routes), len(self._routes))
        app = Starlette(
            routes=routes + self._routes
        )

        logger.debug('Mounting routers...')
        for sub_router in self._routers:
            app.mount(sub_router.path, sub_router._starlette())

        logger.debug('Mounting apps...')
        for mount_path, mount_app in self._mounts.items():
            app.mount(mount_path, mount_app)

        return app
    
    def get_openapi_spec(self) -> dict:
        endpoints = self._collect_endpoints()

        spec = {
            'openapi': '3.0.0',
            'info': {
                'title': self.title or self.__class__.__name__,
                'version': self.version,
                'description': self.description or self.__doc__ or f'API for {self.__class__.__name__}',
            },
            'paths': {},
            'tags': [],
            'components': {
                'schemas': {}
            },
        }

        tags_seen = set()
        schemas = {}

        def add_schema(model: type[BaseModel]) -> str:
            """Add a Pydantic model schema to the OpenAPI spec with examples"""
            name = model.__name__
            if name not in schemas:
                schema = model.model_json_schema(ref_template='#/components/schemas/{model}')
                
                # Add examples if available from Field descriptions
                if 'properties' in schema:
                    for prop_name, prop_schema in schema['properties'].items():
                        field_info = model.model_fields.get(prop_name)
                        if field_info and hasattr(field_info, 'examples') and field_info.examples:
                            prop_schema['examples'] = field_info.examples
                        elif field_info and hasattr(field_info, 'description') and field_info.description:
                            prop_schema['description'] = field_info.description
                
                # Try to generate an example instance
                try:
                    # Create example with default or example values
                    example_data = {}
                    for field_name, field_info in model.model_fields.items():
                        if hasattr(field_info, 'examples') and field_info.examples:
                            example_data[field_name] = field_info.examples[0]
                        elif hasattr(field_info, 'default') and field_info.default is not None:
                            example_data[field_name] = field_info.default
                        else:
                            # Generate reasonable default based on type
                            field_type = field_info.annotation
                            if field_type == str:
                                example_data[field_name] = "string"
                            elif field_type == int:
                                example_data[field_name] = 0
                            elif field_type == float:
                                example_data[field_name] = 0.0
                            elif field_type == bool:
                                example_data[field_name] = True
                    
                    if example_data:
                        schema['example'] = example_data
                except Exception:
                    pass  # Skip example generation if it fails
                
                schemas[name] = schema
            return name

        def get_parameter_schema(param_type: type) -> dict:
            """Get OpenAPI schema for a parameter type"""
            if param_type == int:
                return {'type': 'integer', 'format': 'int32'}
            elif param_type == float:
                return {'type': 'number', 'format': 'float'}
            elif param_type == bool:
                return {'type': 'boolean'}
            elif param_type == str:
                return {'type': 'string'}
            else:
                return {'type': 'string'}  # default fallback

        for endpoint in endpoints:
            if not endpoint.include_in_schema:
                continue

            method = endpoint.method.lower()
            path = (self.path or '') + endpoint.path

            if path not in spec['paths']:
                spec['paths'][path] = {}

            docstring = endpoint.docs.strip().split('\n')[0] if endpoint.docs else ''

            # Extract all parameters using the new system
            parameters = []
            request_body = None
            
            # Get parameter information from endpoint signature
            parameters_info = _extract_parameters(endpoint._endpoint.func, endpoint.path)
            
            # Process path parameters
            for param_name, param_info in parameters_info.get('path', {}).items():
                parameters.append({
                    'name': param_info['key'],
                    'in': 'path',
                    'required': True,
                    'schema': get_parameter_schema(param_info['type']),
                    'description': f'Path parameter {param_info["key"]}'
                })
            
            # Process query parameters
            for param_name, param_info in parameters_info.get('query', {}).items():
                parameters.append({
                    'name': param_info['key'],
                    'in': 'query',
                    'required': False,  # Query parameters are optional by default
                    'schema': get_parameter_schema(param_info['type']),
                    'description': f'Query parameter {param_info["key"]}'
                })
            
            # Process header parameters
            for param_name, param_info in parameters_info.get('headers', {}).items():
                parameters.append({
                    'name': param_info['key'],
                    'in': 'header',
                    'required': False,  # Headers are optional by default
                    'schema': get_parameter_schema(param_info['type']),
                    'description': f'Header parameter {param_info["key"]}'
                })
            
            # Process body parameters
            for param_name, model_class in parameters_info.get('body', {}).items():
                if issubclass(model_class, BaseModel):
                    schema_name = add_schema(model_class)
                    request_body = {
                        'required': True,
                        'content': {
                            'application/json': {
                                'schema': {'$ref': f'#/components/schemas/{schema_name}'}
                            }
                        }
                    }

            # Response body
            responses = {
                "200": {
                    "description": "Successful response",
                }
            }

            # Try to introspect return type from function signature
            if endpoint.response_type:
                if issubclass(endpoint.response_type, JSONResponse):
                    responses["200"]["content"] = {
                        "application/json": {
                            "schema": {"type": "object"}
                        }
                    }
                elif issubclass(endpoint.response_type, HTMLResponse):
                    responses["200"]["content"] = {
                        "text/html": {
                            "schema": {"type": "string"}
                        }
                    }
                else:
                    # Default to JSON
                    responses["200"]["content"] = {
                        "application/json": {
                            "schema": {"type": "object"}
                        }
                    }
            else:
                # Try to get return annotation from function signature
                return_annotation = endpoint.signature.return_annotation
                if return_annotation and return_annotation != inspect.Signature.empty:
                    if return_annotation == str:
                        responses["200"]["content"] = {
                            "text/plain": {
                                "schema": {"type": "string"}
                            }
                        }
                    elif return_annotation == dict or hasattr(return_annotation, '__dict__'):
                        responses["200"]["content"] = {
                            "application/json": {
                                "schema": {"type": "object"}
                            }
                        }
                    else:
                        responses["200"]["content"] = {
                            "application/json": {
                                "schema": {"type": "object"}
                            }
                        }
                else:
                    # Default response
                    responses["200"]["content"] = {
                        "application/json": {
                            "schema": {"type": "object"}
                        }
                    }

            # Tags
            # Order of resolution: User specified (endpoint) -> user specified (router) -> class name of the router
            tags = endpoint.tags or self.tags or [self.__class__.__name__]
            for tag in tags:
                if tag not in tags_seen:
                    tags_seen.add(tag)
                    if len(tags) == 1 and tags[0] == self.__class__.__name__:
                        spec['tags'].append({'name': tag, 'description': self.summary or tag})

            spec['paths'][path][method] = {
                'tags': tags,
                'summary': endpoint.summary,
                'description': docstring,
                'parameters': parameters or [],
                'responses': responses,
                'deprecated': endpoint.deprecated,
            }

            if request_body:
                spec['paths'][path][method]['requestBody'] = request_body

        # Merge child routers' paths
        for child_router in self._routers:
            child_spec = child_router.get_openapi_spec()
            update_dict(spec['paths'], child_spec['paths'])
            update_dict(spec['components']['schemas'], child_spec.get('components', {}).get('schemas', {}))
            for tag in child_spec.get('tags', []):
                if tag['name'] not in tags_seen:
                    spec['tags'].append(tag)
                    tags_seen.add(tag['name'])

        # Inject collected schemas
        spec['components']['schemas'].update(schemas)

        return spec

        
    def run(self, host: str = 'localhost', port: int = 8000, openapi_url: Optional[str] = '/openapi.json', swagger_url: Optional[str] = '/docs/swagger', redoc_url: Optional[str] = '/docs/redoc', rapidoc_url: Optional[str] = '/docs/rapidoc') -> NoReturn:
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
        
        async def openapi_endpoint(request: Request):
            return JSONResponse(self.get_openapi_spec())

        async def redocs_endpoint(request: Request):
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{self.title} - ReDoc</title>
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
                <title>{self.title} - Swagger UI</title>
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
                <title>{self.title} - RapiDoc</title>
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

class ConventionRouter(BaseRouter):
    def __init__(self):
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

        return routes

def router(path: str) -> Type[DecoratedRouter]:
    class _DecoratedRouter(DecoratedRouter):
        def __init__(self):
            super().__init__(path=path)

    return _DecoratedRouter