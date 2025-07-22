Getting Started 🚀
==================

How to Install 🛠️
------------------

You can install Tatami either from PyPI or directly from the source. Either way, keep in mind:

.. warning::

   Tatami is still **experimental** and **not production ready**. Even the PyPI version is subject to breaking changes at any time. You've been warned! ⚠️

**Install from PyPI** (recommended for playing around):

.. code-block:: bash

   pip install tatami

**Install the latest dev version** (if you're hacking on it or want the newest stuff):

.. code-block:: bash

   git clone https://github.com/ibonn/tatami.git
   cd tatami
   pip install -e .

This installs Tatami in editable mode so any changes to the source are immediately reflected when running your app.

Example App 🍱
--------------

Here's a super simple example to get you up and running with Tatami:

.. code-block:: python

   from tatami import Tatami, get, post, router
   from pydantic import BaseModel
   from starlette.responses import JSONResponse

   class Item(BaseModel):
       name: str
       value: int

   class ItemRouter(router("/items")):
       @get("/{item_id}")
       def get_item(self, item_id: str):
           return {"id": item_id}

       @post("/", response_type=JSONResponse)
       def create_item(self, item: Item):
           return {"created": item.name}

   app = Tatami(title="My Cool API")
   app.include_router(ItemRouter())

   if __name__ == "__main__":
       from tatami import run
       run(app)

🧭 OpenAPI & Docs
------------------

Tatami automatically gives you some nice documentation endpoints out of the box — no config needed:

- ``/openapi.json`` - the raw OpenAPI spec
- ``/docs/swagger`` - Swagger UI (interactive docs)
- ``/docs/redoc`` - ReDoc (clean docs view)
- ``/docs/rapidoc`` - RapiDoc (with a dark theme!)

Pop open one of those in your browser and enjoy!

💡 Tip: You can disable or customize these routes when calling ``run()`` if needed.
