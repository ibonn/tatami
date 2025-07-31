Migrating from Flask 🍶➡️🎋
=========================

This guide helps Flask developers transition to Tatami, highlighting similarities and differences.

Why Migrate to Tatami?
----------------------

Coming from Flask, you'll love Tatami's:

- ✅ **Familiar Python patterns** - No magic, just clean code  
- ✅ **Better organization** - Class-based routers keep related endpoints together  
- ✅ **Built-in OpenAPI** - Automatic API documentation  
- ✅ **Type safety** - Full type hints with Pydantic validation  
- ✅ **Modern async support** - ASGI-based for better performance  
- ✅ **Convention over configuration** - Smart defaults, less boilerplate  

Key Differences
---------------

.. list-table:: Flask vs Tatami Comparison
   :header-rows: 1

   * - Feature
     - Flask
     - Tatami
   * - **Routing**
     - Function decorators
     - Class-based routers
   * - **Validation**
     - Manual/Flask-WTF
     - Automatic with Pydantic
   * - **Documentation**
     - Manual/Swagger setup
     - Built-in OpenAPI
   * - **Project Structure**
     - Flexible (too flexible)
     - Convention-based
   * - **Async Support**
     - Limited (WSGI)
     - Native (ASGI)
   * - **Type Hints**
     - Optional
     - Encouraged throughout

Basic Flask to Tatami Translation
---------------------------------

Flask App Structure
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Flask app.py
   from flask import Flask, request, jsonify
   from dataclasses import dataclass
   
   app = Flask(__name__)
   
   @dataclass
   class User:
       name: str
       email: str
   
   users = []
   
   @app.route('/users', methods=['GET'])
   def get_users():
       return jsonify(users)
   
   @app.route('/users', methods=['POST'])
   def create_user():
       data = request.get_json()
       user = User(name=data['name'], email=data['email'])
       users.append(user)
       return jsonify({'message': 'User created'})
   
   @app.route('/users/<int:user_id>', methods=['GET'])
   def get_user(user_id):
       if user_id >= len(users):
           return jsonify({'error': 'User not found'}), 404
           return jsonify(users[user_id])
   
   if __name__ == '__main__':
       app.run(debug=True)

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
   
   class Users(router('/users')):
       """User management endpoints"""
       
       def __init__(self):
           super().__init__()
           self.users = []
       
       @get('/')
       def get_users(self) -> List[User]:
           """Get all users"""
           return self.users
       
       @post('/')
       def create_user(self, user: User) -> dict:
           """Create a new user"""
           self.users.append(user)
           return {'message': 'User created'}
       
       @get('/{user_id}')
       def get_user(self, user_id: int) -> User:
           """Get user by ID"""
           if user_id >= len(self.users):
               return {'error': 'User not found'}, 404
           return self.users[user_id]

**Key improvements:**
- ✅ Automatic request validation with Pydantic
- ✅ Built-in OpenAPI documentation
- ✅ Type hints for better IDE support
- ✅ Organized code structure

Migration Strategies
--------------------

1. Gradual Migration (Recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Start by migrating one Flask Blueprint at a time:

**Step 1: Convert a Blueprint to a Tatami Router**

.. code-block:: python

   # Flask Blueprint
   from flask import Blueprint
   
   users_bp = Blueprint('users', __name__)
   
   @users_bp.route('/users', methods=['GET'])
   def get_users():
       return jsonify([])

.. code-block:: python

   # Tatami Router
   from tatami import router, get
   
   class Users(router('/users')):
       @get('/')
       def get_users(self):
           return []

**Step 2: Update Data Models**

.. code-block:: python

   # Flask with manual validation
   @app.route('/users', methods=['POST'])
   def create_user():
       data = request.get_json()
       if not data.get('name'):
           return jsonify({'error': 'Name required'}), 400
       if '@' not in data.get('email', ''):
           return jsonify({'error': 'Invalid email'}), 400
       # ... create user

.. code-block:: python

   # Tatami with automatic validation
   from pydantic import BaseModel, EmailStr, Field
   
   class UserCreate(BaseModel):
       name: str = Field(min_length=1)
       email: EmailStr
   
   class Users(router('/users')):
       @post('/')
       def create_user(self, user: UserCreate):
           # Validation happens automatically!
           return {'message': 'User created'}

2. Complete Rewrite
^^^^^^^^^^^^^^^^^^^

For smaller Flask apps, a complete rewrite might be faster:

.. code-block:: bash

   # Create new Tatami project
   tatami create my-new-api
   cd my-new-api
   
   # Copy and convert your Flask routes to Tatami routers
   # Update data models to use Pydantic
   # Test thoroughly

Common Migration Patterns
-------------------------

Flask Request Handling → Tatami Parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Flask
   from flask import request
   
   @app.route('/search')
   def search():
       query = request.args.get('q')
       page = int(request.args.get('page', 1))
       category = request.args.get('category')

.. code-block:: python

   # Tatami
   from tatami.param import Query
   
   class Search(router('/search')):
       @get('/')
       def search(
           self,
           q: str = Query(...),
           page: int = Query(1),
           category: str = Query(None)
       ):
           # Parameters automatically extracted and validated

Flask Error Handling → Tatami Error Responses
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Flask
   from flask import jsonify
   
   @app.route('/users/<int:user_id>')
   def get_user(user_id):
       user = get_user_from_db(user_id)
       if not user:
           return jsonify({'error': 'User not found'}), 404
       return jsonify(user.dict())

.. code-block:: python

   # Tatami
   class Users(router('/users')):
       @get('/{user_id}')
       def get_user(self, user_id: int):
           user = get_user_from_db(user_id)
           if not user:
               return {'error': 'User not found'}, 404
           return user

Flask Blueprints → Tatami Routers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Flask
   from flask import Blueprint
   
   auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
   users_bp = Blueprint('users', __name__, url_prefix='/users')
   
   @auth_bp.route('/login', methods=['POST'])
   def login():
       pass
   
   @users_bp.route('/', methods=['GET'])
   def get_users():
       pass
   
   app.register_blueprint(auth_bp)
   app.register_blueprint(users_bp)

.. code-block:: python

   # Tatami
   class Auth(router('/auth')):
       @post('/login')
       def login(self, credentials: LoginData):
           pass
   
   class Users(router('/users')):
       @get('/')
       def get_users(self):
           pass
   
   # Routers are auto-discovered when using `tatami run`

Flask-SQLAlchemy → Tatami with SQLAlchemy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Flask-SQLAlchemy
   from flask_sqlalchemy import SQLAlchemy
   
   db = SQLAlchemy(app)
   
   class User(db.Model):
       id = db.Column(db.Integer, primary_key=True)
       name = db.Column(db.String(100), nullable=False)
   
   @app.route('/users')
   def get_users():
       users = User.query.all()
       return jsonify([{'id': u.id, 'name': u.name} for u in users])

.. code-block:: python

   # Tatami with SQLAlchemy
   from sqlalchemy.orm import Session
   from services.user_service import UserService
   
   class Users(router('/users')):
       def __init__(self, user_service: UserService):
           super().__init__()
           self.user_service = user_service
       
       @get('/')
       def get_users(self):
           return self.user_service.get_all_users()

Handling Flask Extensions
-------------------------

Flask-Login → Custom Auth Middleware
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Flask-Login
   from flask_login import login_required, current_user
   
   @app.route('/profile')
   @login_required
   def profile():
       return jsonify({'user_id': current_user.id})

.. code-block:: python

   # Tatami with middleware
   from middleware.auth_middleware import AuthMiddleware
   
   class Profile(router('/profile')):
       def __init__(self):
           super().__init__()
           self.add_middleware(AuthMiddleware)
       
       @get('/')
       def profile(self, current_user: User = Depends(get_current_user)):
           return {'user_id': current_user.id}

Flask-CORS → ASGI CORS Middleware
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # Flask-CORS
   from flask_cors import CORS
   
   CORS(app, origins=['http://localhost:3000'])

.. code-block:: python

   # Tatami with CORS middleware
   from starlette.middleware.cors import CORSMiddleware
   
   # In middleware/cors_middleware.py
   cors_middleware = CORSMiddleware(
       allow_origins=['http://localhost:3000'],
       allow_credentials=True,
       allow_methods=['*'],
       allow_headers=['*'],
   )

Development Workflow Changes
----------------------------

Flask Development
^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Flask
   export FLASK_APP=app.py
   export FLASK_ENV=development
   flask run --debug

Tatami Development
^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Tatami
   tatami run . --mode dev --verbose

Configuration Migration
-----------------------

Flask Config
^^^^^^^^^^^^

.. code-block:: python

   # Flask config.py
   class Config:
       SECRET_KEY = 'dev-secret-key'
       SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
       DEBUG = True

Tatami Config
^^^^^^^^^^^^^

.. code-block:: yaml

   # config-dev.yaml
   app:
     secret_key: "dev-secret-key"
     debug: true
   
   database:
     url: "sqlite:///app.db"

Testing Migration
-----------------

Flask Testing
^^^^^^^^^^^^^

.. code-block:: python

   # Flask testing
   import pytest
   from app import app
   
   @pytest.fixture
   def client():
       with app.test_client() as client:
           yield client
   
   def test_get_users(client):
       response = client.get('/users')
       assert response.status_code == 200

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
           response = client.get('/users')
           assert response.status_code == 200

Migration Checklist
-------------------

Before Migration
^^^^^^^^^^^^^^^^

- [ ] **Audit Flask app** - List all routes, blueprints, and extensions
- [ ] **Identify models** - Catalog all data models and validation
- [ ] **Review middleware** - List Flask extensions and custom middleware
- [ ] **Document APIs** - Ensure you understand current functionality

During Migration
^^^^^^^^^^^^^^^^

- [ ] **Create Tatami project** - `tatami create new-app`
- [ ] **Convert models** - Update to Pydantic models
- [ ] **Migrate routes** - Convert Flask routes to Tatami routers
- [ ] **Update tests** - Adapt test suite for Tatami
- [ ] **Handle extensions** - Replace Flask extensions with Tatami equivalents

After Migration
^^^^^^^^^^^^^^^

- [ ] **Test thoroughly** - Ensure all functionality works
- [ ] **Update documentation** - API docs are auto-generated now!
- [ ] **Performance test** - ASGI should be faster than WSGI
- [ ] **Deploy** - Use Docker for consistent deployment

Common Gotchas
--------------

1. Request Context
^^^^^^^^^^^^^^^^^^

Flask's request context doesn't exist in Tatami. Pass data explicitly:

.. code-block:: python

   # Flask - implicit request context
   from flask import request
   
   def some_function():
       user_id = request.headers.get('User-ID')

.. code-block:: python

   # Tatami - explicit parameters
   from tatami.param import Header
   
   def some_function(user_id: str = Header(..., alias='User-ID')):
       # user_id is explicitly passed

2. Global State
^^^^^^^^^^^^^^^

Avoid global variables. Use dependency injection:

.. code-block:: python

   # Flask - global state
   from flask_sqlalchemy import SQLAlchemy
   
   db = SQLAlchemy()  # Global

.. code-block:: python

   # Tatami - dependency injection
   class UserService:
       def __init__(self, db: Session):
           self.db = db  # Injected dependency

3. Template Rendering
^^^^^^^^^^^^^^^^^^^^^

Tatami uses Jinja2 but templates are in the `templates/` directory:

.. code-block:: python

   # Flask
   from flask import render_template
   
   @app.route('/')
   def index():
       return render_template('index.html', users=users)

.. code-block:: python

   # Tatami
   from starlette.templating import Jinja2Templates
   
   templates = Jinja2Templates(directory="templates")
   
   class Pages(router('/')):
       @get('/')
       def index(self, request: Request):
           return templates.TemplateResponse("index.html", {
               "request": request, 
               "users": users
           })

Benefits After Migration
------------------------

Once you've migrated, you'll enjoy:

- 🚀 **Better Performance** - ASGI is faster than WSGI  
- 📚 **Auto Documentation** - OpenAPI docs generated automatically  
- 🔧 **Better Tooling** - Enhanced IDE support with type hints  
- 🧪 **Easier Testing** - Dependency injection makes mocking simple  
- 🏗️ **Cleaner Architecture** - Separation of concerns built-in  
- 📈 **Future-Proof** - Modern async/await patterns  

Need Help?
----------

- 📖 **Documentation**: Read through the Tatami guides
- 🎥 **Examples**: Check the examples in the repository
- 💬 **Community**: Join discussions on GitHub
- 🐛 **Issues**: Report problems or ask questions

The migration might seem daunting, but the cleaner architecture and modern features make it worthwhile! 🎋
