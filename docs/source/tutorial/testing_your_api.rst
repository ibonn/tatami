Testing Your API 🧪
==================

Learn how to write comprehensive tests for your Tatami applications.

Why Testing Matters
-------------------

Testing ensures your API works correctly and prevents regressions as your code evolves.

Unit Testing Services
---------------------

.. code-block:: python

   # tests/test_user_service.py
   import pytest
   from services.user_service import UserService

   def test_create_user():
       service = UserService()
       user_data = {"name": "Test User", "email": "test@example.com"}
       
       result = service.create_user(user_data)
       
       assert result["name"] == "Test User"
       assert result["email"] == "test@example.com"

Integration Testing Routers
---------------------------

.. code-block:: python

   # tests/test_user_router.py
   import httpx
   from tatami import BaseRouter

   def test_get_user():
       app = BaseRouter()
       app.include_router(Users())
       
       with httpx.Client(app=app, base_url="http://test") as client:
           response = client.get("/users/1")
           assert response.status_code == 200

What's Next?
------------

Learn about deploying your Tatami applications to production.
