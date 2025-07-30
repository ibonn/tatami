import logging
import os
import shutil
import warnings
from importlib.resources import files
from types import ModuleType
from typing import Callable, Optional

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import FileResponse
from starlette.routing import Route
from starlette.staticfiles import StaticFiles

from tatami._utils import import_from_path
from tatami.config import Config, find_config, load_config
from tatami.router import BaseRouter, ProjectIntrospection

logger = logging.getLogger('tatami.convention')

def _for_each_module_in(path: str, callback: Callable):
    for filename in os.listdir(path):
        full_path = os.path.join(path, filename)
        _, ext = os.path.splitext(filename)
        if os.path.isfile(full_path) and ext == '.py':
            module = import_from_path(full_path)
            callback(module)

def _add_router(app: BaseRouter, introspection: ProjectIntrospection) -> Callable[[ModuleType], None]:
    def add_router(router_module: ModuleType) -> None:
        for name in dir(router_module):
            if not name.startswith('_'):
                try:
                    value = getattr(router_module, name)
                    
                    if isinstance(value, type):
                        if issubclass(value, BaseRouter):
                            router = value()
                            app.include_router(router)
                            
                            # Track in introspection
                            introspection.routers.append({
                                'name': name,
                                'class': value,
                                'instance': router,
                                'module': getattr(router_module, '__name__', '<unknown>'),
                                'type': value.__class__.__name__
                            })

                        else:
                           warnings.warn(f'Non router class found at routers: {value.__name__}')
                except Exception as e:
                    logger.error(f"Error processing router module attribute {name}: {e}")
                    continue

    return add_router

def _add_middleware(app: BaseRouter, introspection: ProjectIntrospection) -> Callable[[ModuleType], None]:
    def add_middleware(middleware_module: ModuleType) -> None:
        for name in dir(middleware_module):
            if not name.startswith('_'):
                value = getattr(middleware_module, name)

                if issubclass(value, Middleware):
                    # TODO find a way to pass arguments
                    app.add_middleware(value)
                    
                    # Track in introspection
                    introspection.middleware.append({
                        'name': name,
                        'class': value,
                        'module': getattr(middleware_module, '__name__', '<unknown>')
                    })

                else:
                    # TODO transform classes into routers
                    warnings.warn("Non middleware class found in a file under the 'middleware' directory. Tatami currently ignores such classes, but will later support automatic conversion to middleware. Avoid placing non-middleware code here for now")

    return add_middleware


def _load_models(introspection: ProjectIntrospection) -> Callable[[ModuleType], None]:
    """Load Pydantic models from model modules and store them in introspection."""
    def load_models(model_module: ModuleType) -> None:
        for name in dir(model_module):
            if not name.startswith('_'):
                try:
                    value = getattr(model_module, name)
                    
                    # Check if it's a class and a Pydantic model
                    if isinstance(value, type) and issubclass(value, BaseModel):
                        introspection.models[name] = value
                        logger.debug(f"Loaded Pydantic model: {name}")
                            
                except Exception as e:
                    logger.error(f"Error processing model module attribute {name}: {e}")
                    continue

    return load_models


def get_favicon_router(favicon_path: str) -> Callable[[Request], FileResponse]:
    def favicon_router(request: Request) -> FileResponse:
        return FileResponse(favicon_path)
    return favicon_router


def build_from_dir(path: str, mode: Optional[str] = None, routers_dir: str = 'routers', middleware_dir: str = 'middleware', models_dir: str = 'models', mounts_dir: str = 'mounts', static_dir: str = 'static', templates_dir: str = 'templates', favicon_file: str = 'favicon.ico', readme_file: str = 'README.md') -> tuple[BaseRouter, ProjectIntrospection]:
    # Load config
    config_path = find_config(path, mode)

    # Try to load fallback config
    if config_path is None and mode is not None:
        config_path = find_config(path)
        logger.warning('Could not locate configuration for mode "%s", will try to load the default project config', mode)
        warnings.warn(f'Could not locate configuration for mode "{mode}", will try to load the default project config')
    
    # If the config is still None, warn the user and load the default config
    if config_path is None:
        logger.warning('Could not locate any configuration files for the project. The default config will be loaded')
        warnings.warn('Could not locate any configuration files for the project. The default config will be loaded')
        config = Config()
    else:
        config = load_config(config_path)

    # Paths
    routers_path = os.path.join(path, routers_dir)
    middleware_path = os.path.join(path, middleware_dir)
    models_path = os.path.join(path, models_dir)
    mounts_path = os.path.join(path, mounts_dir)
    static_path = os.path.join(path, static_dir)
    templates_path = os.path.join(path, templates_dir)
    favicon_path = os.path.join(path, favicon_file)
    readme_path = os.path.join(path, readme_file)

    if os.path.isfile(readme_path):
        logger.debug('Loading description from readme...')
        with open(readme_path, 'r', encoding='utf-8') as f:
            description = f.read()
    else:
        logger.debug('No readme found, skipping...')
        description = None

    app = BaseRouter(title=config.app_name, description=description, version=config.version)
    
    # Create introspection object
    introspection = ProjectIntrospection(
        config_file=os.path.basename(config_path) if config_path else None,
        static_path=static_path if os.path.isdir(static_path) else None,
        templates_path=templates_path if os.path.isdir(templates_path) else None,
        favicon_path=favicon_path if os.path.isfile(favicon_path) else None
    )

    if os.path.isdir(routers_path):
        _for_each_module_in(routers_path, _add_router(app, introspection))
    else:
        logger.debug('No routers directory found, skipping...')

    if os.path.isdir(middleware_path):
        _for_each_module_in(middleware_path, _add_middleware(app, introspection))
    else:
        logger.debug('No middleware directory found, skipping...')

    if os.path.isdir(models_path):
        _for_each_module_in(models_path, _load_models(introspection))
        introspection.models_source = models_path
        logger.debug('Loaded models from directory %s', models_path)
    else:
        # Check for models.py file
        models_file = os.path.join(path, f'{models_dir}.py')
        if os.path.isfile(models_file):
            model_module = import_from_path(models_file)
            _load_models(introspection)(model_module)
            introspection.models_source = models_file
            logger.debug('Loaded models from file %s', models_file)
        else:
            logger.debug('No models directory or models.py file found, skipping...')

    if os.path.isdir(mounts_path):
        # TODO allow mounting non-tatami apps (if instead of a dir it is a .py, load it and mount the found app)
        for mount_name in os.listdir(mounts_path):
            full_path = os.path.join(mounts_path, mount_name)
            mount_app, mount_introspection = build_from_dir(full_path, mode=mode)
            app.mount(f'/{mount_name}', mount_app)
            
            # Track in introspection
            introspection.mounts.append({
                'name': mount_name,
                'path': f'/{mount_name}',
                'source_path': full_path,
                'app': mount_app,
                'introspection': mount_introspection
            })
    else:
        logger.debug('No mounts directory found, skipping...')

    if os.path.isdir(static_path):
        app.mount('/static', StaticFiles(directory=static_path))
    else:
        logger.debug('No static directory found, skipping...')

    if os.path.isdir(templates_path):
        app.templates = Environment(loader=FileSystemLoader(templates_path))
    else:
        logger.debug('No templates directory found, skipping...')

    if os.path.isfile(favicon_path):
        logger.debug('Loading favicon from %s...', favicon_path)
        favicon_router = get_favicon_router(favicon_path)
    else:
        logger.debug('No favicon found, adding default favicon...')
        favicon_router = get_favicon_router(files('tatami.data.images') / 'favicon.ico')
    app.add_route(Route('/favicon.ico', favicon_router, include_in_schema=False))

    return app, introspection


def build_app_from_dir(path: str, mode: Optional[str] = None, **kwargs) -> BaseRouter:
    """
    Backward compatibility function that returns only the app.
    For new code, prefer using build_from_dir which returns both app and introspection.
    """
    app, _ = build_from_dir(path, mode, **kwargs)
    return app


def create_project(path: str, routers_dir: str = 'routers', middleware_dir: str = 'middleware', models_dir: str = 'models', mounts_dir: str = 'mounts', static_dir: str = 'static', templates_dir: str = 'templates', favicon_file: str = 'favicon.ico', readme_file: str = 'README.md') -> None:
    config_path = os.path.join(path, 'config.yaml')
    dev_config_path = os.path.join(path, 'config-dev.yaml')
    routers_path = os.path.join(path, routers_dir)
    middleware_path = os.path.join(path, middleware_dir)
    models_file = os.path.join(path, f'{models_dir}.py')
    mounts_path = os.path.join(path, mounts_dir)
    static_path = os.path.join(path, static_dir)
    templates_path = os.path.join(path, templates_dir)
    favicon_path = os.path.join(path, favicon_file)
    readme_path = os.path.join(path, readme_file)

    # Create the directories
    os.makedirs(routers_path)
    os.makedirs(middleware_path)
    os.makedirs(mounts_path)
    os.makedirs(static_path)
    os.makedirs(templates_path)

    # Create empty config, readme, and models files
    open(config_path, 'w', encoding='utf-8').close()
    open(dev_config_path, 'w', encoding='utf-8').close()
    open(readme_path, 'w', encoding='utf-8').close()
    
    # Create a basic models.py file with an example
    with open(models_file, 'w', encoding='utf-8') as f:
        f.write('''"""
Pydantic models for the application.
"""
from pydantic import BaseModel


# Example model - replace with your own models
# class User(BaseModel):
#     name: str
#     email: str
''')

    # Copy the favicon
    shutil.copy(files('tatami.data.images') / 'favicon.ico', favicon_path)
