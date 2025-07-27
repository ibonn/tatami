"""
OpenAPI specification generation and documentation UI for Tatami.

This module handles all OpenAPI-related functionality including:
- OpenAPI 3.0 spec generation
- Interactive documentation UIs (Swagger, ReDoc, RapiDoc)
- Schema generation for Pydantic models
- Parameter schema extraction
"""

import inspect

from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from tatami._utils import update_dict
from tatami.endpoint import _extract_parameters


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


def add_schema_to_spec(model: type[BaseModel], schemas: dict) -> str:
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
        except (AttributeError, TypeError, ValueError):
            pass  # Skip example generation if it fails
        
        schemas[name] = schema
    return name


def generate_openapi_spec(router_instance) -> dict:
    """
    Generate OpenAPI 3.0 specification for a router and its endpoints.
    
    Args:
        router_instance: The router instance to generate spec for
        
    Returns:
        dict: Complete OpenAPI 3.0 specification
    """
    endpoints = router_instance._collect_endpoints()

    spec = {
        'openapi': '3.0.0',
        'info': {
            'title': router_instance.title or router_instance.__class__.__name__,
            'version': router_instance.version,
            'description': router_instance.description or router_instance.__doc__ or f'API for {router_instance.__class__.__name__}',
        },
        'paths': {},
        'tags': [],
        'components': {
            'schemas': {}
        },
    }

    tags_seen = set()
    schemas = {}

    for endpoint in endpoints:
        if not endpoint.include_in_schema:
            continue

        method = endpoint.method.lower()
        path = (router_instance.path or '') + endpoint.path

        if path not in spec['paths']:
            spec['paths'][path] = {}

        docstring = endpoint.docs.strip().split('\n')[0] if endpoint.docs else ''

        # Extract all parameters using the new system
        parameters = []
        request_body = None
        
        # Get parameter information from endpoint signature
        parameters_info = _extract_parameters(endpoint._endpoint.func, endpoint.path)
        
        # Process path parameters
        for _, param_info in parameters_info.get('path', {}).items():
            parameters.append({
                'name': param_info['key'],
                'in': 'path',
                'required': True,
                'schema': get_parameter_schema(param_info['type']),
                'description': f'Path parameter {param_info["key"]}'
            })
        
        # Process query parameters
        for _, param_info in parameters_info.get('query', {}).items():
            parameters.append({
                'name': param_info['key'],
                'in': 'query',
                'required': False,  # Query parameters are optional by default
                'schema': get_parameter_schema(param_info['type']),
                'description': f'Query parameter {param_info["key"]}'
            })
        
        # Process header parameters
        for _, param_info in parameters_info.get('headers', {}).items():
            parameters.append({
                'name': param_info['key'],
                'in': 'header',
                'required': False,  # Headers are optional by default
                'schema': get_parameter_schema(param_info['type']),
                'description': f'Header parameter {param_info["key"]}'
            })
        
        # Process body parameters
        for _, model_class in parameters_info.get('body', {}).items():
            if issubclass(model_class, BaseModel):
                schema_name = add_schema_to_spec(model_class, schemas)
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
        tags = endpoint.tags or router_instance.tags or [router_instance.__class__.__name__]
        for tag in tags:
            if tag not in tags_seen:
                tags_seen.add(tag)
                if len(tags) == 1 and tags[0] == router_instance.__class__.__name__:
                    spec['tags'].append({'name': tag, 'description': router_instance.summary or tag})

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
    for child_router in router_instance._routers:
        child_spec = generate_openapi_spec(child_router)
        update_dict(spec['paths'], child_spec['paths'])
        update_dict(spec['components']['schemas'], child_spec.get('components', {}).get('schemas', {}))
        for tag in child_spec.get('tags', []):
            if tag['name'] not in tags_seen:
                spec['tags'].append(tag)
                tags_seen.add(tag['name'])

    # Inject collected schemas
    spec['components']['schemas'].update(schemas)

    return spec


def create_openapi_endpoint(router_instance):
    """Create an endpoint that serves the OpenAPI JSON specification."""
    async def openapi_endpoint(_request: Request):
        return JSONResponse(generate_openapi_spec(router_instance))
    return openapi_endpoint


def create_redoc_endpoint(router_instance, openapi_url: str):
    """Create an endpoint that serves ReDoc documentation UI."""
    async def redoc_endpoint(_request: Request):
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{router_instance.title} - ReDoc</title>
            <meta charset="utf-8"/>
        </head>
        <body>
            <redoc spec-url='{openapi_url}'></redoc>
            <script src="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"></script>
        </body>
        </html>
        """
        return HTMLResponse(html)
    return redoc_endpoint


def create_swagger_endpoint(router_instance, openapi_url: str):
    """Create an endpoint that serves Swagger UI documentation."""
    async def swagger_endpoint(_request: Request):
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{router_instance.title} - Swagger UI</title>
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
    return swagger_endpoint


def create_rapidoc_endpoint(router_instance, openapi_url: str):
    """Create an endpoint that serves RapiDoc documentation UI."""
    async def rapidoc_endpoint(_request: Request):
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{router_instance.title} - RapiDoc</title>
            <script type="module" src="https://unpkg.com/rapidoc/dist/rapidoc-min.js"></script>
        </head>
        <body>
            <rapi-doc spec-url="{openapi_url}" theme="dark" show-header="true" render-style="read"></rapi-doc>
        </body>
        </html>
        """
        return HTMLResponse(html)
    return rapidoc_endpoint
