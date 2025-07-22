Conventions Over Configuration 🧭
================================

Tatami tries to stay out of your way. Instead of asking you to configure everything with long YAML files or massive Python settings modules, it leans into the idea of **“convention over configuration.”**

That means: if you follow some simple patterns, Tatami will Just Work™ — no setup required. Of course, you can override stuff if needed, but the goal is to make the default path the easiest one.

Project Structure 📁
--------------------

Here's a typical (minimal) project layout that Tatami understands:

.. code-block::

   myapi/
   ├── app.py              # Your main app file — must define a Tatami instance
   ├── items.py            # A module containing a router
   └── models.py           # (Optional) Pydantic models

By default, you'd define your app in `app.py` like this:

.. code-block:: python

   from tatami import Tatami
   from items import ItemsRouter

   app = Tatami(title="My API")
   app.include_router(ItemsRouter())

Then in `items.py`:

.. code-block:: python

   from tatami import router, get
   from starlette.responses import JSONResponse

   class ItemsRouter(router("/items")):
       @get("/{item_id}", response_type=JSONResponse)
       def show(self, item_id: str):
           return {"id": item_id}

Naming Things
-------------

The framework assumes:

- Files like `items.py` define routers related to that domain.
- Classes like `ItemsRouter` will follow the `router("/items")` convention (URL path matches file/module name).
- Endpoints use HTTP method decorators (`@get`, `@post`, etc.) — no need to register them manually.

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
