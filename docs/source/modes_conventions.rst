Project Modes and Conventions
=============================

Tatami supports two main approaches to building applications: **Explicit Mode** and **Convention Mode**.
You can choose either based on your needs, or even mix them in the same project.

.. contents::
   :local:
   :depth: 1

Explicit Mode
-------------

In Explicit Mode, you manually declare and register all components such as routers, middleware, and static assets.
This gives you full control over the application behavior and structure.

**Manual Router Registration:**

.. code-block:: python

   from tatami import BaseRouter, router, get, post
   from pydantic import BaseModel

   class User(BaseModel):
       name: str
       age: int

   class Users(router('/users')):
       @get('/{user_id}')
       def get_user(self, user_id: int):
           return {"id": user_id, "name": "Alice"}
       
       @post('/')
       def create_user(self, user: User):
           return {"created": user.name}

   # Manual assembly
   app = BaseRouter(title="My API", version="1.0.0")
   app.include_router(Users())
   
   # Run manually
   if __name__ == "__main__":
       app.run(host="0.0.0.0", port=8000)

In this mode, you are responsible for:

- Declaring routes using decorators (`@get`, `@post`, etc.)
- Manually registering routers with `app.include_router()`
- Setting up static file serving and other configuration
- Managing the application lifecycle

This mode is ideal when you want full transparency, fine-grained control, or non-standard project structures.

Convention Mode
---------------

In Convention Mode, the application is automatically assembled by analyzing your project’s directory layout and class names.
Tatami will scan for known components and register them automatically.

By default, Tatami looks for the following folders in your project:

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - Folder
     - Purpose
   * - ``routers/``
     - Classes are treated as routers, with methods mapped to endpoints
   * - ``services/``
     - Classes are automatically registered as injectable services
   * - ``repositories/``
     - Classes are registered as repositories and can be injected
   * - ``middleware/``
     - Middleware classes or callables are registered globally
   * - ``templates/``
     - Template files are auto-configured for rendering
   * - ``static/``
     - Static files are automatically served under ``/static/``

Example — Convention-Based Router:

.. code-block:: python

   # File: myapp/routers/users.py

   class Users:
       def get_user_by_id(self, user_id: int):
           ...

This will result in:

- A router mounted at ``/users``
- An endpoint registered at ``GET /users/{user_id}``

Example — Convention-Based Service:

.. code-block:: python

   # File: myapp/services/user_service.py

   class UserService:
       def get_user(self, user_id: int):
           ...

This service can be injected into endpoints or other services simply by using type annotations:

.. code-block:: python

   def some_endpoint(service: UserService):
       ...

Comparison Table
----------------

+-------------------+---------------------+------------------------+
| Feature           | Explicit Mode       | Convention Mode        |
+===================+=====================+========================+
| Control           | Full                | Automatic              |
+-------------------+---------------------+------------------------+
| Setup Required    | Manual wiring       | Just file/class layout |
+-------------------+---------------------+------------------------+
| Routing           | Decorators          | Folder/Class names     |
+-------------------+---------------------+------------------------+
| Services & DI     | Manual registration | Type-based injection   |
+-------------------+---------------------+------------------------+
| Middleware        | Manual              | Auto-loaded from file  |
+-------------------+---------------------+------------------------+
| Templates/Static  | Manual mounting     | Automatic              |
+-------------------+---------------------+------------------------+

Guidelines
----------

- Use **Convention Mode** with `tatami run` to build apps quickly with minimal boilerplate.
- Use **Explicit Mode** when you need full flexibility or when building libraries.
- You can mix both: use explicit routers within a convention-based project structure.

.. note::

   Convention Mode currently supports automatic router discovery and static file serving.
   Features like dependency injection, middleware auto-loading, and template rendering 
   are planned for future releases.
