Conventions Over Configuration 🧭
=================================

Tatami tries to stay out of your way. Instead of asking you to configure everything with long YAML files or massive Python settings modules, it leans into the idea of **“convention over configuration.”**

That means: if you follow some simple patterns, Tatami will Just Work™ — no setup required. Of course, you can override stuff if needed, but the goal is to make the default path the easiest one.

Project Structure 📁
--------------------

Tatami supports both manual setup and convention-based project structures:

**Convention-based structure (recommended):**

.. code-block::

   myapi/
   ├── config.yaml         # Main configuration
   ├── config-dev.yaml     # Development config (optional)
   ├── README.md           # Project description (used in OpenAPI docs)
   ├── favicon.ico         # Custom favicon (optional)
   ├── routers/            # Router classes and modules
   │   ├── users.py
   │   └── items.py
   ├── middleware/         # Middleware classes (planned)
   ├── static/             # Static files (served at /static)
   ├── templates/          # Template files (Jinja2, planned)
   └── mounts/             # Sub-applications (planned)

**Manual setup:**

.. code-block:: python

   from tatami import BaseRouter
   from routers.items import Items

   app = BaseRouter(title="My API")
   app.include_router(Items())
   app.run()

**Using CLI for convention-based projects:**

.. code-block:: bash

   tatami create myapi
   tatami run myapi

Router Examples
---------------

**Decorator-based routing:**

.. code-block:: python

   from tatami import router, get, post
   from pydantic import BaseModel

   class Item(BaseModel):
       name: str
       price: float

   class Items(router("/items")):
       @get("/{item_id}")
       def show(self, item_id: str):
           return {"id": item_id, "name": "Example Item"}
       
       @post("/")
       def create(self, item: Item):
           return {"created": item.name, "price": item.price}

**Convention-based routing:**

.. code-block:: python

   # File: routers/items.py
   from pydantic import BaseModel

   class Item(BaseModel):
       name: str
       price: float

   class Items:
       def get_items(self):
           """List all items"""
           return [{"id": 1, "name": "Example"}]
       
       def post_item(self, item: Item):
           """Create a new item"""
           return {"created": item.name}
       
       def get_item_by_id(self, item_id: int):
           """Get specific item"""
           return {"id": item_id, "name": "Example"}

Naming Things
-------------

**Decorator-based routing:**
- Use the `router("/path")` function to create a router class
- HTTP method decorators (`@get`, `@post`, `@put`, `@delete`, etc.) define endpoints
- Path parameters are extracted from function signatures

**Convention-based routing:**
- Class names determine the base route (e.g., `Items` -> `/items`)
- Method names follow the pattern: `{verb}_{resource}[_by_{param}]`
- Supported verbs: `get`, `post`, `put`, `patch`, `delete`, `head`, `options`
- Alternative verbs: `update` (PUT), `create`/`new` (POST), `remove` (DELETE)

Examples:
- `get_items()` -> `GET /items/`
- `post_item()` -> `POST /items/`  
- `get_item_by_id(item_id)` -> `GET /items/{item_id}`
- `update_user_by_email(email, user)` -> `PUT /users/{email}`

If you break these conventions, that's fine — but you'll need to wire things up explicitly. For example:

.. code-block:: python

   class Custom(router("/totally-custom")):
       ...

No magic there — you're in full control.

Why It Matters
--------------

This approach helps keep projects:

✅ Easy to read  
✅ Fast to navigate  
✅ Less boilerplate-y  
✅ Friendly for new contributors

We think the structure should describe the API — not the other way around.

Want to customize everything? You still can. But if you follow the defaults, you'll write less code and worry less about glue logic.

Routers
-------

In Tatami, routers are defined as classes. This might look a bit unusual at first, but it comes with some nice benefits:

- **Organization**: Each router is its own class, so it's easy to group related endpoints together.
- **Clarity**: You can immediately tell what paths and actions belong to each part of your API.
- **Reusability**: Since routers are classes, you can use inheritance or mixins to share logic between them.

Here's a basic example:

.. code-block:: python

   from tatami import router

   class HelloRouter(router('/hello')):
       pass

This sets up a router for the ``/hello`` path, but it doesn't do anything yet — we'll add some endpoints next.

Endpoints
---------

Each router can have one or more endpoints. Endpoints are just methods decorated with HTTP verbs like ``@get``, ``@post``, etc.

This structure helps keep your code tidy — instead of scattering route handlers all over the place, they're grouped logically under their parent router class.

Here's a more complete example:

.. code-block:: python

   from tatami import router, get, post, put

   class HelloRouter(router('/hello')):

       @get
       def index(self):
           return {'message': 'Hello from /hello'}

       @get('/greet')
       def greet(self):
           return {'message': 'Greetings from /hello/greet'}

       @post('/')
       def create(self):
           return {'message': 'You sent a POST request to /hello'}

       @put('/update')
       def update(self):
           return {'message': 'PUT request received at /hello/update'}

What's going on here?

- ``@get`` with no path handles ``GET /hello``
- ``@get('/greet')`` handles ``GET /hello/greet``
- ``@post('/')`` handles ``POST /hello``
- ``@put('/update')`` handles ``PUT /hello/update``

By organizing routes like this, you get a clean, readable, and maintainable API structure — especially as your app grows.
