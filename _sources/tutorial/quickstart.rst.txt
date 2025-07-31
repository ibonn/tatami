Quickstart Guide 🚀
===================

Welcome to Tatami! This guide will get you from zero to a working API in just a few minutes.

What You'll Build
-----------------

By the end of this quickstart, you'll have:

- A working Tatami API with multiple endpoints
- Automatic OpenAPI documentation  
- A clean, organized project structure
- Knowledge of Tatami's core concepts

Installation
------------

First, let's install Tatami:

.. code-block:: bash

   pip install tatami

.. note::
   **Requirements**: Python 3.8+ is required. Tatami is built on Starlette and includes Uvicorn for serving.

Your First Tatami Project
-------------------------

Let's create a new project using the CLI:

.. code-block:: bash

   tatami create my-first-api
   cd my-first-api

This creates a project structure like this:

.. code-block::

   my-first-api/
   ├── config.yaml          # Configuration file
   ├── README.md            # Project documentation
   ├── favicon.ico          # Your API's favicon
   ├── routers/             # API route definitions (this is where the magic happens!)
   ├── services/            # Business logic and data access
   ├── middleware/          # Request/response processing
   ├── static/              # Static files (CSS, JS, images)
   └── templates/           # HTML templates

Let's Create Our First Router
-----------------------------

Create a new file `routers/tasks.py`:

.. code-block:: python

   # routers/tasks.py
   from tatami import router, get, post, put, delete
   from pydantic import BaseModel
   from typing import List

   class Task(BaseModel):
       title: str
       description: str = ""
       completed: bool = False

   class Tasks(router('/tasks')):
       """Task management API"""
       
       def __init__(self):
           super().__init__()
           # Simple in-memory storage for this example
           self.tasks = [
               {"id": 1, "title": "Learn Tatami", "completed": False},
               {"id": 2, "title": "Build awesome API", "completed": False}
           ]
           self.next_id = 3
       
       @get
       def list_tasks(self) -> List[dict]:
           """Get all tasks"""
           return self.tasks
       
       @get('/{task_id}')
       def get_task(self, task_id: int) -> dict:
           """Get a specific task by ID"""
           task = next((t for t in self.tasks if t["id"] == task_id), None)
           if not task:
               return {"error": "Task not found"}, 404
           return task
       
       @post('/')
       def create_task(self, task: Task) -> dict:
           """Create a new task"""
           new_task = {
               "id": self.next_id,
               "title": task.title,
               "description": task.description,
               "completed": task.completed
           }
           self.tasks.append(new_task)
           self.next_id += 1
           return new_task
       
       @put('/{task_id}')
       def update_task(self, task_id: int, task: Task) -> dict:
           """Update an existing task"""
           existing_task = next((t for t in self.tasks if t["id"] == task_id), None)
           if not existing_task:
               return {"error": "Task not found"}, 404
           
           existing_task.update({
               "title": task.title,
               "description": task.description,
               "completed": task.completed
           })
           return existing_task
       
       @delete('/{task_id}')
       def delete_task(self, task_id: int) -> dict:
           """Delete a task"""
           task = next((t for t in self.tasks if t["id"] == task_id), None)
           if not task:
               return {"error": "Task not found"}, 404
           
           self.tasks.remove(task)
           return {"message": "Task deleted successfully"}

Let's Run It!
-------------

Now run your API:

.. code-block:: bash

   tatami run .

You should see output like:

.. code-block::

   🌱 Tatami 0.0.1-pre.1
   Running app . on http://localhost:8000
        • Config: config.yaml
        • Routers: 1 discovered
        • Static files: static/
        • Templates: templates/
        • Middleware: 0 loaded
   Run tatami doctor "." for a more detailed analysis 🩺

Explore Your API
----------------

Open your browser and visit:

� **Documentation Portal**: http://localhost:8000/docs/

This landing page provides links to all available documentation formats.

�📊 **Interactive API Documentation**: http://localhost:8000/docs/swagger

You'll see beautiful, interactive documentation for your API! Try out the endpoints:

- **GET** `/tasks` - List all tasks
- **POST** `/tasks` - Create a new task
- **GET** `/tasks/{task_id}` - Get a specific task
- **PUT** `/tasks/{task_id}` - Update a task
- **DELETE** `/tasks/{task_id}` - Delete a task

Test Your API
-------------

Let's test our API using curl or Python requests:

.. code-block:: bash

   # Get all tasks
   curl http://localhost:8000/tasks

   # Create a new task
   curl -X POST http://localhost:8000/tasks \
        -H "Content-Type: application/json" \
        -d '{"title": "Test Tatami API", "description": "This is so easy!"}'

   # Get a specific task
   curl http://localhost:8000/tasks/1

What Just Happened? ✨
----------------------

In just a few minutes, you've:

1. ✅ **Created a project** with `tatami create`
2. ✅ **Defined a router** using class-based routing with `router('/tasks')`
3. ✅ **Added endpoints** using decorators like `@get`, `@post`, `@put`, `@delete`
4. ✅ **Used Pydantic models** for request/response validation
5. ✅ **Got automatic OpenAPI docs** for free
6. ✅ **Ran the API** with `tatami run`

Key Concepts Learned
--------------------

🧱 **Class-based Routers**: Each router is a class that groups related endpoints

🎯 **Explicit Decorators**: `@get`, `@post`, etc. make your API crystal clear

📋 **Pydantic Models**: Automatic validation and documentation for request/response data

🚀 **CLI Tools**: `tatami create` and `tatami run` for rapid development

📚 **Auto Documentation**: OpenAPI/Swagger docs generated automatically

What's Next?
------------

Now that you've got the basics down, you can:

- Learn more about project structure and conventions in the next tutorial
- Dive into routing guide for advanced routing patterns
- Explore working with data for database integration
- Check out dependency injection for better code organization

Ready to build something amazing? Let's keep going! 🎯
