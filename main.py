import inspect
import os
from io import IOBase
from types import MethodType
from typing import (Any, Awaitable, Callable, Mapping, MutableSequence,
                    Optional, Self, Type, Union)

from jinja2 import Environment, FileSystemLoader
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import (HTMLResponse, JSONResponse, Response,
                                 StreamingResponse)
from starlette.routing import Route

def serialize_json(x: Any) -> Any:
    if isinstance(x, BaseModel):
        return x.model_dump()
    
    if isinstance(x, (list, tuple)):
        return [serialize_json(y) for y in x]
    
    if isinstance(x, Mapping):
        return {a: serialize_json(b) for a, b in x.items()}
    
    return x


class TemplateResponse(HTMLResponse):
    def __init__(self, template_name: str, content = None, status_code = 200, headers = None, media_type = None, background = None):
        environment = Environment(loader=FileSystemLoader('templates'))
        template = environment.get_template(template_name)
        super().__init__(template.render(content), status_code, headers, media_type, background)

def _human_friendly_description_from_name(name: str) -> str:
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
    def __init__(self, method: str, path: str, response_type: Optional[Type[Response]] = None, summary: Optional[str] = None, description: Optional[str] = None, tags: Optional[list[Tag]] = None):
        self.method = method.upper()
        self.path = path
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
                kwargs.update(body)
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
    return Endpoint(method, path, response_type)

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

########################
# TODO build from directory structure
# TODO automatically inject dependencies
# TODO automatically detect html templates/response types

import uvicorn
from pydantic import BaseModel, Field


class User(BaseModel):
    name: str = Field(description='The user name')
    age: int = Field(description='Age')

class UserService:
    def add_user(self, user: User) -> int:
        return 42

    def get_user(self, id: int) -> User:
        return User(name="Alice", age=30)

    def get_users(self) -> list[User]:
        return [User(name="Alice", age=30), User(name="Bob", age=25)]

class Users(router('/users')):
    """User management endpoints"""
    def __init__(self, users: UserService):
        self.users = users
        super().__init__()

    @get('/')
    def get_users(self):
        return [user for user in self.users.get_users()]

    @post('/')
    def add_user(self, user: User):
        user_id = self.users.add_user(user)
        return {'id': user_id}

    @get('/{user_id}')
    def get_user_by_id(self, user_id: int):
        return self.users.get_user(user_id)

    @put('/{user_id}')
    def update_user(self, user_id: int, user: User):
        return {'msg': f"Updated user {user_id} with {user}"}

    @delete('/{user_id}')
    def delete_user(self, user_id: int):
        return {'msg': f"Deleted user {user_id}"}

    @options('/')
    def options_users(self):
        """Determine **what** can be done with the `/users` endpoint
        """
        return {'methods': ['GET', 'POST', 'OPTIONS']}
    
class Pets(router('/pets')):
    @get('/')
    def get_pets(self):
        return ['NO PETS']

user_service = UserService()
users = Users(user_service)
pets = Pets()

app = Tatami()
app.include_router(users)
app.include_router(pets)

# Uncomment to run
run(app, host="127.0.0.1", port=8000)
