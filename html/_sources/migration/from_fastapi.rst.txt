Migrating from FastAPI ⚡➡️🎋
===========================

This guide helps FastAPI developers transition to Tatami, highlighting the similarities and unique advantages of Tatami's approach.

Why Consider Tatami?
--------------------

As a FastAPI developer, you'll appreciate Tatami's:

- ✅ **Similar philosophy** - Type hints and automatic validation  
- ✅ **Better organization** - Class-based routers group related endpoints  
- ✅ **Cleaner structure** - Convention-based project organization  
- ✅ **Less boilerplate** - Smart defaults reduce configuration  
- ✅ **Explicit routing** - Clear, obvious API definitions  
- ✅ **Modular design** - Built-in separation of concerns  

Key Similarities
----------------

Both frameworks share:

- **ASGI-based** for async support
- **Pydantic integration** for data validation
- **Automatic OpenAPI** documentation generation
- **Type hint support** throughout
- **Modern Python patterns** (3.8+)

Key Differences
---------------

.. list-table:: FastAPI vs Tatami Comparison
   :header-rows: 1

   * - Feature
     - FastAPI
     - Tatami
   * - **Routing Style**
     - Function decorators
     - Class-based routers
   * - **Project Structure**
     - Flexible (manual setup)
     - Convention-based discovery
   * - **Organization**
     - Single file or manual modules
     - Clear separation by design
   * - **Dependency Injection**
     - Manual Depends() everywhere
     - Auto-discovery and injection
   * - **Configuration**
     - Code-based or manual
     - YAML-based with modes

Basic FastAPI to Tatami Translation
-----------------------------------

FastAPI App Structure
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # FastAPI main.py
   from fastapi import FastAPI, Depends, HTTPException
   from pydantic import BaseModel
   from typing import List
   
   app = FastAPI(title="My API")
   
   class User(BaseModel):
       name: str
       email: str
   
   class UserCreate(BaseModel):
       name: str
       email: str
   
   # In-memory storage
   users_db = []
   
   @app.get("/users", response_model=List[User])
   def get_users():
       return users_db
   
   @app.post("/users", response_model=User)
   def create_user(user: UserCreate):
       new_user = User(**user.dict())
       users_db.append(new_user)
       return new_user
   
   @app.get("/users/{user_id}", response_model=User)
   def get_user(user_id: int):
       if user_id >= len(users_db):
           raise HTTPException(status_code=404, detail="User not found")
       return users_db[user_id]

Equivalent Tatami Code
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # routers/users.py
   from tatami import router, get, post
   from pydantic import BaseModel
   from typing import List
   
   class User(BaseModel):
       name: str
       email: str
   
   class UserCreate(BaseModel):
       name: str
       email: str
   
   class Users(router('/users')):
       """User management endpoints"""
       
       def __init__(self):
           super().__init__()
           self.users_db = []
       
       @get('/')
       def get_users(self) -> List[User]:
           """Get all users"""
           return self.users_db
       
       @post('/')
       def create_user(self, user: UserCreate) -> User:
           """Create a new user"""
           new_user = User(**user.dict())
           self.users_db.append(new_user)
           return new_user
       
       @get('/{user_id}')
       def get_user(self, user_id: int) -> User:
           """Get user by ID"""
           if user_id >= len(self.users_db):
               return {'error': 'User not found'}, 404
           return self.users_db[user_id]

**Key improvements:**
- ✅ Related endpoints grouped in a class
- ✅ Self-contained state management
- ✅ Auto-discovery when using `tatami run`
- ✅ Cleaner project organization

Migration Strategies
--------------------

1. Incremental Migration
^^^^^^^^^^^^^^^^^^^^^^^^

Migrate FastAPI routers one by one:

**Step 1: Convert a FastAPI router to Tatami**

.. code-block:: python

   # FastAPI router
   from fastapi import APIRouter
   
   router = APIRouter(prefix="/posts")
   
   @router.get("/")
   def get_posts():
       return []
   
   @router.post("/")
   def create_post(post: PostCreate):
       return {"message": "Post created"}

.. code-block:: python

   # Tatami router
   from tatami import router, get, post
   
   class Posts(router('/posts')):
       @get('/')
       def get_posts(self):
           return []
       
       @post('/')
       def create_post(self, post: PostCreate):
           return {"message": "Post created"}

**Step 2: Migrate Dependencies**

.. code-block:: python

   # FastAPI dependencies
   from fastapi import Depends
   
   def get_db():
       db = SessionLocal()
       try:
           yield db
       finally:
           db.close()
   
   @app.get("/users")
   def get_users(db: Session = Depends(get_db)):
       return crud.get_users(db)

.. code-block:: python

   # Tatami with service injection
   class Users(router('/users')):
       def __init__(self, user_service: UserService):
           super().__init__()
           self.user_service = user_service
       
       @get('/')
       def get_users(self):
           return self.user_service.get_all()

2. Complete Rewrite
^^^^^^^^^^^^^^^^^^^

For clean architecture, consider a complete rewrite:

.. code-block:: bash

   # Create new Tatami project
   tatami create my-migrated-api
   cd my-migrated-api
   
   # Convert FastAPI routes to Tatami routers
   # Organize code into services and repositories
   # Update configuration to use YAML

Common Migration Patterns
-------------------------

FastAPI Path Parameters → Tatami Path Parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # FastAPI
   @app.get("/users/{user_id}/posts/{post_id}")
   def get_user_post(user_id: int, post_id: int):
       return {"user_id": user_id, "post_id": post_id}

.. code-block:: python

   # Tatami
   class UserPosts(router('/users/{user_id}/posts')):
       @get('/{post_id}')
       def get_user_post(self, user_id: int, post_id: int):
           return {"user_id": user_id, "post_id": post_id}

FastAPI Query Parameters → Tatami Query Parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # FastAPI
   from fastapi import Query
   
   @app.get("/search")
   def search(
       q: str = Query(...),
       page: int = Query(1),
       limit: int = Query(10)
   ):
       return {"query": q, "page": page, "limit": limit}

.. code-block:: python

   # Tatami
   from tatami.param import Query
   
   class Search(router('/search')):
       @get('/')
       def search(
           self,
           q: str = Query(...),
           page: int = Query(1),
           limit: int = Query(10)
       ):
           return {"query": q, "page": page, "limit": limit}

FastAPI Dependencies → Tatami Dependency Injection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # FastAPI
   from fastapi import Depends
   
   def get_user_service():
       return UserService()
   
   def get_email_service():
       return EmailService()
   
   @app.post("/users")
   def create_user(
       user: UserCreate,
       user_service: UserService = Depends(get_user_service),
       email_service: EmailService = Depends(get_email_service)
   ):
       new_user = user_service.create(user)
       email_service.send_welcome(new_user.email)
       return new_user

.. code-block:: python

   # Tatami
   class Users(router('/users')):
       def __init__(self, user_service: UserService, email_service: EmailService):
           super().__init__()
           self.user_service = user_service
           self.email_service = email_service
       
       @post('/')
       def create_user(self, user: UserCreate):
           new_user = self.user_service.create(user)
           self.email_service.send_welcome(new_user.email)
           return new_user

FastAPI Middleware → Tatami Middleware
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # FastAPI
   from fastapi.middleware.cors import CORSMiddleware
   
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )

.. code-block:: python

   # Tatami
   # middleware/cors_middleware.py
   from starlette.middleware.cors import CORSMiddleware
   
   # Auto-discovered and applied globally

FastAPI Background Tasks → Tatami Services
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # FastAPI
   from fastapi import BackgroundTasks
   
   def send_email(email: str, message: str):
       # Send email logic
       pass
   
   @app.post("/send-email")
   def send_email_endpoint(
       email: str,
       message: str,
       background_tasks: BackgroundTasks
   ):
       background_tasks.add_task(send_email, email, message)
       return {"message": "Email will be sent"}

.. code-block:: python

   # Tatami
   class Email(router('/email')):
       def __init__(self, email_service: EmailService):
           super().__init__()
           self.email_service = email_service
       
       @post('/send')
       async def send_email(self, email: str, message: str):
           # Use asyncio or celery for background processing
           await self.email_service.send_async(email, message)
           return {"message": "Email sent"}

Configuration Migration
-----------------------

FastAPI Settings
^^^^^^^^^^^^^^^^

.. code-block:: python

   # FastAPI settings.py
   from pydantic import BaseSettings
   
   class Settings(BaseSettings):
       app_name: str = "My API"
       database_url: str = "sqlite:///./app.db"
       secret_key: str
       
       class Config:
           env_file = ".env"
   
   settings = Settings()

Tatami Configuration
^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

   # config.yaml
   app:
     name: "My API"
     secret_key: "${SECRET_KEY}"
   
   database:
     url: "sqlite:///./app.db"

.. code-block:: yaml

   # config-dev.yaml
   database:
     url: "sqlite:///./dev.db"
   
   features:
     debug: true

Testing Migration
-----------------

FastAPI Testing
^^^^^^^^^^^^^^^

.. code-block:: python

   # FastAPI testing
   from fastapi.testclient import TestClient
   
   client = TestClient(app)
   
   def test_get_users():
       response = client.get("/users")
       assert response.status_code == 200
       assert response.json() == []

Tatami Testing
^^^^^^^^^^^^^^

.. code-block:: python

   # Tatami testing
   import httpx
   from tatami import BaseRouter
   
   def test_get_users():
       app = BaseRouter()
       app.include_router(Users())
       
       with httpx.Client(app=app, base_url="http://test") as client:
           response = client.get("/users")
           assert response.status_code == 200
           assert response.json() == []

Project Structure Comparison
----------------------------

FastAPI Project Structure
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block::

   fastapi-project/
   ├── main.py              # All routes or app setup
   ├── models.py            # Pydantic models
   ├── database.py          # Database setup
   ├── crud.py              # Database operations
   ├── dependencies.py      # Dependency functions
   ├── routers/             # Optional organization
   │   ├── users.py
   │   └── posts.py
   └── requirements.txt

Tatami Project Structure
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block::

   tatami-project/
   ├── config.yaml          # Configuration
   ├── routers/             # API endpoints (auto-discovered)
   │   ├── users.py
   │   └── posts.py
   ├── services/            # Business logic (auto-discovered)
   │   ├── user_service.py
   │   └── email_service.py
   ├── repositories/        # Data access (auto-discovered)
   │   └── user_repository.py
   ├── middleware/          # Middleware (auto-discovered)
   │   └── auth_middleware.py
   ├── static/              # Static files (auto-served)
   └── templates/           # Templates (auto-configured)

Advantages of Migration
-----------------------

Better Organization
^^^^^^^^^^^^^^^^^^^

FastAPI encourages but doesn't enforce good structure. Tatami provides it by default:

.. code-block:: python

   # FastAPI - everything in one file (common but not ideal)
   from fastapi import FastAPI
   
   app = FastAPI()
   
   # 50+ route definitions here...
   # Models scattered throughout...
   # Business logic mixed with HTTP concerns...

.. code-block:: python

   # Tatami - clear separation by convention
   # routers/users.py - HTTP concerns only
   # services/user_service.py - Business logic
   # repositories/user_repository.py - Data access

Reduced Boilerplate
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # FastAPI - manual dependency injection everywhere
   @app.get("/users")
   def get_users(
       user_service: UserService = Depends(get_user_service),
       email_service: EmailService = Depends(get_email_service)
   ):
       pass

.. code-block:: python

   # Tatami - inject once in constructor
   class Users(router('/users')):
       def __init__(self, user_service: UserService, email_service: EmailService):
           self.user_service = user_service
           self.email_service = email_service

Auto-Discovery
^^^^^^^^^^^^^^

.. code-block:: python

   # FastAPI - manual registration
   app.include_router(users_router)
   app.include_router(posts_router)
   app.include_router(auth_router)
   # ... manual setup for everything

.. code-block:: bash

   # Tatami - automatic discovery
   tatami run .  # Discovers everything automatically

Migration Gotchas
-----------------

1. Dependency Injection Differences
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

FastAPI uses function-level dependency injection:

.. code-block:: python

   # FastAPI
   @app.get("/users")
   def get_users(db: Session = Depends(get_db)):
       pass

Tatami uses constructor-level injection:

.. code-block:: python

   # Tatami
   class Users(router('/users')):
       def __init__(self, user_service: UserService):
           self.user_service = user_service

2. Response Models
^^^^^^^^^^^^^^^^^^

FastAPI uses `response_model` parameter:

.. code-block:: python

   # FastAPI
   @app.get("/users", response_model=List[User])
   def get_users():
       pass

Tatami uses return type hints:

.. code-block:: python

   # Tatami
   @get('/')
   def get_users(self) -> List[User]:
       pass

3. Exception Handling
^^^^^^^^^^^^^^^^^^^^^

FastAPI uses HTTPException:

.. code-block:: python

   # FastAPI
   from fastapi import HTTPException
   
   @app.get("/users/{user_id}")
   def get_user(user_id: int):
       if user_id not in users:
           raise HTTPException(status_code=404, detail="User not found")

Tatami uses tuple returns:

.. code-block:: python

   # Tatami
   @get('/{user_id}')
   def get_user(self, user_id: int):
       if user_id not in self.users:
           return {"error": "User not found"}, 404

Migration Checklist
-------------------

Before Migration
^^^^^^^^^^^^^^^^

- [ ] **Audit FastAPI app** - Catalog all routes, dependencies, middleware
- [ ] **Identify business logic** - What can be moved to services?
- [ ] **Review dependencies** - How are services currently injected?
- [ ] **Document current structure** - Understand existing organization

During Migration
^^^^^^^^^^^^^^^^

- [ ] **Create Tatami project** - `tatami create new-app`
- [ ] **Convert routes to routers** - Group related endpoints
- [ ] **Extract services** - Move business logic to service classes
- [ ] **Update dependencies** - Use constructor injection
- [ ] **Migrate configuration** - Convert to YAML format

After Migration
^^^^^^^^^^^^^^^

- [ ] **Test thoroughly** - Ensure all functionality works
- [ ] **Verify auto-discovery** - Check `tatami doctor`
- [ ] **Update deployment** - Use `tatami run` for serving
- [ ] **Document changes** - API docs are auto-generated

Why Make the Switch?
--------------------

While FastAPI is excellent, Tatami offers:

- 🏗️ **Better Architecture** - Enforced separation of concerns  
- 🔧 **Less Configuration** - Convention over configuration approach  
- 📁 **Cleaner Projects** - Organized structure from day one  
- 🚀 **Faster Development** - Auto-discovery reduces boilerplate  
- 🧪 **Better Testing** - Clear dependencies make mocking easier  

The migration effort pays off in maintainability and team productivity! 🎋
