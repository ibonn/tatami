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

