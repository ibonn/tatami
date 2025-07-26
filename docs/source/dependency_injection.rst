Dependency Injection
====================

.. warning::

   **Dependency injection is not yet implemented in Tatami.** 
   
   This documentation describes planned features that are currently under development. 
   For now, you'll need to handle dependency injection manually in your router constructors.

Current State
-------------

As of version 0.0.1-pre.1, Tatami does not include a built-in dependency injection system. You can still organize your code with services and dependencies, but you'll need to wire them manually:

.. code-block:: python

   # services/user_service.py
   class UserService:
       def __init__(self):
           self.users = {}
       
       def get_user(self, user_id: str):
           return self.users.get(user_id)
       
       def create_user(self, user_data):
           # Implementation here
           pass

   # routers/users.py
   from tatami import router, get, post
   from services.user_service import UserService

   class Users(router('/users')):
       def __init__(self, user_service: UserService):
           self.user_service = user_service
           super().__init__()
       
       @get('/{user_id}')
       def get_user(self, user_id: str):
           return self.user_service.get_user(user_id)

   # Manual wiring in your main app
   from tatami import BaseRouter
   
   user_service = UserService()
   users_router = Users(user_service)
   
   app = BaseRouter()
   app.include_router(users_router)

Planned Features
----------------

Future versions of Tatami will include:

- **@inject decorator** for automatic dependency resolution
- **Service registration** and discovery
- **Scoped dependencies** (singleton, per-request, transient)
- **Convention-based service loading** from services/ directory
- **Type-based injection** using Python type hints

Roadmap Example (Not Yet Implemented):

.. code-block:: python

   # This is planned but not working yet:
   from tatami import inject, router, get
   
   @inject  # This decorator doesn't exist yet
   def my_endpoint(user_id: str, user_service: UserService):
       return user_service.get_user(user_id)
   
   # Or automatic injection in routers:
   class Users(router('/users')):
       @get('/{user_id}')
       def get_user(self, user_id: str, user_service: UserService):
           # user_service would be auto-injected (planned)
           return user_service.get_user(user_id)

Contributing
------------

If you're interested in helping implement dependency injection in Tatami, please check the project's GitHub issues or start a discussion about the design approach.

