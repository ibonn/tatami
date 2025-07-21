import inspect
from types import MethodType
from typing import Awaitable, Callable, Optional, Self, Type, Union

import uvicorn
from pydantic import BaseModel
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route

from tatami._utils import (_human_friendly_description_from_name,
                           get_request_type, update_dict, wrap_response)


class Router(Starlette):
    path: str

    def __init__(self, title: Optional[str] = None, description: Optional[str] = None, version: Optional[str] = None, debug = False, routes = None, middleware = None, exception_handlers = None, on_startup = None, on_shutdown = None, lifespan = None):
        super().__init__(debug, routes, middleware, exception_handlers, on_startup, on_shutdown, lifespan)
        self.title = title
        self.description = description
        self.version = version

    def _get_base_openapi_spec(self) -> dict:
        return {
            'openapi': '3.0.0',
            'info': {
                'title': self.title or self.__class__.__name__,
                'version': self.version,
                'description': self.description or self.__doc__ or f'API for {self.__class__.__name__}',
            },
            'paths': {},
            'tags': [],
        }

    def get_openapi_spec(self) -> dict:
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

            super().__init__(routes=routes)

    return _Router


# Universal request helper
def request(method: str, path: str, response_type: Optional[Type[Response]] = None) -> Endpoint:
    return Endpoint(method, path, response_type=response_type)

# Convenience decorators for all HTTP verbs
def get(path: str, response_type: Optional[Type[Response]] = None) -> Callable:
    return request('GET', path, response_type)
def post(path: str, response_type: Optional[Type[Response]] = None) -> Callable:
    return request('POST', path, response_type)
def put(path: str, response_type: Optional[Type[Response]] = None) -> Callable:
    return request('PUT', path, response_type)
def patch(path: str, response_type: Optional[Type[Response]] = None) -> Callable:
    return request('PATCH', path, response_type)
def delete(path: str, response_type: Optional[Type[Response]] = None) -> Callable:
    return request('DELETE', path, response_type)
def head(path: str, response_type: Optional[Type[Response]] = None) -> Callable:
    return request('HEAD', path, response_type)
def options(path: str, response_type: Optional[Type[Response]] = None) -> Callable:
    return request('OPTIONS', path, response_type)

class Tatami(Router):
    def __init__(self, title: Optional[str] = None, description: Optional[str] = None, version: Optional[str] = None, debug = False, routes = None, middleware = None, exception_handlers = None, on_startup = None, on_shutdown = None, lifespan = None):
        super().__init__(debug, routes, middleware, exception_handlers, on_startup, on_shutdown, lifespan)
        self.title = title
        self.description = description
        self.version = version

    def include_router(self, router: Router) -> Self:
        self.mount(router.path, router)
        return self
    
    def get_openapi_spec(self):
        base = self._get_base_openapi_spec()

        for route in self.routes:
            if isinstance(route.app, Router):
                update_dict(base['paths'], route.app.get_openapi_spec()['paths'])
                base['tags'].append({
                    'name': route.app.__class__.__name__,
                    'description': route.app.__class__.__doc__ or ''
                })

        return base

    

def run(app: Tatami, host: str = 'localhost', port: int = 8000, openapi_url: Optional[str] = '/openapi.json', swagger_url: Optional[str] = '/docs/swagger', redoc_url: Optional[str] = '/docs/redoc', rapidoc_url: Optional[str] = '/docs/rapidoc') -> None:
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
