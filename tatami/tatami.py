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
