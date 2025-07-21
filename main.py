import inspect
from types import MethodType
from typing import Callable, Mapping, MutableSequence, Optional, Type, Union

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import (HTMLResponse, JSONResponse, RedirectResponse,
                                 Response)
from starlette.routing import Route


def _human_friendly_description_from_name(name: str) -> str:
    return ' '.join(name.split('_')).capitalize()


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

    def __call__(self, ep_fn: Callable) -> 'Endpoint':
        self.ep_fn = ep_fn

        async def route_handler(request: Request):
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
            return JSONResponse(result)

        self._build_route = lambda base_path: Route(
            path=base_path + self.path,
            endpoint=route_handler,
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

            # /openapi.json
            async def openapi_endpoint(request: Request):
                spec = {
                    'openapi': '3.0.0', 
                    'info': {
                        'title': title or f'{self.__class__.__name__} API',
                        'description': description or self.__class__.__doc__ or f'REST API for {self.__class__.__name__}',
                        'version': version,
                        'tags': [{'name': self.__class__.__name__, 'description': self.__class__.__doc__}]
                    }, 
                    'paths': {},
                }
                for ep in self.endpoints:
                    update_dict(spec['paths'], ep.get_openapi_spec(self))
                return JSONResponse(spec)
            routes.append(Route("/openapi.json", openapi_endpoint, methods=["GET"]))

            # /docs/redoc
            async def redoc_ui(request: Request):
                html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>ReDoc</title>
                    <meta charset="utf-8"/>
                </head>
                <body>
                    <redoc spec-url='/openapi.json'></redoc>
                    <script src="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"></script>
                </body>
                </html>
                """
                return HTMLResponse(html)
            routes.append(Route("/docs/redoc", redoc_ui, methods=["GET"]))

            # /docs/swagger
            async def swagger_ui(request: Request):
                html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Swagger UI</title>
                    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist/swagger-ui.css" />
                    <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
                    <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-standalone-preset.js"></script>
                </head>
                <body>
                    <div id="swagger-ui"></div>
                    <script>
                    SwaggerUIBundle({
                        url: '/openapi.json',
                        dom_id: '#swagger-ui',
                        presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
                        layout: "BaseLayout"
                    });
                    </script>
                </body>
                </html>
                """
                return HTMLResponse(html)
            routes.append(Route("/docs/swagger", swagger_ui, methods=["GET"]))

            # /docs/rapidoc
            async def rapidoc_ui(request: Request):
                html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>RapiDoc</title>
                    <script type="module" src="https://unpkg.com/rapidoc/dist/rapidoc-min.js"></script>
                </head>
                <body>
                    <rapi-doc spec-url="/openapi.json" theme="dark" show-header="true" render-style="read"></rapi-doc>
                </body>
                </html>
                """
                return HTMLResponse(html)
            routes.append(Route("/docs/rapidoc", rapidoc_ui, methods=["GET"]))

            # Optional: redirect /docs → Swagger UI
            routes.append(Route("/docs", lambda request: RedirectResponse("/docs/swagger"), methods=["GET"]))

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
        return [user.model_dump() for user in self.users.get_users()]

    @post('/')
    def add_user(self, user: User):
        user_id = self.users.add_user(user)
        return {'id': user_id}

    @get('/{user_id}')
    def get_user_by_id(self, user_id: int):
        return self.users.get_user(user_id).model_dump()

    @put('/{user_id}')
    def update_user(self, user_id: int, user: User):
        return {'msg': f"Updated user {user_id} with {user.model_dump()}"}

    @delete('/{user_id}')
    def delete_user(self, user_id: int):
        return {'msg': f"Deleted user {user_id}"}

    @options('/')
    def options_users(self):
        """Determine **what** can be done with the `/users` endpoint
        """
        return {'methods': ['GET', 'POST', 'OPTIONS']}

user_service = UserService()
app = Users(user_service)

# Uncomment to run
uvicorn.run(app, host="127.0.0.1", port=8000)
