Middleware & Services 🔄
=======================

Learn how to create middleware for request processing and organize your business logic into services.

Understanding Middleware
------------------------

Middleware processes every request and response in your application, enabling cross-cutting concerns like authentication, logging, and CORS.

Creating Custom Middleware
--------------------------

.. code-block:: python

   # middleware/auth_middleware.py
   from starlette.middleware.base import BaseHTTPMiddleware

   class AuthMiddleware(BaseHTTPMiddleware):
       async def dispatch(self, request, call_next):
           # Process request
           auth_header = request.headers.get('Authorization')
           
           if not auth_header and request.url.path.startswith('/api/'):
               return Response("Unauthorized", status_code=401)
           
           # Continue to endpoint
           response = await call_next(request)
           
           # Process response
           response.headers["X-Custom-Header"] = "Added by middleware"
           return response

Service Organization
--------------------

Services contain your business logic:

.. code-block:: python

   # services/user_service.py
   from tatami.di import injectable
   
   @injectable
   class UserService:
       def __init__(self, user_repository: UserRepository):
           self.user_repository = user_repository
       
       def create_user(self, user_data):
           # Business logic here
           if self.user_exists(user_data.email):
               raise ValueError("User already exists")
           
           return self.user_repository.create(user_data)

What's Next?
------------

Learn about testing your applications and deployment strategies.
