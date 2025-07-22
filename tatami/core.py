import logging
import os
from typing import NoReturn, Optional, Union

import uvicorn
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from tatami.tatami import Tatami

logger = logging.getLogger('tatami.core')




def create_project(name: str, middleware_dir: str = 'middleware', routers_dir: str = 'routers', static_dir: str = 'static', templates_dir: str = 'templates', services_dir: str = 'services', tests_dir: str = 'tests') -> None:
    middleware_path = os.path.join(name, middleware_dir)
    routers_path = os.path.join(name, routers_dir)
    static_path = os.path.join(name, static_dir)
    templates_path = os.path.join(name, templates_dir)
    services_path = os.path.join(name, services_dir)
    tests_path = os.path.join(name, tests_dir)
    config_path = os.path.join(name, 'config.yaml')


    # Create the folders
    os.makedirs(middleware_path)
    os.makedirs(routers_path)
    os.makedirs(static_path)
    os.makedirs(templates_path)
    os.makedirs(services_path)
    os.makedirs(tests_path)

    # Create the config file
    open(config_path, 'w', encoding='utf-8').close()


def run(app: Tatami, host: str = 'localhost', port: int = 8000, openapi_url: Optional[str] = '/openapi.json', swagger_url: Optional[str] = '/docs/swagger', redoc_url: Optional[str] = '/docs/redoc', rapidoc_url: Optional[str] = '/docs/rapidoc') -> NoReturn:
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
