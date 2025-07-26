![Tatami Logo](https://raw.githubusercontent.com/ibonn/tatami/refs/heads/main/images/tatami-logo.png)

![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/ibonn/tatami/pypi-publish.yml?style=flat-square)
![Read the Docs](https://img.shields.io/readthedocs/tatami-framework?style=flat-square)
![PyPI - Downloads](https://img.shields.io/pypi/dm/tatami?style=flat-square)
![PyPI - Version](https://img.shields.io/pypi/v/tatami?style=flat-square)
![Zen of Python - Compliance](https://img.shields.io/badge/Zen_of_Python-91%25_compliant-yellow?logo=python&logoColor=white&style=flat-square)


---

**The clean, modular Python web floorplan.**

Tatami is a minimal, convention-powered web framework that builds your application from the ground up — guided by your directory structure, not boilerplate or ceremony.

Like traditional *tatami* mats that structure a Japanese room, Tatami lets you define the shape and flow of your web app naturally, simply by laying things out.

---

## ✨ Features

- 🔁 **Automatic routing** from file and folder structure
- 📦 **Service injection** via convention
- 🧩 **Auto-loaded middleware**, templates, and static assets
- 📖 **Live OpenAPI docs** (ReDoc, Swagger, RapiDoc)
- 🧠 **Auto-generated endpoint documentation** from docstrings and README
- ⚡ **Zero-config startup** — just run your app directory

---

## 🚀 Quick Start

```bash
pip install tatami
```

**Create a new project:**
```bash
tatami create myproject
```

**Run your project:**
```bash
tatami run myproject
```

Your API will be available at `http://localhost:8000` with automatic docs at `/docs/swagger`.

## 🧠 Philosophy

Tatami is designed for:

* Structure-first design: Routes and services emerge from file layout.
* Simplicity: Eliminate configuration and glue code.
* Alignment: Your docs, code, and architecture reflect each other.

It's like FastAPI and Flask had a minimalist, Spring Boot-inspired child.

## 📚 Documentation

* 🚀 [Getting Started](https://tatami-framework.readthedocs.io/en/latest/getting_started.html)
* 🎛️ [CLI Usage](https://tatami-framework.readthedocs.io/en/latest/the_cli.html)
* 🧠 [Core Concepts](https://tatami-framework.readthedocs.io/en/latest/concepts.html)
* 📖 [API Reference](https://tatami-framework.readthedocs.io/en/latest/api/tatami.html)

**Built-in documentation is served automatically:**
- `/openapi.json` - OpenAPI specification
- `/docs/swagger` - Swagger UI
- `/docs/redoc` - ReDoc
- `/docs/rapidoc` - RapiDoc

## 🔌 Example

**Using decorators (recommended):**
```python
from tatami import get, post, router
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int

class Users(router('/users')):
    @get('/')
    def list_users(self):
        """Returns all users in the system."""
        return [{"id": 1, "name": "Alice", "age": 30}]

    @post('/')
    def create_user(self, user: User):
        """Creates a new user."""
        return {"message": f"Created user {user.name}"}

    @get('/{user_id}')
    def get_user(self, user_id: int):
        """Get a specific user by ID."""
        return {"id": user_id, "name": "Alice", "age": 30}
```

**Using convention-based routing:**
```python
# In routers/users.py
class Users:
    def get_users(self):
        """List all users"""
        return [{"id": 1, "name": "Alice"}]
    
    def post_user(self, user: User):
        """Create a new user"""
        return {"created": user.name}
```

This automatically creates:
* GET /users/
* POST /users/
* GET /users/{user_id}

...with full OpenAPI schemas generated automatically.

## 🌱 Still Early

Tatami is experimental. Expect breaking changes, rapid iteration, and exciting ideas.

Contributions, feedback, and issue reports are more than welcome.