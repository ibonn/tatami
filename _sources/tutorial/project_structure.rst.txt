Project Structure & Conventions 📁
===================================

Tatami uses smart conventions to organize your code, making projects easy to understand and maintain. This guide explains the project structure and how Tatami's convention-over-configuration approach works.

Why Project Structure Matters
-----------------------------

Good project structure:

- 🧭 **Guides developers** - New team members know where to find things
- 🔍 **Improves maintainability** - Related code stays together
- ⚡ **Enables automation** - Tatami can auto-discover components
- 🧪 **Simplifies testing** - Clear separation makes testing easier
- 📈 **Scales well** - Structure remains clean as projects grow

The Tatami Project Structure
----------------------------

When you run `tatami create myproject`, you get this structure:

.. code-block::

   myproject/
   ├── config.yaml          # 🔧 Main configuration
   ├── config-dev.yaml      # 🛠️ Development configuration
   ├── README.md            # 📖 Project documentation
   ├── favicon.ico          # 🎨 API favicon
   ├── routers/             # 🎯 HTTP endpoints and routing
   │   └── __init__.py
   ├── services/            # 🧠 Business logic layer
   │   └── __init__.py
   ├── middleware/          # 🔄 Request/response processing
   │   └── __init__.py
   ├── static/              # 📁 Static files (CSS, JS, images)
   ├── templates/           # 📄 HTML templates (Jinja2)
   └── mounts/              # 🗂️ Sub-applications

Let's explore each directory in detail.

Configuration Files
-------------------

config.yaml
^^^^^^^^^^^

The main configuration file. Tatami uses YAML for clean, readable config:

.. code-block:: yaml

   # config.yaml
   app:
     title: "My Amazing API"
     description: "A Tatami-powered API"
     version: "1.0.0"
   
   server:
     host: "0.0.0.0"
     port: 8000
   
   database:
     url: "sqlite:///./app.db"
   
   features:
     enable_docs: true
     enable_cors: false

config-dev.yaml
^^^^^^^^^^^^^^^

Development-specific overrides:

.. code-block:: yaml

   # config-dev.yaml
   server:
     host: "localhost"
     port: 8080
   
   database:
     url: "sqlite:///./dev.db"
   
   features:
     enable_cors: true
     debug: true

Use development config with:

.. code-block:: bash

   tatami run . --mode dev

The `routers/` Directory 🎯
----------------------------

This is where your API endpoints live. Each file becomes a router:

.. code-block::

   routers/
   ├── __init__.py          # Makes it a Python package
   ├── users.py             # User management endpoints
   ├── posts.py             # Blog post endpoints
   ├── auth.py              # Authentication endpoints
   └── admin/               # Admin endpoints (nested)
       ├── __init__.py
       ├── analytics.py
       └── settings.py

Router File Example
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # routers/users.py
   from tatami import router, get, post, put, delete
   from pydantic import BaseModel
   from services.user_service import UserService

   class User(BaseModel):
       name: str
       email: str

   class Users(router('/users')):
       """User management endpoints"""
       
       def __init__(self, user_service: UserService):
           super().__init__()
           self.user_service = user_service

       @get
       def list_users(self):
           """Get all users"""
           return self.user_service.get_all()

       @get('/{user_id}')
       def get_user(self, user_id: int):
           """Get user by ID"""
           return self.user_service.get_by_id(user_id)

       @post
       def create_user(self, user: User):
           """Create a new user"""
           return self.user_service.create(user)

Router Naming Conventions
^^^^^^^^^^^^^^^^^^^^^^^^^

- **File names** become route prefixes: `users.py` → `/users`
- **Class names** should match the file: `Users` class in `users.py`
- **Method names** are descriptive and use HTTP decorators

The `services/` Directory 🧠
-----------------------------

Services contain your business logic, separated from HTTP concerns:

.. code-block::

   services/
   ├── __init__.py
   ├── user_service.py      # User business logic
   ├── email_service.py     # Email sending logic
   ├── payment_service.py   # Payment processing
   └── data/               # Data access layer
       ├── __init__.py
       ├── user_repository.py
       └── post_repository.py

Service Example
^^^^^^^^^^^^^^^

.. code-block:: python

   # services/user_service.py
   from typing import List, Optional
   from tatami.di import injectable
   from services.data.user_repository import UserRepository
   from routers.models import User, UserCreate

   @injectable
   class UserService:
       """Business logic for user management"""
       
       def __init__(self, user_repo: UserRepository):
           self.user_repo = user_repo

       def create_user(self, user_data: UserCreate) -> User:
           # Business logic: validation, rules, etc.
           if self.user_repo.get_by_email(user_data.email):
               raise ValueError("Email already exists")
           
           # Create user
           return self.user_repo.create(user_data)

       def get_user_by_id(self, user_id: int) -> Optional[User]:
           return self.user_repo.get_by_id(user_id)

       def get_all_users(self) -> List[User]:
           return self.user_repo.get_all()

Auto-Discovery of Services
^^^^^^^^^^^^^^^^^^^^^^^^^^

Tatami automatically discovers and makes services available for dependency injection:

.. code-block:: python

   # This service is automatically available for injection
   from tatami.di import injectable
   
   @injectable
   class EmailService:
       def send_welcome_email(self, user_email: str):
           # Email sending logic
           pass

   # Use it in a router
   class Users(router('/users')):
       def __init__(self, email_service: EmailService):
           self.email_service = email_service

The `middleware/` Directory 🔄
-------------------------------

Middleware processes requests and responses:

.. code-block::

   middleware/
   ├── __init__.py
   ├── auth_middleware.py    # Authentication
   ├── cors_middleware.py    # CORS handling
   ├── logging_middleware.py # Request logging
   └── rate_limit_middleware.py # Rate limiting

Middleware Example
^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # middleware/auth_middleware.py
   from starlette.middleware.base import BaseHTTPMiddleware
   from starlette.requests import Request
   from starlette.responses import Response

   class AuthMiddleware(BaseHTTPMiddleware):
       async def dispatch(self, request: Request, call_next):
           # Check authentication
           auth_header = request.headers.get('Authorization')
           
           if not auth_header and request.url.path.startswith('/api/'):
               return Response("Unauthorized", status_code=401)
           
           # Process request
           response = await call_next(request)
           return response

The `static/` Directory 📁
---------------------------

Static files are automatically served at `/static`:

.. code-block::

   static/
   ├── css/
   │   ├── styles.css
   │   └── admin.css
   ├── js/
   │   ├── app.js
   │   └── utils.js
   ├── images/
   │   ├── logo.png
   │   └── favicon.ico
   └── docs/
       └── api_guide.pdf

Files are accessible at:
- `/static/css/styles.css`
- `/static/js/app.js`
- `/static/images/logo.png`

The `templates/` Directory 📄
------------------------------

HTML templates for server-side rendering:

.. code-block::

   templates/
   ├── base.html            # Base template
   ├── index.html           # Homepage
   ├── users/
   │   ├── list.html        # User list page
   │   └── detail.html      # User detail page
   ├── admin/
   │   ├── dashboard.html
   │   └── reports.html
   └── __tatami__/          # 🎋 Tatami system templates
       ├── docs_landing.html    # Custom docs landing page
       ├── swagger.html         # Custom Swagger UI
       └── redoc.html           # Custom ReDoc UI

Template Example
^^^^^^^^^^^^^^^^

.. code-block:: html

   <!-- templates/users/list.html -->
   <!DOCTYPE html>
   <html>
   <head>
       <title>Users - {{ app_name }}</title>
       <link rel="stylesheet" href="/static/css/styles.css">
   </head>
   <body>
       <h1>Users</h1>
       <ul>
       {% for user in users %}
           <li>{{ user.name }} ({{ user.email }})</li>
       {% endfor %}
       </ul>
   </body>

Customizing Tatami's Auto-Generated Pages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Tatami automatically provides several pages like documentation and API explorers. You can customize these by creating templates in the special `__tatami__/` directory:

**Automatic Docs Landing Page**

Tatami serves a landing page at `/docs/` that links to all available documentation. Customize it with:

.. code-block:: html

   <!-- templates/__tatami__/docs_landing.html -->
   <!DOCTYPE html>
   <html>
   <head>
       <title>{{ app_name }} API Documentation</title>
       <link rel="stylesheet" href="/static/css/docs.css">
   </head>
   <body>
       <div class="docs-container">
           <h1>{{ app_name }} API Documentation</h1>
           <p>Welcome to the {{ app_name }} API documentation portal.</p>
           
           <div class="docs-links">
               <a href="/docs/swagger" class="docs-link">
                   <h3>📊 Swagger UI</h3>
                   <p>Interactive API explorer with request/response examples</p>
               </a>
               
               <a href="/docs/redoc" class="docs-link">
                   <h3>📚 ReDoc</h3>
                   <p>Beautiful API documentation with detailed schemas</p>
               </a>
               
               <a href="/docs/openapi.json" class="docs-link">
                   <h3>📄 OpenAPI Spec</h3>
                   <p>Raw OpenAPI 3.0 specification in JSON format</p>
               </a>
           </div>
       </div>
   </body>
   </html>

**Custom Swagger/ReDoc Templates**

Override the default Swagger or ReDoc interfaces:

.. code-block:: html

   <!-- templates/__tatami__/swagger.html -->
   <!DOCTYPE html>
   <html>
   <head>
       <title>{{ app_name }} - Swagger UI</title>
       <!-- Your custom styling -->
       <link rel="stylesheet" href="/static/css/custom-swagger.css">
   </head>
   <body>
       <!-- Custom header -->
       <header class="api-header">
           <h1>{{ app_name }} API Explorer</h1>
       </header>
       
       <!-- Swagger UI will be injected here -->
       <div id="swagger-ui"></div>
       
       <!-- Custom footer -->
       <footer>© 2025 {{ app_name }}</footer>
   </body>
   </html>

Available Template Variables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In `__tatami__/` templates, you have access to:

- ``app_name`` - Your application name
- ``app_version`` - Application version  
- ``openapi_spec`` - The OpenAPI specification object
- ``base_url`` - Base URL of your API
- ``docs_url`` - URL to documentation landing page
   </html>

The `mounts/` Directory 🗂️
--------------------------

Mount sub-applications or external ASGI apps:

.. code-block::

   mounts/
   ├── admin_app.py         # Admin interface
   ├── docs_app.py          # Custom docs app
   └── legacy_app.py        # Legacy application

Mount Example
^^^^^^^^^^^^^

.. code-block:: python

   # mounts/admin_app.py
   from starlette.applications import Starlette
   from starlette.routing import Route
   from starlette.responses import JSONResponse

   async def admin_dashboard(request):
       return JSONResponse({"page": "admin dashboard"})

   # This gets mounted at /admin
   admin_app = Starlette(routes=[
       Route('/', admin_dashboard),
   ])

Convention-Based Auto-Discovery
-------------------------------

Tatami automatically discovers and registers:

📂 **Routers** (from `routers/`)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- Files with router classes are registered
- Nested directories create sub-routes
- Example: `routers/admin/users.py` → `/admin/users`

🧠 **Services** (from `services/`)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- Classes are available for dependency injection
- Automatic singleton management
- Constructor dependencies are resolved

🔄 **Middleware** (from `middleware/`)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- Middleware classes are registered globally
- Order can be controlled with naming (01_auth.py, 02_cors.py)

📁 **Static Files** (from `static/`)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- Automatically served at `/static`
- No configuration needed

📄 **Templates** (from `templates/`)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
- Jinja2 environment auto-configured
- Templates available in routers

Best Practices
--------------

🎯 Keep Routers Thin
^^^^^^^^^^^^^^^^^^^^^
Routers should handle HTTP concerns only:

.. code-block:: python

   # ✅ Good - thin router
   class Users(router('/users')):
       def __init__(self, user_service: UserService):
           self.user_service = user_service

       @post('/')
       def create_user(self, user: UserCreate):
           return self.user_service.create(user)

   # ❌ Bad - fat router
   class Users(router('/users')):
       @post('/')
       def create_user(self, user: UserCreate):
           # Don't put business logic here!
           if User.query.filter_by(email=user.email).first():
               raise ValueError("Email exists")
           # ... more business logic

🧠 Put Logic in Services
^^^^^^^^^^^^^^^^^^^^^^^^^
Services handle business rules and data access:

.. code-block:: python

   # ✅ Good - service handles business logic
   from tatami.di import injectable
   
   @injectable
   class UserService:
       def create_user(self, user_data: UserCreate):
           # Validation
           if self.user_exists(user_data.email):
               raise UserAlreadyExistsError()
           
           # Business rules
           user_data = self.apply_business_rules(user_data)
           
           # Data access
           return self.user_repo.create(user_data)

📋 Use Pydantic Models
^^^^^^^^^^^^^^^^^^^^^^^
Define clear data contracts:

.. code-block:: python

   # models.py or in router files
   class UserCreate(BaseModel):
       name: str = Field(min_length=1, max_length=100)
       email: EmailStr
       age: int = Field(ge=13, le=120)

   class UserResponse(BaseModel):
       id: int
       name: str
       email: str
       created_at: datetime

🔧 Configure Thoughtfully
^^^^^^^^^^^^^^^^^^^^^^^^^^
Keep configuration clean and environment-specific:

.. code-block:: yaml

   # config.yaml - production defaults
   database:
     pool_size: 20
     echo: false
   
   features:
     debug: false
     enable_profiling: false

   # config-dev.yaml - development overrides
   database:
     echo: true
   
   features:
     debug: true
     enable_profiling: true

Why This Structure Works
------------------------

🚀 **Rapid Development**
^^^^^^^^^^^^^^^^^^^^^^^^^
- No boilerplate configuration
- Auto-discovery reduces setup time
- Clear separation of concerns

🧭 **Easy Navigation**
^^^^^^^^^^^^^^^^^^^^^^^
- Predictable file locations
- Related code stays together
- New developers onboard quickly

🧪 **Testability**
^^^^^^^^^^^^^^^^^^^
- Services can be unit tested easily
- HTTP layer separated from business logic
- Dependency injection enables mocking

📈 **Scalability**
^^^^^^^^^^^^^^^^^^^
- Structure remains clean as projects grow
- Easy to split into microservices later
- Clear boundaries between components

Real-World Example
------------------

Here's how a real e-commerce API might be structured:

.. code-block::

   ecommerce-api/
   ├── config.yaml
   ├── routers/
   │   ├── products.py          # Product catalog
   │   ├── users.py             # User management
   │   ├── orders.py            # Order processing
   │   ├── payments.py          # Payment handling
   │   └── admin/
   │       ├── analytics.py     # Admin analytics
   │       └── inventory.py     # Inventory management
   ├── services/
   │   ├── product_service.py   # Product business logic
   │   ├── order_service.py     # Order processing
   │   ├── payment_service.py   # Payment integration
   │   ├── email_service.py     # Email notifications
   │   └── data/
   │       ├── product_repo.py  # Product data access
   │       └── order_repo.py    # Order data access
   ├── middleware/
   │   ├── auth_middleware.py   # Authentication
   │   ├── rate_limit.py        # Rate limiting
   │   └── request_logging.py   # Request logging
   ├── static/
   │   ├── css/
   │   └── js/
   └── templates/
       ├── emails/              # Email templates
       └── admin/               # Admin interface

This structure scales from small APIs to large applications while maintaining clarity and organization.

What's Next?
------------

Now that you understand Tatami's project structure, you're ready to:

- Learn advanced routing patterns and techniques
- Explore dependency injection for better code organization
- Dive into middleware development
- Master testing strategies for Tatami applications

The structure is your foundation - let's build something amazing on it! 🏗️
