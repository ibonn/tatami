from typing import Optional, Type

from starlette.applications import Starlette

from tatami._utils import update_dict
from tatami.endpoint import Endpoint


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
