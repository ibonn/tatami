Implementation Status 🚧
========================

This page tracks what's currently implemented in Tatami vs. what's planned for future releases.

Current Version: ``0.0.1-pre.1``

✅ Implemented Features
-----------------------

**Core Routing:**
- ✅ `BaseRouter` class for manual application assembly
- ✅ `router()` decorator for creating router classes  
- ✅ HTTP method decorators: `@get`, `@post`, `@put`, `@patch`, `@delete`, `@head`, `@options`
- ✅ Path parameters with type hints
- ✅ Request body parsing with Pydantic models
- ✅ Automatic response wrapping

**Convention-Based Routing:**
- ✅ `ConventionRouter` for method-name-based routing
- ✅ Method name patterns: `get_users()`, `post_user()`, `get_user_by_id()`
- ✅ Automatic HTTP verb mapping (`get_*` → GET, `post_*` → POST, etc.)
- ✅ Path parameter extraction from method signatures

**OpenAPI Documentation:**
- ✅ Automatic OpenAPI spec generation
- ✅ Swagger UI at `/docs/swagger`
- ✅ ReDoc at `/docs/redoc`  
- ✅ RapiDoc at `/docs/rapidoc`
- ✅ Raw spec at `/openapi.json`
- ✅ Docstring integration for endpoint descriptions
- ✅ Pydantic model schema generation

**CLI Tools:**
- ✅ `tatami create` for project scaffolding
- ✅ `tatami run` for convention-based execution
- ✅ Configuration mode support (`--mode dev`)
- ✅ Verbosity levels and logging
- ✅ Basic project structure creation

**Static Assets:**
- ✅ Static file serving from `static/` directory
- ✅ Automatic favicon handling
- ✅ Custom favicon support

**Configuration:**
- ✅ YAML configuration files
- ✅ Environment variable substitution in config
- ✅ Multi-mode configuration (`config-dev.yaml`, etc.)

🚧 Planned Features
-------------------

**Dependency Injection:**
- 🚧 `@inject` decorator
- 🚧 Automatic service discovery from `services/` directory  
- 🚧 Type-based dependency resolution
- 🚧 Service lifecycle management (singleton, per-request, transient)

**Middleware:**
- 🚧 Automatic middleware loading from `middleware/` directory
- 🚧 Middleware dependency injection
- 🚧 Built-in middleware for common patterns

**Templates:**
- 🚧 Jinja2 template integration
- 🚧 Template auto-discovery from `templates/` directory  
- 🚧 Template response helpers

**Advanced Features:**
- 🚧 Sub-application mounting from `mounts/` directory
- 🚧 Database integration and ORM support
- 🚧 Authentication and authorization helpers
- 🚧 WebSocket support
- 🚧 Background task support
- 🚧 Plugin system

**CLI Enhancements:**
- 🚧 `tatami doctor` for project diagnostics
- 🚧 Template-based project creation
- 🚧 Development server with auto-reload
- 🚧 Database migration commands

**Developer Experience:**
- 🚧 Type checking improvements
- 🚧 Better error messages and debugging
- 🚧 IDE integration and language server support
- 🚧 Testing utilities and fixtures

⚠️ Breaking Changes Expected
----------------------------

Since Tatami is in pre-release (version 0.0.1-pre.1), expect breaking changes in:

- API signatures and import paths
- Configuration file formats  
- CLI command structure
- Convention patterns and naming

We'll document breaking changes in release notes as we approach version 1.0.

🤝 Contributing
---------------

Want to help implement these features? Check out the GitHub repository and look for issues labeled "help wanted" or "good first issue".

The framework is designed to be modular, so many features can be implemented independently.
