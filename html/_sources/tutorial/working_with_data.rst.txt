Working with Data 🗄️
====================

This tutorial covers data handling in Tatami applications - from simple in-memory storage to full database integration with SQLAlchemy, plus validation, serialization, and best practices.

Data Layer Architecture
-----------------------

Tatami promotes a clean separation of concerns:

**🎯 Routers**: Handle HTTP requests/responses  
**🧠 Services**: Business logic and validation  
**🗄️ Repositories**: Data access and persistence  
**📋 Models**: Data structures and validation  

This pattern keeps your code organized and testable.

Setting Up Data Models
----------------------

Pydantic Models for API
^^^^^^^^^^^^^^^^^^^^^^^

Use Pydantic models for request/response validation:

.. code-block:: python

   # models/user_models.py
   from datetime import datetime
   from typing import Optional, List
   from pydantic import BaseModel, Field, EmailStr

   class UserBase(BaseModel):
       name: str = Field(min_length=1, max_length=100)
       email: EmailStr
       age: Optional[int] = Field(None, ge=13, le=120)

   class UserCreate(UserBase):
       password: str = Field(min_length=8)

   class UserUpdate(BaseModel):
       name: Optional[str] = Field(None, min_length=1, max_length=100)
       email: Optional[EmailStr] = None
       age: Optional[int] = Field(None, ge=13, le=120)

   class UserResponse(UserBase):
       id: int
       created_at: datetime
       updated_at: datetime
       is_active: bool = True

   class UserList(BaseModel):
       users: List[UserResponse]
       total: int
       page: int
       page_size: int

Database Models with SQLAlchemy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For database persistence, use SQLAlchemy:

.. code-block:: python

   # models/database.py
   from datetime import datetime
   from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
   from sqlalchemy.ext.declarative import declarative_base
   from sqlalchemy.orm import relationship

   Base = declarative_base()

   class User(Base):
       __tablename__ = "users"
       
       id = Column(Integer, primary_key=True, index=True)
       name = Column(String(100), nullable=False)
       email = Column(String(255), unique=True, index=True, nullable=False)
       password_hash = Column(String(255), nullable=False)
       age = Column(Integer, nullable=True)
       is_active = Column(Boolean, default=True)
       created_at = Column(DateTime, default=datetime.utcnow)
       updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

In-Memory Data Storage
----------------------

For simple applications or prototyping, start with in-memory storage:

.. code-block:: python

   # services/user_service.py
   from typing import List, Optional, Dict
   from datetime import datetime
   from tatami.di import injectable
   from models.user_models import UserCreate, UserUpdate, UserResponse

   @injectable
   class InMemoryUserService:
       def __init__(self):
           self.users: Dict[int, dict] = {}
           self.next_id = 1

       def create_user(self, user_data: UserCreate) -> UserResponse:
           # Check if email already exists
           if any(u["email"] == user_data.email for u in self.users.values()):
               raise ValueError("Email already registered")

           # Create user
           user = {
               "id": self.next_id,
               "name": user_data.name,
               "email": user_data.email,
               "age": user_data.age,
               "is_active": True,
               "created_at": datetime.utcnow(),
               "updated_at": datetime.utcnow(),
           }
           
           self.users[self.next_id] = user
           self.next_id += 1
           
           return UserResponse(**user)

       def get_user(self, user_id: int) -> Optional[UserResponse]:
           user = self.users.get(user_id)
           return UserResponse(**user) if user else None

       def get_users(self, skip: int = 0, limit: int = 100) -> List[UserResponse]:
           users = list(self.users.values())[skip:skip + limit]
           return [UserResponse(**user) for user in users]

       def update_user(self, user_id: int, updates: UserUpdate) -> Optional[UserResponse]:
           user = self.users.get(user_id)
           if not user:
               return None

           # Update only provided fields
           update_data = updates.dict(exclude_unset=True)
           for key, value in update_data.items():
               user[key] = value
           
           user["updated_at"] = datetime.utcnow()
           return UserResponse(**user)

       def delete_user(self, user_id: int) -> bool:
           return self.users.pop(user_id, None) is not None

Database Integration
--------------------

Setting Up SQLAlchemy
^^^^^^^^^^^^^^^^^^^^^

First, install the required packages:

.. code-block:: bash

   pip install sqlalchemy databases[sqlite] alembic

Create database configuration:

.. code-block:: python

   # config/database.py
   from sqlalchemy import create_engine
   from sqlalchemy.orm import sessionmaker
   from models.database import Base

   # Database URL (SQLite for development)
   DATABASE_URL = "sqlite:///./app.db"

   # Create engine
   engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

   # Create session factory
   SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

   # Create tables
   def create_tables():
       Base.metadata.create_all(bind=engine)

   # Dependency to get database session
   def get_db():
       db = SessionLocal()
       try:
           yield db
       finally:
           db.close()

Repository Pattern
^^^^^^^^^^^^^^^^^^

Create a repository for data access:

.. code-block:: python

   # repositories/user_repository.py
   from typing import List, Optional
   from sqlalchemy.orm import Session
   from models.database import User
   from models.user_models import UserCreate, UserUpdate

   class UserRepository:
       def __init__(self, db: Session):
           self.db = db

       def create(self, user_data: UserCreate) -> User:
           # Hash password (use bcrypt in real applications)
           password_hash = self._hash_password(user_data.password)
           
           db_user = User(
               name=user_data.name,
               email=user_data.email,
               age=user_data.age,
               password_hash=password_hash
           )
           
           self.db.add(db_user)
           self.db.commit()
           self.db.refresh(db_user)
           return db_user

       def get_by_id(self, user_id: int) -> Optional[User]:
           return self.db.query(User).filter(User.id == user_id).first()

       def get_by_email(self, email: str) -> Optional[User]:
           return self.db.query(User).filter(User.email == email).first()

       def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
           return self.db.query(User).offset(skip).limit(limit).all()

       def update(self, user_id: int, updates: UserUpdate) -> Optional[User]:
           user = self.get_by_id(user_id)
           if not user:
               return None

           update_data = updates.dict(exclude_unset=True)
           for key, value in update_data.items():
               setattr(user, key, value)

           self.db.commit()
           self.db.refresh(user)
           return user

       def delete(self, user_id: int) -> bool:
           user = self.get_by_id(user_id)
           if user:
               self.db.delete(user)
               self.db.commit()
               return True
           return False

       def _hash_password(self, password: str) -> str:
           # In real applications, use bcrypt or similar
           import hashlib
           return hashlib.sha256(password.encode()).hexdigest()

Service Layer with Database
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Update your service to use the repository:

.. code-block:: python

   # services/user_service.py
   from typing import List, Optional
   from sqlalchemy.orm import Session
   from tatami.di import injectable
   from repositories.user_repository import UserRepository
   from models.user_models import UserCreate, UserUpdate, UserResponse

   @injectable
   class UserService:
       def __init__(self, db: Session):
           self.user_repo = UserRepository(db)

       def create_user(self, user_data: UserCreate) -> UserResponse:
           # Check if email exists
           if self.user_repo.get_by_email(user_data.email):
               raise ValueError("Email already registered")

           # Create user
           user = self.user_repo.create(user_data)
           return self._to_response_model(user)

       def get_user(self, user_id: int) -> Optional[UserResponse]:
           user = self.user_repo.get_by_id(user_id)
           return self._to_response_model(user) if user else None

       def get_users(self, skip: int = 0, limit: int = 100) -> List[UserResponse]:
           users = self.user_repo.get_all(skip=skip, limit=limit)
           return [self._to_response_model(user) for user in users]

       def update_user(self, user_id: int, updates: UserUpdate) -> Optional[UserResponse]:
           user = self.user_repo.update(user_id, updates)
           return self._to_response_model(user) if user else None

       def delete_user(self, user_id: int) -> bool:
           return self.user_repo.delete(user_id)

       def _to_response_model(self, user) -> UserResponse:
           return UserResponse(
               id=user.id,
               name=user.name,
               email=user.email,
               age=user.age,
               is_active=user.is_active,
               created_at=user.created_at,
               updated_at=user.updated_at
           )

Router with Database Integration
--------------------------------

Create a router that uses the database-backed service:

.. code-block:: python

   # routers/users.py
   from typing import List
   from tatami import router, get, post, put, delete
   from tatami.param import Query
   from sqlalchemy.orm import Session
   from config.database import get_db
   from services.user_service import UserService
   from models.user_models import UserCreate, UserUpdate, UserResponse, UserList

   class Users(router('/users')):
       """User management with database backend"""

       @get
       def list_users(
           self,
           skip: int = Query(0, ge=0),
           limit: int = Query(100, ge=1, le=1000),
           db: Session = Depends(get_db)
       ) -> UserList:
           """Get paginated list of users"""
           user_service = UserService(db)
           users = user_service.get_users(skip=skip, limit=limit)
           
           # Get total count for pagination
           total = len(user_service.get_users(skip=0, limit=1000))  # Simple approach
           
           return UserList(
               users=users,
               total=total,
               page=skip // limit + 1,
               page_size=limit
           )

       @get('/{user_id}')
       def get_user(self, user_id: int, db: Session = Depends(get_db)) -> UserResponse:
           """Get user by ID"""
           user_service = UserService(db)
           user = user_service.get_user(user_id)
           
           if not user:
               return {"error": "User not found"}, 404
           
           return user

       @post('/')
       def create_user(self, user: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
           """Create a new user"""
           user_service = UserService(db)
           
           try:
               return user_service.create_user(user)
           except ValueError as e:
               return {"error": str(e)}, 400

       @put('/{user_id}')
       def update_user(
           self, 
           user_id: int, 
           updates: UserUpdate, 
           db: Session = Depends(get_db)
       ) -> UserResponse:
           """Update an existing user"""
           user_service = UserService(db)
           user = user_service.update_user(user_id, updates)
           
           if not user:
               return {"error": "User not found"}, 404
           
           return user

       @delete('/{user_id}')
       def delete_user(self, user_id: int, db: Session = Depends(get_db)) -> dict:
           """Delete a user"""
           user_service = UserService(db)
           
           if user_service.delete_user(user_id):
               return {"message": "User deleted successfully"}
           
           return {"error": "User not found"}, 404

Data Validation & Serialization
-------------------------------

Custom Validators
^^^^^^^^^^^^^^^^^

Create custom validation functions:

.. code-block:: python

   # validators/user_validators.py
   from pydantic import validator
   import re

   class UserCreate(BaseModel):
       name: str
       email: EmailStr
       password: str

       @validator('name')
       def validate_name(cls, v):
           if not v.strip():
               raise ValueError('Name cannot be empty')
           if len(v) < 2:
               raise ValueError('Name must be at least 2 characters')
           return v.title()  # Capitalize

       @validator('password')
       def validate_password(cls, v):
           if len(v) < 8:
               raise ValueError('Password must be at least 8 characters')
           if not re.search(r'[A-Z]', v):
               raise ValueError('Password must contain uppercase letter')
           if not re.search(r'[a-z]', v):
               raise ValueError('Password must contain lowercase letter')
           if not re.search(r'\d', v):
               raise ValueError('Password must contain a number')
           return v

Response Serialization
^^^^^^^^^^^^^^^^^^^^^^

Control what data is returned:

.. code-block:: python

   class UserResponse(BaseModel):
       id: int
       name: str
       email: str
       age: Optional[int]
       is_active: bool
       created_at: datetime

       class Config:
           # Automatically convert SQLAlchemy models
           from_attributes = True
           # Don't include password hash
           exclude = {'password_hash'}

Advanced Database Operations
----------------------------

Relationships and Joins
^^^^^^^^^^^^^^^^^^^^^^^

Define relationships between models:

.. code-block:: python

   # models/database.py
   from sqlalchemy import ForeignKey
   from sqlalchemy.orm import relationship

   class User(Base):
       __tablename__ = "users"
       
       id = Column(Integer, primary_key=True)
       name = Column(String(100), nullable=False)
       email = Column(String(255), unique=True, nullable=False)
       
       # Relationship to posts
       posts = relationship("Post", back_populates="author")

   class Post(Base):
       __tablename__ = "posts"
       
       id = Column(Integer, primary_key=True)
       title = Column(String(200), nullable=False)
       content = Column(Text, nullable=False)
       author_id = Column(Integer, ForeignKey("users.id"))
       
       # Relationship to user
       author = relationship("User", back_populates="posts")

Query Operations
^^^^^^^^^^^^^^^^

Implement complex queries:

.. code-block:: python

   # repositories/post_repository.py
   class PostRepository:
       def __init__(self, db: Session):
           self.db = db

       def get_posts_by_user(self, user_id: int) -> List[Post]:
           return self.db.query(Post).filter(Post.author_id == user_id).all()

       def search_posts(self, query: str) -> List[Post]:
           return self.db.query(Post).filter(
               Post.title.ilike(f"%{query}%") | 
               Post.content.ilike(f"%{query}%")
           ).all()

       def get_popular_posts(self, limit: int = 10) -> List[Post]:
           # Complex query with joins and aggregations
           return self.db.query(Post)\
               .join(User)\
               .order_by(Post.created_at.desc())\
               .limit(limit)\
               .all()

Database Migrations
-------------------

Use Alembic for database schema management:

.. code-block:: bash

   # Initialize Alembic
   alembic init alembic

   # Create migration
   alembic revision --autogenerate -m "Create users table"

   # Apply migration
   alembic upgrade head

Example migration file:

.. code-block:: python

   # alembic/versions/001_create_users.py
   from alembic import op
   import sqlalchemy as sa

   def upgrade():
       op.create_table('users',
           sa.Column('id', sa.Integer(), primary_key=True),
           sa.Column('name', sa.String(100), nullable=False),
           sa.Column('email', sa.String(255), nullable=False),
           sa.Column('created_at', sa.DateTime(), nullable=True),
       )
       op.create_index('ix_users_email', 'users', ['email'], unique=True)

   def downgrade():
       op.drop_index('ix_users_email', table_name='users')
       op.drop_table('users')

Testing Data Layer
------------------

Test your data operations:

.. code-block:: python

   # tests/test_user_service.py
   import pytest
   from sqlalchemy import create_engine
   from sqlalchemy.orm import sessionmaker
   from models.database import Base
   from services.user_service import UserService
   from models.user_models import UserCreate

   @pytest.fixture
   def test_db():
       # Create in-memory SQLite database for testing
       engine = create_engine("sqlite:///:memory:")
       Base.metadata.create_all(engine)
       SessionLocal = sessionmaker(bind=engine)
       return SessionLocal()

   def test_create_user(test_db):
       user_service = UserService(test_db)
       user_data = UserCreate(
           name="Test User",
           email="test@example.com",
           password="testpass123"
       )
       
       user = user_service.create_user(user_data)
       
       assert user.name == "Test User"
       assert user.email == "test@example.com"
       assert user.id is not None

Best Practices
--------------

🔐 Security
^^^^^^^^^^^^

- Never store plain text passwords
- Use parameterized queries to prevent SQL injection
- Validate and sanitize all input data
- Implement proper access controls

📊 Performance
^^^^^^^^^^^^^^^

- Use database indexes on frequently queried columns
- Implement pagination for large datasets
- Use lazy loading for relationships
- Consider caching for read-heavy operations

🧪 Testing
^^^^^^^^^^^

- Use separate test databases
- Mock external dependencies
- Test edge cases and error conditions
- Use factories for test data generation

🏗️ Architecture
^^^^^^^^^^^^^^^^

- Keep business logic in services
- Use repositories for data access
- Separate read and write models if needed
- Consider CQRS for complex domains

What's Next?
------------

You now know how to handle data in Tatami! Next topics:

- Dependency injection for better service management
- Middleware for request processing
- Testing strategies for data operations
- Advanced patterns like CQRS and event sourcing

Keep building great data-driven APIs! 📊
