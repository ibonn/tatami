Routing Guide 🗺️
================

This guide covers everything you need to know about routing in Tatami. You'll learn about URL patterns, parameters, HTTP methods, and advanced routing techniques.

Why Class-Based Routers? 🏗️
---------------------------

Tatami uses class-based routers because they provide:

**🎯 Organization**: Related endpoints stay together
**🔧 Reusability**: Share logic between endpoints
**🧹 Clean Code**: Clear separation of concerns
**💉 Dependency Injection**: Easy service integration
**📚 Documentation**: Self-documenting API structure

Traditional frameworks scatter routes across files. Tatami groups them logically:

.. code-block:: python

   # ✅ Tatami way - organized and clear
   class Users(router('/users')):
       @get('/{user_id}')
       def get_user(self, user_id: int):
           return self.user_service.get(user_id)
       
       @post('/')
       def create_user(self, user: User):
           return self.user_service.create(user)

   # ❌ Traditional way - scattered routes
   @app.get('/users/{user_id}')
   def get_user(user_id: int):
       # Logic here...

   @app.post('/users')  
   def create_user(user: User):
       # Logic here...

Basic Router Setup
------------------

Creating a Router
^^^^^^^^^^^^^^^^^

Use the `router()` function to create a router class:

.. code-block:: python

   from tatami import router, get, post, put, delete

   class Products(router('/products')):
       """Product management endpoints"""
       pass

The path `/products` becomes the base URL for all endpoints in this router.

Adding Endpoints
^^^^^^^^^^^^^^^^

Use HTTP method decorators to define endpoints:

.. code-block:: python

   class Products(router('/products')):
       @get
       def list_products(self):
           """GET /products - List all products"""
           return {"products": []}
       
       @get('/{product_id}')
       def get_product(self, product_id: int):
           """GET /products/{product_id} - Get specific product"""
           return {"id": product_id}
       
       @post
       def create_product(self, product: ProductCreate):
           """POST /products - Create new product"""
           return {"message": "Product created"}

HTTP Method Decorators
----------------------

Tatami provides decorators for all HTTP methods:

.. code-block:: python

   from tatami import get, post, put, patch, delete, head, options

   class API(router('/api')):
       @get('/data')
       def get_data(self):
           return {"method": "GET"}
       
       @post('/data')
       def create_data(self, data: dict):
           return {"method": "POST", "data": data}
       
       @put('/data/{id}')
       def replace_data(self, id: int, data: dict):
           return {"method": "PUT", "id": id}
       
       @patch('/data/{id}')
       def update_data(self, id: int, updates: dict):
           return {"method": "PATCH", "id": id}
       
       @delete('/data/{id}')
       def delete_data(self, id: int):
           return {"method": "DELETE", "id": id}
       
       @head('/data')
       def head_data(self):
           # Return headers only, no body
           pass
       
       @options('/data')
       def options_data(self):
           return {"allowed_methods": ["GET", "POST", "PUT", "DELETE"]}

URL Parameters
--------------

Path Parameters
^^^^^^^^^^^^^^^

Extract values from the URL path:

.. code-block:: python

   class Users(router('/users')):
       @get('/{user_id}')
       def get_user(self, user_id: int):
           """user_id comes from the URL path"""
           return {"user_id": user_id}
       
       @get('/{user_id}/posts/{post_id}')
       def get_user_post(self, user_id: int, post_id: int):
           """Multiple path parameters"""
           return {"user_id": user_id, "post_id": post_id}

Path parameters are automatically converted to the specified type (int, str, float, etc.).

Query Parameters
^^^^^^^^^^^^^^^^

Extract values from the query string:

.. code-block:: python

   from tatami.param import Query

   class Products(router('/products')):
       @get
       def list_products(
           self,
           page: int = Query(1),
           limit: int = Query(10),
           category: str = Query(None)
       ):
           """
           GET /products?page=2&limit=20&category=electronics
           """
           return {
               "page": page,
               "limit": limit,
               "category": category
           }

Required vs Optional Parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

   from tatami.param import Query

   class Search(router('/search')):
       @get
       def search(
           self,
           q: str = Query(...),  # Required
           type: str = Query("all"),  # Optional with default
           limit: int = Query(None)  # Optional, can be None
       ):
           return {"query": q, "type": type, "limit": limit}

Header Parameters
^^^^^^^^^^^^^^^^^

Extract values from HTTP headers:

.. code-block:: python

   from tatami.param import Header

   class API(router('/api')):
       @get('/data')
       def get_data(
           self,
           authorization: str = Header(...),
           content_type: str = Header("application/json", alias="Content-Type"),
           user_agent: str = Header(None, alias="User-Agent")
       ):
           return {
               "auth": authorization,
               "content_type": content_type,
               "user_agent": user_agent
           }

Request Body Handling
---------------------

JSON Request Bodies
^^^^^^^^^^^^^^^^^^^

Use Pydantic models for request body validation:

.. code-block:: python

   from pydantic import BaseModel, Field

   class ProductCreate(BaseModel):
       name: str = Field(min_length=1, max_length=100)
       price: float = Field(gt=0)
       description: str = Field(None, max_length=500)
       tags: List[str] = Field(default_factory=list)

   class Products(router('/products')):
       @post('/')
       def create_product(self, product: ProductCreate):
           """Automatic JSON parsing and validation"""
           return {
               "message": f"Created product: {product.name}",
               "price": product.price
           }

Form Data
^^^^^^^^^

Handle form submissions:

.. code-block:: python

   from starlette.requests import Request

   class Upload(router('/upload')):
       @post('/file')
       async def upload_file(self, request: Request):
           """Handle file uploads"""
           form = await request.form()
           file = form.get("file")
           
           if file:
               content = await file.read()
               return {"filename": file.filename, "size": len(content)}
           
           return {"error": "No file provided"}, 400

Advanced Routing Patterns
-------------------------

Nested Routers
^^^^^^^^^^^^^^

Create hierarchical URL structures:

.. code-block:: python

   class Users(router('/users')):
       @get('/{user_id}')
       def get_user(self, user_id: int):
           return {"user_id": user_id}

   class UserPosts(router('/users/{user_id}/posts')):
       @get
       def list_user_posts(self, user_id: int):
           return {"user_id": user_id, "posts": []}
       
       @get('/{post_id}')
       def get_user_post(self, user_id: int, post_id: int):
           return {"user_id": user_id, "post_id": post_id}

Router Composition
^^^^^^^^^^^^^^^^^^

Include routers within other routers:

.. code-block:: python

   from tatami import BaseRouter

   # Create sub-routers
   users_router = Users()
   posts_router = Posts()

   # Main application
   app = BaseRouter(title="My API")
   app.include_router(users_router)
   app.include_router(posts_router)

Custom Response Types
^^^^^^^^^^^^^^^^^^^^^

Return different response types:

.. code-block:: python

   from starlette.responses import JSONResponse, HTMLResponse, RedirectResponse

   class Pages(router('/pages')):
       @get('/json')
       def json_response(self):
           return JSONResponse({"message": "JSON response"})
       
       @get('/html')
       def html_response(self):
           return HTMLResponse("<h1>HTML Response</h1>")
       
       @get('/redirect')
       def redirect_response(self):
           return RedirectResponse(url="/pages/html")

Error Handling
--------------

Return Error Responses
^^^^^^^^^^^^^^^^^^^^^^

Return tuples for error responses:

.. code-block:: python

   class Users(router('/users')):
       @get('/{user_id}')
       def get_user(self, user_id: int):
           if user_id < 1:
               return {"error": "Invalid user ID"}, 400
           
           user = self.user_service.get(user_id)
           if not user:
               return {"error": "User not found"}, 404
           
           return user

Custom Exceptions
^^^^^^^^^^^^^^^^^

Create and raise custom exceptions:

.. code-block:: python

   class UserNotFoundError(Exception):
       pass

   class Users(router('/users')):
       @get('/{user_id}')
       def get_user(self, user_id: int):
           user = self.user_service.get(user_id)
           if not user:
               raise UserNotFoundError(f"User {user_id} not found")
           return user

Route Priority and Ordering
---------------------------

Tatami automatically orders routes by specificity:

.. code-block:: python

   class API(router('/api')):
       @get('/users/me')          # 🥇 Most specific - matches first
       def get_current_user(self):
           return {"user": "current"}
       
       @get('/users/{user_id}')   # 🥈 Less specific - matches after /me
       def get_user(self, user_id: int):
           return {"user_id": user_id}
       
       @get('/users')             # 🥉 Least specific - matches last
       def list_users(self):
           return {"users": []}

The order in your code doesn't matter - Tatami sorts routes intelligently!

Middleware Integration
----------------------

Add middleware to specific routers:

.. code-block:: python

   from starlette.middleware.base import BaseHTTPMiddleware

   class AuthMiddleware(BaseHTTPMiddleware):
       async def dispatch(self, request, call_next):
           # Authentication logic
           response = await call_next(request)
           return response

   class AdminAPI(router('/admin')):
       def __init__(self):
           super().__init__()
           self.add_middleware(AuthMiddleware)
       
       @get('/dashboard')
       def dashboard(self):
           return {"page": "admin dashboard"}

Dependency Injection in Routers
-------------------------------

Inject services into router constructors:

.. code-block:: python

   class Users(router('/users')):
       def __init__(self, user_service: UserService, email_service: EmailService):
           super().__init__()
           self.user_service = user_service
           self.email_service = email_service
       
       @post('/')
       def create_user(self, user: UserCreate):
           # Use injected services
           new_user = self.user_service.create(user)
           self.email_service.send_welcome(new_user.email)
           return new_user

Testing Routers
---------------

Test routers using standard HTTP clients:

.. code-block:: python

   import httpx
   from tatami import BaseRouter

   def test_users_api():
       # Setup
       users_router = Users(user_service=MockUserService())
       app = BaseRouter()
       app.include_router(users_router)
       
       # Test
       with httpx.Client(app=app, base_url="http://test") as client:
           response = client.get("/users/1")
           assert response.status_code == 200
           assert response.json()["user_id"] == 1

Best Practices
--------------

🎯 Keep Routers Focused
^^^^^^^^^^^^^^^^^^^^^^^^

Each router should handle one resource or domain:

.. code-block:: python

   # ✅ Good - focused on users
   class Users(router('/users')):
       @get
       def list_users(self): pass
       
       @post
       def create_user(self): pass

   # ❌ Bad - mixed concerns
   class MixedAPI(router('/api')):
       @get('/users')
       def list_users(self): pass
       
       @get('/products')
       def list_products(self): pass

🔧 Use Type Hints
^^^^^^^^^^^^^^^^^^

Always use type hints for better IDE support and validation:

.. code-block:: python

   class Products(router('/products')):
       @get('/{product_id}')
       def get_product(self, product_id: int) -> ProductResponse:
           return self.product_service.get(product_id)

📋 Document Your Endpoints
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use docstrings for API documentation:

.. code-block:: python

   class Users(router('/users')):
       @get('/{user_id}')
       def get_user(self, user_id: int):
           """
           Get a user by ID.
           
           Returns user information including name, email, and profile data.
           """
           return self.user_service.get(user_id)

🔍 Validate Input Early
^^^^^^^^^^^^^^^^^^^^^^^^

Use Pydantic models for comprehensive validation:

.. code-block:: python

   class UserCreate(BaseModel):
       name: str = Field(min_length=1, max_length=100)
       email: EmailStr
       age: int = Field(ge=13, le=120)
       
   class Users(router('/users')):
       @post('/')
       def create_user(self, user: UserCreate):
           # Validation happens automatically!
           return self.user_service.create(user)

Common Patterns
---------------

RESTful CRUD Operations
^^^^^^^^^^^^^^^^^^^^^^^

Standard REST API pattern:

.. code-block:: python

   class Products(router('/products')):
       @get
       def list_products(self):
           """GET /products - List all products"""
           return self.product_service.list()
       
       @get('/{product_id}')
       def get_product(self, product_id: int):
           """GET /products/{id} - Get specific product"""
           return self.product_service.get(product_id)
       
       @post('/')
       def create_product(self, product: ProductCreate):
           """POST /products - Create new product"""
           return self.product_service.create(product)
       
       @put('/{product_id}')
       def update_product(self, product_id: int, product: ProductUpdate):
           """PUT /products/{id} - Update product"""
           return self.product_service.update(product_id, product)
       
       @delete('/{product_id}')
       def delete_product(self, product_id: int):
           """DELETE /products/{id} - Delete product"""
           self.product_service.delete(product_id)
           return {"message": "Product deleted"}

Search and Filtering
^^^^^^^^^^^^^^^^^^^^

Implement search with query parameters:

.. code-block:: python

   class Products(router('/products')):
       @get('/search')
       def search_products(
           self,
           q: str = Query(...),
           category: str = Query(None),
           min_price: float = Query(None),
           max_price: float = Query(None),
           sort: str = Query("name"),
           page: int = Query(1),
           limit: int = Query(20)
       ):
           """Search products with filters"""
           return self.product_service.search(
               query=q,
               category=category,
               min_price=min_price,
               max_price=max_price,
               sort=sort,
               page=page,
               limit=limit
           )

Batch Operations
^^^^^^^^^^^^^^^^

Handle multiple items at once:

.. code-block:: python

   class Products(router('/products')):
       @post('/batch')
       def create_products_batch(self, products: List[ProductCreate]):
           """Create multiple products at once"""
           results = []
           for product in products:
               try:
                   result = self.product_service.create(product)
                   results.append({"success": True, "product": result})
               except Exception as e:
                   results.append({"success": False, "error": str(e)})
           return {"results": results}

What's Next?
------------

Now you're a Tatami routing expert! Next, learn about:

- Working with data and database integration
- Dependency injection for better code organization
- Middleware for request processing
- Testing strategies for your APIs

Happy routing! 🎯
