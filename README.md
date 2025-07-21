![Tatami Logo](https://raw.githubusercontent.com/ibonn/tatami/refs/heads/main/images/tatami-logo.png)

![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/ibonn/tatami/tests?style=flat-square)
![PyPI - Downloads](https://img.shields.io/pypi/dm/tatami?style=flat-square)
![PyPI - Version](https://img.shields.io/pypi/v/tatami?style=flat-square)


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

## 🧠 Philosophy

Tatami is designed for:

* Structure-first design: Routes and services emerge from file layout.
* Simplicity: Eliminate configuration and glue code.
* Alignment: Your docs, code, and architecture reflect each other.

It’s like FastAPI and Flask had a minimalist, Spring Boot-inspired child.

## 📚 Documentation

* 📖 Getting Started
* 🔧 Project Structure
* 🧪 Testing
* 💡 Extending Tatami

Docs are served by default at `/docs/swagger` (Swagger) or `/docs/redoc` (ReDoc) or `/docs/rapidoc` (RapiDoc).

## 🔌 Example
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
        ...

    @post('/')
    def create_user(self, user: User):
        """Creates a new user."""
        ...
```
This defines two routes:

* GET /users/
* POST /users/

...and auto-documents them with full OpenAPI schemas. For a fully featured example, check the [Tatami Pet Store]()

## 🌱 Still Early

Tatami is experimental. Expect breaking changes, rapid iteration, and exciting ideas.

Contributions, feedback, and issue reports are more than welcome.