Getting Started 🚀
==================

How to Install 🛠️
------------------

You can install Tatami either from PyPI or directly from the source. 

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

Quick Start with CLI
--------------------------

The fastest way to get started is using the Tatami CLI:

.. code-block:: bash

   # Create a new project
   tatami create myapp

   # Run your project
   tatami run myapp

This creates a project structure like:

.. code-block::

   myapp/
   ├── config.yaml
   ├── config-dev.yaml
   ├── README.md
   ├── favicon.ico
   ├── routers/
   ├── middleware/
   ├── mounts/
   ├── static/
   └── templates/

Your app will be available at `http://localhost:8000` with documentation at `/docs/swagger`.

Example App 🍱
--------------

Here's a simple example using decorators:

.. code-block:: python

   # routers/items.py
   from tatami import router, get, post
   from pydantic import BaseModel

   class Item(BaseModel):
       name: str
       value: int

   class Items(router("/items")):
       @get("/{item_id}")
       def get_item(self, item_id: str):
           return {"id": item_id, "name": "Example Item"}

       @post("/")
       def create_item(self, item: Item):
           return {"created": item.name, "value": item.value}

Or using convention-based routing:

.. code-block:: python

   # routers/users.py  
   from pydantic import BaseModel

   class User(BaseModel):
       name: str
       age: int

   class Users:
       def get_users(self):
           """List all users"""
           return [{"id": 1, "name": "Alice"}]
       
       def post_user(self, user: User):
           """Create a new user"""
           return {"message": f"Created {user.name}"}
       
       def get_user_by_id(self, user_id: int):
           """Get a specific user"""
           return {"id": user_id, "name": "Alice"}

This automatically creates endpoints:
- GET /users/ 
- POST /users/
- GET /users/{user_id}

🧭 OpenAPI & Docs
------------------

Tatami automatically gives you documentation endpoints out of the box:

- ``/openapi.json`` - the raw OpenAPI spec
- ``/docs/swagger`` - Swagger UI (interactive docs)
- ``/docs/redoc`` - ReDoc (clean docs view)
- ``/docs/rapidoc`` - RapiDoc (with a dark theme!)

Documentation is generated from your docstrings, type hints, and Pydantic models.

💡 Tip: You can disable or customize these routes when calling ``run()`` if needed.
