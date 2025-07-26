import inspect
import logging
import re
from typing import NoReturn, Optional, Self, Type, Any

import uvicorn
from pydantic import BaseModel, Field
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from tatami._utils import camel_to_snake, is_path_param, update_dict
from tatami.core import TatamiObject
from tatami.endpoint import BoundEndpoint, Endpoint

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
    static: Optional[str] = Field(description='path to the static files', default=None)
    templates: Optional[str] = Field(description='path to the directory containing the templates', default=None)


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
            name = model.__name__
            if name not in schemas:
                schemas[name] = model.model_json_schema(ref_template='#/components/schemas/{model}')
            return name

        for endpoint in endpoints:
            if not endpoint.include_in_schema:
                continue

            method = endpoint.method.lower()
            path = (self.path or '') + endpoint.path

            if path not in spec['paths']:
                spec['paths'][path] = {}

            docstring = endpoint.docs.strip().split('\n')[0] if endpoint.docs else ''

            # Path parameters
            parameters = []
        
            for param in endpoint.signature.parameters.values():
                if is_path_param(param.annotation):
                    # Determine schema type based on annotation
                    schema = {'type': 'string'}  # default
                    if param.annotation == int:
                        schema = {'type': 'integer'}
                    elif param.annotation == float:
                        schema = {'type': 'number'}
                    elif param.annotation == bool:
                        schema = {'type': 'boolean'}
                    elif hasattr(param.annotation, '__origin__') and param.annotation.__origin__ is list:
                        schema = {'type': 'array', 'items': {'type': 'string'}}
                    
                    parameters.append({
                        'name': param.name,
                        'in': 'path',
                        'required': True,
                        'schema': schema,
                    })

            # Request body (only if applicable)
            request_body = None
            if endpoint.request_type:
                for param_name, model in endpoint.request_type.items():
                    model_name = add_schema(model)
                    request_body = {
                        'content': {
                            'application/json': {
                                'schema': {'$ref': f"#/components/schemas/{model_name}"}
                            }
                        },
                        'required': True
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

        self._regex = f'(get|post|put|patch|head|delete|options|update|create|new|remove)_(?:{snake_case_name}?)s?'
        
    def _collect_endpoints(self) -> list[BoundEndpoint]:
        endpoints = []
        public_names = [x for x in dir(self) if not x.startswith('_')]

        for name in public_names:
            value = getattr(self, name)
            if callable(value) and (m := re.match(self._regex, name)):
                http_verb = _INTENTIONS_MAPPING[m.group(1)]

                # Get path params
                signature = inspect.signature(value)
                path_params = []
                for param in signature.parameters.values():
                    if is_path_param(param.annotation):
                        braced_param = f'{{{param.name}}}'
                        path_params.append(braced_param)

                if len(path_params) == 0:
                    joined_path_params = ''
                else:
                    joined_path_params = '/' + '/'.join(path_params)

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