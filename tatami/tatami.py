import importlib
import logging
import os
from typing import Optional, Self

from starlette.routing import Route

from tatami._utils import package_from_path, update_dict, _none_if_dir_not_exists
from tatami.router import Router

logger = logging.getLogger('tatami.tatami')


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
