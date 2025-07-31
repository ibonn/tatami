Dependency Injection 💉
======================

Learn how Tatami's dependency injection system makes your code more modular, testable, and maintainable.

.. important::
   **Key Design Principle**: Services with ``@injectable`` decorator **CANNOT** access request data (headers, path params, query params) directly. This enforces separation of concerns where routers handle HTTP concerns and services handle business logic.
   
   However, services **CAN** be chained with other services and will be automatically injected by Tatami's dependency injection system.

What is Dependency Injection?
-----------------------------

Dependency injection is a design pattern where objects receive their dependencies from external sources rather than creating them internally.

Why Use Dependency Injection?
-----------------------------

- ✅ **Better Testing**: Easy to mock dependencies  
- ✅ **Loose Coupling**: Components aren't tightly bound  
- ✅ **Reusability**: Services can be used across different contexts  
- ✅ **Maintainability**: Changes in one component don't break others  

The @injectable Decorator
-------------------------

Services in Tatami must be marked with the ``@injectable`` decorator to be discovered by the dependency injection system:

.. code-block:: python

   # services/user_service.py
   from tatami.di import injectable
   
   @injectable
   class UserService:
       def __init__(self):
           self.users = {}  # In-memory storage (use proper storage in production)
       
       def get_user(self, user_id: int):
           return self.users.get(user_id, {"id": user_id, "name": "Unknown"})
       
       def create_user(self, user_data):
           user_id = len(self.users) + 1
           user = {"id": user_id, **user_data}
           self.users[user_id] = user
           return user

Basic Router with Dependency Injection
--------------------------------------

.. code-block:: python

   # routers/users.py
   from tatami import router, get, post
   from services.user_service import UserService
   from pydantic import BaseModel

   class UserCreate(BaseModel):
       name: str
       email: str

   class Users(router('/users')):
       def __init__(self, user_service: UserService):
           super().__init__()
           self.user_service = user_service
       
       @get
       def list_users(self):
           """List all users"""
           return list(self.user_service.users.values())
       
       @get('/{user_id}')
       def get_user(self, user_id: int):
           """Get user by ID"""
           return self.user_service.get_user(user_id)
       
       @post
       def create_user(self, user_data: UserCreate):
           """Create a new user"""
           return self.user_service.create_user(user_data.dict())

Tatami automatically discovers and injects the ``UserService`` into the ``Users`` router!

Dependency Injection Scopes
---------------------------

Tatami supports different dependency scopes:

.. code-block:: python

   from tatami.di import injectable, Scope

   @injectable(scope=Scope.SINGLETON)
   class DatabaseService:
       """Single instance shared across the application"""
       def __init__(self):
           self.connection = create_db_connection()

   @injectable(scope=Scope.REQUEST)
   class RequestContextService:
       """New instance for each HTTP request"""
       def __init__(self):
           self.request_id = generate_request_id()

   @injectable  # Default is REQUEST scope
   class UserService:
       def __init__(self, db_service: DatabaseService):
           self.db = db_service

Chained Dependencies
--------------------

Services can depend on other services, creating dependency chains:

.. code-block:: python

   from tatami.di import injectable

   @injectable
   class EmailService:
       def send_email(self, to: str, subject: str, body: str):
           print(f"📧 Sending email to {to}: {subject}")
           # Actual email sending logic here

   @injectable
   class NotificationService:
       def __init__(self, email_service: EmailService):
           self.email_service = email_service
       
       def notify_user(self, user_email: str, message: str):
           self.email_service.send_email(
               to=user_email,
               subject="Notification",
               body=message
           )

   @injectable
   class UserService:
       def __init__(self, notification_service: NotificationService):
           self.notification_service = notification_service
           self.users = {}
       
       def create_user(self, user_data):
           user_id = len(self.users) + 1
           user = {"id": user_id, **user_data}
           self.users[user_id] = user
           
           # Send welcome notification
           self.notification_service.notify_user(
               user["email"],
               "Welcome to our platform!"
           )
           return user

Mixed Dependencies: Services and Factories
------------------------------------------

You can combine injectable services with factory-created dependencies using ``Annotated[T, Inject()]``:

.. code-block:: python

   from tatami.di import injectable, Inject
   from typing import Annotated
   import redis
   from sqlalchemy import create_engine, Engine

   # Factory functions for external resources
   def create_redis_client():
       """Factory for Redis client"""
       return redis.Redis(host='localhost', port=6379, db=0)

   def create_database_engine():
       """Factory for database engine"""
       return create_engine('postgresql://user:pass@localhost/db')

   @injectable
   class CacheService:
       """Service that uses factory-created Redis client"""
       def __init__(self, redis_client: Annotated[redis.Redis, Inject(factory=create_redis_client)]):
           self.redis = redis_client
       
       def get(self, key: str):
           return self.redis.get(key)
       
       def set(self, key: str, value: str, ttl: int = 300):
           self.redis.setex(key, ttl, value)

   @injectable
   class UserRepository:
       """Service that mixes factory dependency with service dependency"""
       def __init__(self, 
                    db_engine: Annotated[Engine, Inject(factory=create_database_engine)],
                    cache_service: CacheService):  # Injectable service
           self.db = db_engine
           self.cache = cache_service
       
       def get_user(self, user_id: int):
           # Try cache first
           cached_user = self.cache.get(f"user:{user_id}")
           if cached_user:
               return eval(cached_user)  # In real code, use json.loads
           
           # Query database
           with self.db.connect() as conn:
               result = conn.execute(f"SELECT * FROM users WHERE id = {user_id}")
               user = dict(result.fetchone())
           
           # Cache the result
           self.cache.set(f"user:{user_id}", str(user), ttl=600)
           return user

   @injectable
   class UserService:
       """Service that depends on mixed-dependency service"""
       def __init__(self, 
                    user_repo: UserRepository,  # Service with mixed dependencies
                    email_service: EmailService):  # Pure injectable service
           self.user_repo = user_repo
           self.email_service = email_service
       
       def create_user(self, user_data: dict):
           # Business logic using chained dependencies
           user_id = len(self.get_all_users()) + 1
           user = {"id": user_id, **user_data}
           
           # Save via repository (which uses DB + cache)
           self.user_repo.save_user(user)
           
           # Send welcome email via service
           self.email_service.send_email(
               to=user["email"],
               subject="Welcome!",
               body="Welcome to our platform!"
           )
           return user

This pattern allows you to:

- Use **injectable services** for your business logic (``EmailService``, ``CacheService``)
- Use **factory functions** for external resources (database connections, Redis clients)
- **Chain dependencies** freely - services can depend on other services OR factory-created objects
- **Mix and match** - a service can have both service dependencies and factory dependencies

Separation of Concerns: Services vs Routers
-------------------------------------------

**IMPORTANT**: Services with ``@injectable`` decorator **CANNOT** access request data (headers, path params, query params) directly. This is by design to maintain separation of concerns.

**✅ Correct**: Routers handle request data, services handle business logic:

.. code-block:: python

   from tatami.di import injectable

   @injectable
   class UserService:
       def __init__(self):
           self.users = {}
       
       def create_user(self, user_data: dict):
           # Pure business logic - no request access
           user_id = len(self.users) + 1
           user = {"id": user_id, **user_data}
           self.users[user_id] = user
           return user
       
       def authenticate_user(self, auth_token: str):
           # Service receives processed data, not raw request
           if auth_token == "valid-token":
               return {"id": 1, "name": "Authenticated User"}
           return None

   class Users(router('/users')):
       def __init__(self, user_service: UserService):
           super().__init__()
           self.user_service = user_service
       
       @post
       def create_user(self, request: Request, user_data: UserCreate):
           # Router extracts request data
           auth_token = request.headers.get("authorization", "")
           user_ip = request.client.host
           
           # Router validates authentication via service
           current_user = self.user_service.authenticate_user(auth_token)
           if not current_user:
               raise HTTPException(401, "Unauthorized")
           
           # Router passes processed data to service
           new_user = self.user_service.create_user({
               "name": user_data.name,
               "email": user_data.email,
               "created_by_ip": user_ip
           })
           return new_user

**❌ Incorrect**: Services should NOT access request directly:

.. code-block:: python

   @injectable
   class BadUserService:
       def __init__(self, request: Request):  # ❌ DON'T DO THIS!
           self.request = request  # Violates separation of concerns
       
       def create_user(self, user_data):
           # ❌ Business logic mixed with request handling
           auth_header = self.request.headers.get("authorization")
           user_ip = self.request.client.host

Factory-Created Dependencies Can Access Request Data
----------------------------------------------------

**IMPORTANT**: Dependencies created via factory functions (using ``Annotated[T, Inject(factory=...)]``) **CAN** access request data. This is useful for request-specific utilities, middleware-like functions, or validation helpers.

**✅ Correct**: Factory-created dependencies accessing request:

.. code-block:: python

   from tatami import Request
   from tatami.di import Inject, Scope
   from typing import Optional, Annotated
   from datetime import datetime

   class RequestValidator:
       """Request-aware validator"""
       def __init__(self, request: Request):
           self.request = request
       
       def get_auth_user(self) -> Optional[dict]:
           """Extract and validate authentication from request"""
           auth_header = self.request.headers.get("authorization", "")
           if not auth_header.startswith("Bearer "):
               return None
           
           token = auth_header[7:]  # Remove "Bearer " prefix
           # Validate token logic here
           if token == "valid-token":
               return {"id": 1, "name": "John Doe", "role": "user"}
           return None
       
       def get_client_info(self) -> dict:
           """Extract client information from request"""
           return {
               "ip": self.request.client.host,
               "user_agent": self.request.headers.get("user-agent", ""),
               "forwarded_for": self.request.headers.get("x-forwarded-for", "")
           }

   class AuditLogger:
       """Request-aware audit logger"""
       def __init__(self, request: Request):
           self.request = request
       
       def log_action(self, action: str, user_id: int, details: dict):
           """Log user action with request context"""
           log_entry = {
               "action": action,
               "user_id": user_id,
               "timestamp": datetime.now().isoformat(),
               "ip": self.request.client.host,
               "endpoint": f"{self.request.method} {self.request.url.path}",
               "details": details
           }
           print(f"📝 AUDIT: {log_entry}")

   # Factory functions that can access request
   def create_request_validator(request: Request) -> RequestValidator:
       """Factory function for RequestValidator"""
       return RequestValidator(request)

   def create_audit_logger(request: Request) -> AuditLogger:
       """Factory function for AuditLogger"""
       return AuditLogger(request)

   @injectable
   class UserService:
       """Injectable service - pure business logic"""
       def __init__(self):
           self.users = {}
       
       def create_user(self, user_data: dict) -> dict:
           user_id = len(self.users) + 1
           user = {"id": user_id, **user_data}
           self.users[user_id] = user
           return user

   class Users(router('/users')):
       def __init__(self, user_service: UserService):
           super().__init__()
           self.user_service = user_service
       
       @post
       def create_user(self, 
                       user_data: UserCreate,
                       # Factory-created dependencies that can access request
                       validator: Annotated[RequestValidator, Inject(factory=create_request_validator, scope=Scope.REQUEST)],
                       audit_logger: Annotated[AuditLogger, Inject(factory=create_audit_logger, scope=Scope.REQUEST)]):
           
           # Use request-aware dependencies
           current_user = validator.get_auth_user()
           if not current_user:
               raise HTTPException(401, "Unauthorized")
           
           client_info = validator.get_client_info()
           
           # Use pure business service
           new_user = self.user_service.create_user({
               "name": user_data.name,
               "email": user_data.email,
               "created_by": current_user["id"],
               "created_from_ip": client_info["ip"]
           })
           
           # Log the action with request context
           audit_logger.log_action(
               action="user_created",
               user_id=current_user["id"],
               details={"new_user_id": new_user["id"]}
           )
           
           return new_user

**Key Rules**:

- **@injectable services**: Cannot access request data - keep business logic pure
- **Factory-created dependencies**: Can access request data via ``Annotated[T, Inject(factory=...)]``
- **Mix both**: Use injectable services for business logic, factory dependencies for request handling

Factory Functions for Complex Dependencies
------------------------------------------

Use factories for complex object creation:

.. code-block:: python

   from tatami.di import injectable, Inject
   from typing import Annotated

   def create_database_connection():
       """Factory function for database connections"""
       return Database(url="postgresql://user:pass@localhost/db")

   @injectable
   class UserRepository:
       def __init__(self, db: Annotated[Database, Inject(factory=create_database_connection)]):
           self.db = db
       
       def find_user(self, user_id: int):
           return self.db.query(f"SELECT * FROM users WHERE id = {user_id}")

Testing with Dependency Injection
---------------------------------

Dependency injection makes testing straightforward:

.. code-block:: python

   # tests/test_users.py
   import pytest
   from unittest.mock import Mock
   from routers.users import Users

   def test_get_user():
       # Create mock service
       mock_service = Mock()
       mock_service.get_user.return_value = {"id": 1, "name": "Test User"}
       
       # Inject mock directly
       router = Users(user_service=mock_service)
       result = router.get_user(1)
       
       assert result["name"] == "Test User"
       mock_service.get_user.assert_called_once_with(1)

   def test_create_user():
       # Mock multiple dependencies
       mock_user_service = Mock()
       mock_audit_service = Mock()
       
       mock_user_service.create_user.return_value = {"id": 1, "name": "New User"}
       
       router = Users(
           user_service=mock_user_service,
           audit_service=mock_audit_service
       )
       
       user_data = {"name": "New User", "email": "user@example.com"}
       result = router.create_user(UserCreate(**user_data))
       
       assert result["name"] == "New User"
       mock_audit_service.log_action.assert_called_once()

Best Practices for Dependency Injection
---------------------------------------

- **Always use @injectable**: Mark all services with the decorator
- **Store data in services**: Keep business logic and data storage in services, not routers
- **Use appropriate scopes**: SINGLETON for shared resources, REQUEST for request-specific data
- **Chain dependencies logically**: Create clear dependency hierarchies
- **Test with mocks**: Use dependency injection to make testing easier
- **NEVER access request data in services**: Keep HTTP concerns in routers, business logic in services

Summary: Separation of Concerns
-------------------------------

Remember the key principle of Tatami's dependency injection:

.. code-block:: python

   # ✅ CORRECT: Router handles HTTP, Service handles business logic
   class UserRouter(router('/users')):
       def __init__(self, user_service: UserService):
           self.user_service = user_service
       
       @post
       def create_user(self, request: Request, user_data: UserCreate):
           # Router extracts HTTP data
           auth_token = request.headers.get("authorization")
           
           # Router calls service with processed data
           return self.user_service.create_user(user_data.dict(), auth_token)

   @injectable
   class UserService:
       def create_user(self, user_data: dict, auth_token: str):
           # Service handles pure business logic
           if not self.is_valid_token(auth_token):
               raise ValueError("Invalid authentication")
           # ... business logic only

What's Next?
------------

Continue learning about middleware and services, testing strategies, and deployment options.
