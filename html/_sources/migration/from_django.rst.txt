Migrating from Django 🎸➡️🎋
==========================

This guide helps Django developers transition to Tatami, showing how Django's MTV pattern translates to Tatami's modern API architecture.

Why Consider Tatami?
--------------------

As a Django developer, you'll find Tatami offers:

- ✅ **API-first design** - Built specifically for modern web APIs  
- ✅ **Simpler deployment** - No complex WSGI/ASGI configuration  
- ✅ **Auto-discovery** - Automatic component registration like Django apps  
- ✅ **Type safety** - Full type hint support throughout  
- ✅ **Modern async** - Built on ASGI from the ground up  
- ✅ **Less boilerplate** - Convention over configuration  

Key Concept Mapping
-------------------

.. list-table:: Django to Tatami Translation
   :header-rows: 1

   * - Django Concept
     - Tatami Equivalent
     - Purpose
   * - **Views (Class-based)**
     - Class-based Routers
     - Handle HTTP requests
   * - **URL patterns**
     - Router decorators
     - Define endpoints
   * - **Models**
     - Pydantic models
     - Data validation/serialization
   * - **Services/Managers**
     - Service classes
     - Business logic
   * - **Middleware**
     - Middleware classes
     - Request/response processing
   * - **Apps**
     - Router modules
     - Organize functionality
   * - **Settings**
     - YAML configuration
     - App configuration

Basic Django to Tatami Translation
----------------------------------

Django Views → Tatami Routers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Django Class-Based Views:**

.. code-block:: python

   # Django views.py
   from django.http import JsonResponse
   from django.views import View
   from django.utils.decorators import method_decorator
   from django.views.decorators.csrf import csrf_exempt
   from .models import Post
   from .serializers import PostSerializer
   
   @method_decorator(csrf_exempt, name='dispatch')
   class PostView(View):
       def get(self, request, post_id=None):
           if post_id:
               try:
                   post = Post.objects.get(id=post_id)
                   return JsonResponse(PostSerializer(post).data)
               except Post.DoesNotExist:
                   return JsonResponse({'error': 'Post not found'}, status=404)
           else:
               posts = Post.objects.all()
               return JsonResponse([PostSerializer(p).data for p in posts], safe=False)
       
       def post(self, request):
           serializer = PostSerializer(data=request.POST)
           if serializer.is_valid():
               post = serializer.save()
               return JsonResponse(PostSerializer(post).data, status=201)
           return JsonResponse(serializer.errors, status=400)

**Equivalent Tatami Router:**

.. code-block:: python

   # routers/posts.py
   from tatami import router, get, post
   from pydantic import BaseModel
   from typing import List, Optional
   
   class Post(BaseModel):
       id: Optional[int] = None
       title: str
       content: str
       author: str
   
   class PostCreate(BaseModel):
       title: str
       content: str
       author: str
   
   class Posts(router('/posts')):
       """Post management endpoints"""
       
       def __init__(self, post_service: PostService):
           super().__init__()
           self.post_service = post_service
       
       @get('/')
       def list_posts(self) -> List[Post]:
           """Get all posts"""
           return self.post_service.get_all()
       
       @get('/{post_id}')
       def get_post(self, post_id: int) -> Post:
           """Get post by ID"""
           post = self.post_service.get_by_id(post_id)
           if not post:
               return {'error': 'Post not found'}, 404
           return post
       
       @post('/')
       def create_post(self, post_data: PostCreate) -> Post:
           """Create a new post"""
           return self.post_service.create(post_data)

Django URLs → Tatami Routing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Django URL Configuration:**

.. code-block:: python

   # urls.py
   from django.urls import path, include
   from . import views
   
   app_name = 'blog'
   
   urlpatterns = [
       path('posts/', views.PostView.as_view(), name='post-list'),
       path('posts/<int:post_id>/', views.PostView.as_view(), name='post-detail'),
       path('users/', include('users.urls')),
       path('comments/', include('comments.urls')),
   ]
   
   # Main urls.py
   from django.contrib import admin
   from django.urls import path, include
   
   urlpatterns = [
       path('admin/', admin.site.urls),
       path('api/v1/', include('blog.urls')),
   ]

**Tatami Auto-Discovery:**

.. code-block:: python

   # routers/posts.py - automatically discovered
   class Posts(router('/api/v1/posts')):
       # Routes automatically registered
       pass
   
   # routers/users.py - automatically discovered  
   class Users(router('/api/v1/users')):
       # Routes automatically registered
       pass
   
   # routers/comments.py - automatically discovered
   class Comments(router('/api/v1/comments')):
       # Routes automatically registered
       pass

Django Models → Pydantic Models + Services
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Django Models:**

.. code-block:: python

   # models.py
   from django.db import models
   from django.contrib.auth.models import User
   
   class Post(models.Model):
       title = models.CharField(max_length=200)
       content = models.TextField()
       author = models.ForeignKey(User, on_delete=models.CASCADE)
       created_at = models.DateTimeField(auto_now_add=True)
       updated_at = models.DateTimeField(auto_now=True)
       
       class Meta:
           ordering = ['-created_at']
       
       def __str__(self):
           return self.title
       
       @classmethod
       def get_by_author(cls, author):
           return cls.objects.filter(author=author)

**Tatami Pydantic Models + Service:**

.. code-block:: python

   # models.py (Pydantic models for API)
   from pydantic import BaseModel
   from datetime import datetime
   from typing import Optional
   
   class Post(BaseModel):
       id: Optional[int] = None
       title: str
       content: str
       author_id: int
       created_at: Optional[datetime] = None
       updated_at: Optional[datetime] = None
   
   class PostCreate(BaseModel):
       title: str
       content: str
       author_id: int
   
   # services/post_service.py (Business logic)
   from typing import List, Optional
   
   class PostService:
       def __init__(self, post_repository: PostRepository):
           self.post_repository = post_repository
       
       def get_all(self) -> List[Post]:
           return self.post_repository.find_all()
       
       def get_by_id(self, post_id: int) -> Optional[Post]:
           return self.post_repository.find_by_id(post_id)
       
       def get_by_author(self, author_id: int) -> List[Post]:
           return self.post_repository.find_by_author(author_id)
       
       def create(self, post_data: PostCreate) -> Post:
           return self.post_repository.create(post_data)

Django Forms/Serializers → Pydantic Validation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Django Forms/Serializers:**

.. code-block:: python

   # forms.py or serializers.py
   from django import forms
   from rest_framework import serializers
   from .models import Post
   
   class PostForm(forms.ModelForm):
       class Meta:
           model = Post
           fields = ['title', 'content']
       
       def clean_title(self):
           title = self.cleaned_data['title']
           if len(title) < 5:
               raise forms.ValidationError("Title must be at least 5 characters")
           return title
   
   # Or with DRF
   class PostSerializer(serializers.ModelSerializer):
       class Meta:
           model = Post
           fields = ['id', 'title', 'content', 'author', 'created_at']
       
       def validate_title(self, value):
           if len(value) < 5:
               raise serializers.ValidationError("Title must be at least 5 characters")
           return value

**Tatami Pydantic Validation:**

.. code-block:: python

   # models.py
   from pydantic import BaseModel, validator
   from typing import Optional
   
   class PostCreate(BaseModel):
       title: str
       content: str
       author_id: int
       
       @validator('title')
       def title_must_be_long_enough(cls, v):
           if len(v) < 5:
               raise ValueError('Title must be at least 5 characters')
           return v
       
       @validator('content')
       def content_not_empty(cls, v):
           if not v.strip():
               raise ValueError('Content cannot be empty')
           return v

Migration Strategies
--------------------

1. API-First Migration (Recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Extract Django API functionality into Tatami:

**Step 1: Identify API endpoints**

.. code-block:: python

   # Django - mixed web + API
   # views.py
   def post_list_html(request):  # Web view
       return render(request, 'posts.html')
   
   def post_list_api(request):   # API view
       posts = Post.objects.all()
       return JsonResponse([serialize(p) for p in posts])

**Step 2: Extract to Tatami API**

.. code-block:: python

   # Tatami - pure API
   class Posts(router('/api/posts')):
       @get('/')
       def list_posts(self) -> List[Post]:
           return self.post_service.get_all()

**Step 3: Update Django to use Tatami API**

.. code-block:: python

   # Django - consume Tatami API
   import httpx
   
   def post_list_html(request):
       response = httpx.get('http://api.example.com/api/posts')
       posts = response.json()
       return render(request, 'posts.html', {'posts': posts})

2. Gradual Router Migration
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Migrate Django apps one by one:

.. code-block::

   # Django app structure
   myproject/
   ├── blog/           # Migrate first
   ├── users/          # Migrate second  
   ├── comments/       # Migrate third
   └── notifications/  # Migrate last

.. code-block::

   # Tatami equivalent
   tatami-api/
   ├── routers/
   │   ├── blog.py     # Migrated from blog app
   │   ├── users.py    # Migrated from users app
   │   └── comments.py # Migrated from comments app
   └── services/       # Business logic extracted

3. Microservice Split
^^^^^^^^^^^^^^^^^^^^^

Use Tatami for new microservices:

.. code-block::

   # Keep Django for web frontend
   django-web/
   ├── templates/
   ├── static/
   └── views.py  # Renders HTML, calls APIs
   
   # New Tatami API services
   tatami-api/
   ├── user-service/    # User management
   ├── post-service/    # Content management
   └── auth-service/    # Authentication

Common Migration Patterns
-------------------------

Django Admin → Custom Admin Interface
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Django Admin:**

.. code-block:: python

   # admin.py
   from django.contrib import admin
   from .models import Post
   
   @admin.register(Post)
   class PostAdmin(admin.ModelAdmin):
       list_display = ['title', 'author', 'created_at']
       list_filter = ['author', 'created_at']
       search_fields = ['title', 'content']

**Tatami Admin API:**

.. code-block:: python

   # routers/admin.py
   class Admin(router('/admin')):
       def __init__(self, post_service: PostService):
           self.post_service = post_service
       
       @get('/posts')
       def list_posts(
           self,
           author: Optional[str] = None,
           search: Optional[str] = None
       ) -> List[Post]:
           return self.post_service.admin_list(author, search)

Django Authentication → JWT/Custom Auth
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Django Authentication:**

.. code-block:: python

   # Django views
   from django.contrib.auth.decorators import login_required
   
   @login_required
   def protected_view(request):
       return JsonResponse({'user': request.user.username})

**Tatami Authentication:**

.. code-block:: python

   # middleware/auth_middleware.py
   from starlette.middleware.base import BaseHTTPMiddleware
   
   class AuthMiddleware(BaseHTTPMiddleware):
       async def dispatch(self, request, call_next):
           # JWT validation logic
           response = await call_next(request)
           return response
   
   # routers/protected.py
   class Protected(router('/protected')):
       def __init__(self, auth_service: AuthService):
           self.auth_service = auth_service
       
       @get('/')
       def protected_endpoint(self, request) -> dict:
           user = self.auth_service.get_current_user(request)
           return {'user': user.username}

Django Signals → Event Services
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Django Signals:**

.. code-block:: python

   # signals.py
   from django.db.models.signals import post_save
   from django.dispatch import receiver
   from .models import Post
   
   @receiver(post_save, sender=Post)
   def post_created(sender, instance, created, **kwargs):
       if created:
           send_notification(instance.author, f"Post '{instance.title}' created")

**Tatami Event Services:**

.. code-block:: python

   # services/post_service.py
   class PostService:
       def __init__(self, notification_service: NotificationService):
           self.notification_service = notification_service
       
       def create_post(self, post_data: PostCreate) -> Post:
           post = self.post_repository.create(post_data)
           # Explicit event handling
           self.notification_service.send_post_created(post)
           return post

Django Middleware → Tatami Middleware
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Django Middleware:**

.. code-block:: python

   # middleware.py
   class CustomMiddleware:
       def __init__(self, get_response):
           self.get_response = get_response
       
       def __call__(self, request):
           # Process request
           request.custom_header = request.META.get('HTTP_X_CUSTOM')
           response = self.get_response(request)
           # Process response
           response['X-Custom-Response'] = 'processed'
           return response

**Tatami Middleware:**

.. code-block:: python

   # middleware/custom_middleware.py
   from starlette.middleware.base import BaseHTTPMiddleware
   
   class CustomMiddleware(BaseHTTPMiddleware):
       async def dispatch(self, request, call_next):
           # Process request
           custom_header = request.headers.get('x-custom')
           request.state.custom_data = custom_header
           
           response = await call_next(request)
           
           # Process response
           response.headers['x-custom-response'] = 'processed'
           return response

Configuration Migration
-----------------------

Django Settings → Tatami Config
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Django settings.py:**

.. code-block:: python

   # settings.py
   import os
   from pathlib import Path
   
   BASE_DIR = Path(__file__).resolve().parent.parent
   
   SECRET_KEY = os.environ.get('SECRET_KEY')
   DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
   
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': os.environ.get('DB_NAME'),
           'USER': os.environ.get('DB_USER'),
           'PASSWORD': os.environ.get('DB_PASSWORD'),
           'HOST': os.environ.get('DB_HOST', 'localhost'),
           'PORT': os.environ.get('DB_PORT', '5432'),
       }
   }
   
   INSTALLED_APPS = [
       'django.contrib.admin',
       'django.contrib.auth',
       'rest_framework',
       'blog',
       'users',
   ]

**Tatami config.yaml:**

.. code-block:: yaml

   # config.yaml
   app:
     name: "My API"
     secret_key: "${SECRET_KEY}"
     debug: false
   
   database:
     engine: "postgresql"
     name: "${DB_NAME}"
     user: "${DB_USER}"
     password: "${DB_PASSWORD}"
     host: "${DB_HOST:localhost}"
     port: "${DB_PORT:5432}"

.. code-block:: yaml

   # config-dev.yaml
   app:
     debug: true
   
   database:
     host: "localhost"
     name: "dev_db"

Database Migration
------------------

Django ORM → SQLAlchemy (Recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Django Models:**

.. code-block:: python

   # models.py
   from django.db import models
   
   class Post(models.Model):
       title = models.CharField(max_length=200)
       content = models.TextField()
       author = models.ForeignKey('auth.User', on_delete=models.CASCADE)
       tags = models.ManyToManyField('Tag', blank=True)
       created_at = models.DateTimeField(auto_now_add=True)

**SQLAlchemy Models:**

.. code-block:: python

   # repositories/models.py
   from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
   from sqlalchemy.ext.declarative import declarative_base
   from sqlalchemy.orm import relationship
   
   Base = declarative_base()
   
   class PostModel(Base):
       __tablename__ = 'posts'
       
       id = Column(Integer, primary_key=True)
       title = Column(String(200), nullable=False)
       content = Column(Text, nullable=False)
       author_id = Column(Integer, ForeignKey('users.id'))
       created_at = Column(DateTime, nullable=False)
       
       author = relationship("UserModel", back_populates="posts")

Repository Pattern
^^^^^^^^^^^^^^^^^^

.. code-block:: python

   # repositories/post_repository.py
   from typing import List, Optional
   from .models import PostModel
   
   class PostRepository:
       def __init__(self, db_session):
           self.db = db_session
       
       def find_all(self) -> List[Post]:
           models = self.db.query(PostModel).all()
           return [Post.from_orm(m) for m in models]
       
       def find_by_id(self, post_id: int) -> Optional[Post]:
           model = self.db.query(PostModel).get(post_id)
           return Post.from_orm(model) if model else None
       
       def create(self, post_data: PostCreate) -> Post:
           model = PostModel(**post_data.dict())
           self.db.add(model)
           self.db.commit()
           return Post.from_orm(model)

Testing Migration
-----------------

Django Tests → Tatami Tests
^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Django Tests:**

.. code-block:: python

   # tests.py
   from django.test import TestCase, Client
   from django.contrib.auth.models import User
   from .models import Post
   
   class PostTestCase(TestCase):
       def setUp(self):
           self.user = User.objects.create_user('testuser', 'test@example.com')
           self.client = Client()
       
       def test_create_post(self):
           response = self.client.post('/api/posts/', {
               'title': 'Test Post',
               'content': 'Test content',
               'author': self.user.id
           })
           self.assertEqual(response.status_code, 201)
           self.assertEqual(Post.objects.count(), 1)

**Tatami Tests:**

.. code-block:: python

   # tests/test_posts.py
   import httpx
   import pytest
   from tatami import BaseRouter
   from routers.posts import Posts
   from services.post_service import PostService
   
   def test_create_post():
       # Mock dependencies
       mock_service = Mock(spec=PostService)
       mock_service.create.return_value = Post(
           id=1, title="Test Post", content="Test content"
       )
       
       # Setup app
       app = BaseRouter()
       app.include_router(Posts(mock_service))
       
       # Test request
       with httpx.Client(app=app, base_url="http://test") as client:
           response = client.post("/posts/", json={
               'title': 'Test Post',
               'content': 'Test content',
               'author_id': 1
           })
           
           assert response.status_code == 201
           assert response.json()['title'] == 'Test Post'

Project Structure Comparison
----------------------------

Django Project Structure
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block::

   django-project/
   ├── manage.py
   ├── requirements.txt
   ├── myproject/
   │   ├── __init__.py
   │   ├── settings.py
   │   ├── urls.py
   │   └── wsgi.py
   ├── blog/                    # Django app
   │   ├── __init__.py
   │   ├── admin.py
   │   ├── apps.py
   │   ├── models.py
   │   ├── views.py
   │   ├── urls.py
   │   ├── serializers.py
   │   └── migrations/
   ├── users/                   # Django app
   │   ├── models.py
   │   ├── views.py
   │   └── urls.py
   ├── static/
   └── templates/

Tatami Project Structure
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block::

   tatami-project/
   ├── config.yaml              # Configuration
   ├── routers/                 # API endpoints (auto-discovered)
   │   ├── posts.py            # Blog functionality
   │   ├── users.py            # User management
   │   └── auth.py             # Authentication
   ├── services/               # Business logic (auto-discovered)
   │   ├── post_service.py     # Post operations
   │   ├── user_service.py     # User operations
   │   └── auth_service.py     # Authentication logic
   ├── repositories/           # Data access (auto-discovered)
   │   ├── post_repository.py  # Post data access
   │   └── user_repository.py  # User data access
   ├── middleware/             # Middleware (auto-discovered)
   │   ├── auth_middleware.py  # Authentication
   │   └── cors_middleware.py  # CORS handling
   ├── models/                 # Pydantic models
   │   ├── post.py
   │   └── user.py
   └── static/                 # Static files (auto-served)

Migration Advantages
--------------------

Performance
^^^^^^^^^^^

**Django:** 
- Synchronous by default
- Complex async configuration
- ORM can generate inefficient queries

**Tatami:**
- Async-first architecture
- Built on Starlette/ASGI
- Direct control over database queries

Development Speed
^^^^^^^^^^^^^^^^^

**Django:**

.. code-block:: python

   # Multiple files for simple CRUD
   # models.py
   class Post(models.Model): pass
   
   # serializers.py  
   class PostSerializer(serializers.ModelSerializer): pass
   
   # views.py
   class PostViewSet(viewsets.ModelViewSet): pass
   
   # urls.py
   router.register(r'posts', PostViewSet)

**Tatami:**

.. code-block:: python

   # Single file for simple CRUD
   class Posts(router('/posts')):
       @get('/')
       def list_posts(self) -> List[Post]: pass
       
       @post('/')
       def create_post(self, post: PostCreate) -> Post: pass

Type Safety
^^^^^^^^^^^

**Django:** Limited type hints, runtime errors

.. code-block:: python

   def get_posts(request):
       # No type hints for request/response
       posts = Post.objects.all()
       # Serialization can fail at runtime
       return JsonResponse([serialize(p) for p in posts])

**Tatami:** Full type safety throughout

.. code-block:: python

   @get('/')
   def list_posts(self) -> List[Post]:  # Return type enforced
       return self.post_service.get_all()  # Validated automatically

Migration Gotchas
-----------------

1. No Built-in Admin
^^^^^^^^^^^^^^^^^^^^

Django Admin doesn't translate directly. Consider:

- Build custom admin interface
- Use existing admin tools (Django Admin + API calls)
- Third-party admin solutions

2. Different Database Patterns
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Django uses Active Record pattern, Tatami uses Repository pattern:

.. code-block:: python

   # Django Active Record
   post = Post.objects.get(id=1)
   post.title = "Updated"
   post.save()

.. code-block:: python

   # Tatami Repository Pattern
   post = self.post_repository.find_by_id(1)
   updated_post = post.copy(update={'title': 'Updated'})
   self.post_repository.save(updated_post)

3. Authentication Differences
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Django has built-in user model and session auth. Tatami typically uses JWT:

.. code-block:: python

   # Django - built-in sessions
   if request.user.is_authenticated:
       pass

.. code-block:: python

   # Tatami - JWT/custom auth
   user = self.auth_service.verify_token(request.headers.get('authorization'))

Migration Checklist
-------------------

Planning Phase
^^^^^^^^^^^^^^

- [ ] **Audit Django project** - Identify API vs web functionality
- [ ] **Map Django apps** - Plan Tatami router organization  
- [ ] **Review models** - Plan Pydantic model structure
- [ ] **Identify dependencies** - What services need injection?
- [ ] **Plan database migration** - ORM to Repository pattern

Implementation Phase
^^^^^^^^^^^^^^^^^^^^

- [ ] **Create Tatami project** - `tatami create new-api`
- [ ] **Convert models** - Django models to Pydantic + SQLAlchemy
- [ ] **Migrate views** - Django views to Tatami routers
- [ ] **Extract services** - Business logic to service classes
- [ ] **Setup repositories** - Data access layer
- [ ] **Convert middleware** - Django to Starlette middleware

Testing Phase
^^^^^^^^^^^^^

- [ ] **Port tests** - Django tests to Tatami tests
- [ ] **Test endpoints** - Verify API functionality
- [ ] **Performance testing** - Compare response times
- [ ] **Integration testing** - Test with existing Django frontend

Deployment Phase
^^^^^^^^^^^^^^^^

- [ ] **Update CI/CD** - Use `tatami run` for deployment
- [ ] **Configure load balancer** - Route to Tatami API
- [ ] **Monitor performance** - Track API metrics
- [ ] **Plan rollback** - Keep Django API as backup

Why Migrate from Django?
------------------------

For **API-focused projects**, Tatami offers:

- 🚀 **Better Performance** - Async-first architecture  
- 🧹 **Cleaner Code** - Less boilerplate, better organization  
- ⚡ **Faster Development** - Convention over configuration  
- 🔒 **Type Safety** - Catch errors at development time  
- 📦 **Modern Patterns** - Built for current Python practices  
- 🛠️ **Better Testing** - Clear dependencies, easy mocking  

The migration effort creates a more maintainable, performant API! 🎋

*Note: Keep Django for admin interfaces and complex web apps. Use Tatami for clean, fast APIs.*
