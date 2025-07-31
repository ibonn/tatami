Your First API 📝
=================

In this tutorial, we'll build a complete blog API to demonstrate Tatami's features. You'll learn about models, validation, error handling, and more advanced routing patterns.

What We're Building
-------------------

We're creating a blog API with:

- 📝 **Posts**: Create, read, update, delete blog posts
- 👤 **Authors**: Manage author information  
- 🏷️ **Tags**: Categorize posts with tags
- 💬 **Comments**: Add comments to posts
- 🔍 **Search**: Find posts by title or content

Project Setup
-------------

Let's start with a fresh project:

.. code-block:: bash

   tatami create blog-api
   cd blog-api

First, let's understand the project structure that was created:

.. code-block::

   blog-api/
   ├── config.yaml          # Main configuration
   ├── config-dev.yaml      # Development-specific config  
   ├── README.md            # Project documentation
   ├── favicon.ico          # Your API's favicon
   ├── routers/             # 🎯 API endpoints (we'll focus here)
   ├── services/            # 🧠 Business logic layer
   ├── middleware/          # 🔄 Request/response processing
   ├── static/              # 📁 Static files (CSS, JS, images)
   └── templates/           # 📄 HTML templates

Understanding Routers vs Services
---------------------------------

**Routers** handle HTTP concerns:
- Route definitions (`@get`, `@post`, etc.)
- Request/response handling
- HTTP status codes
- Parameter extraction

**Services** handle business logic:
- Data access and manipulation
- Business rules and validation
- Pure Python functions
- No HTTP knowledge

This separation keeps your code clean and testable!

Creating Data Models
--------------------

First, let's create our data models. Create `routers/models.py`:

.. code-block:: python

   # routers/models.py
   from datetime import datetime
   from typing import List, Optional
   from pydantic import BaseModel, Field

   class Author(BaseModel):
       name: str = Field(..., min_length=1, max_length=100)
       email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
       bio: Optional[str] = Field(None, max_length=500)

   class Tag(BaseModel):
       name: str = Field(..., min_length=1, max_length=50)
       color: str = Field('#blue', regex=r'^#[a-zA-Z]+$')

   class PostCreate(BaseModel):
       title: str = Field(..., min_length=1, max_length=200)
       content: str = Field(..., min_length=1)
       author_id: int
       tags: List[str] = Field(default_factory=list)
       published: bool = False

   class PostUpdate(BaseModel):
       title: Optional[str] = Field(None, min_length=1, max_length=200)
       content: Optional[str] = Field(None, min_length=1)
       published: Optional[bool] = None
       tags: Optional[List[str]] = None

   class Post(BaseModel):
       id: int
       title: str
       content: str
       author_id: int
       author_name: str
       tags: List[str]
       published: bool
       created_at: datetime
       updated_at: datetime

   class Comment(BaseModel):
       id: int
       post_id: int
       author_name: str
       content: str
       created_at: datetime

   class CommentCreate(BaseModel):
       author_name: str = Field(..., min_length=1, max_length=100)
       content: str = Field(..., min_length=1, max_length=1000)

Creating a Service Layer
------------------------

Now let's create a service to handle our business logic. Create `services/blog_service.py`:

.. code-block:: python

   # services/blog_service.py
   from datetime import datetime
   from typing import List, Optional
   from tatami.di import injectable
   from routers.models import Author, Post, PostCreate, PostUpdate, Comment, CommentCreate

   @injectable
   class BlogService:
       def __init__(self):
           # In-memory storage for this example
           # In a real app, this would be a database
           self.posts = []
           self.authors = [
               {"id": 1, "name": "Alice Johnson", "email": "alice@example.com", "bio": "Tech writer"},
               {"id": 2, "name": "Bob Smith", "email": "bob@example.com", "bio": "Developer"},
           ]
           self.comments = []
           self.next_post_id = 1
           self.next_comment_id = 1

       def create_post(self, post_data: PostCreate) -> Post:
           author = next((a for a in self.authors if a["id"] == post_data.author_id), None)
           if not author:
               raise ValueError("Author not found")

           new_post = {
               "id": self.next_post_id,
               "title": post_data.title,
               "content": post_data.content,
               "author_id": post_data.author_id,
               "author_name": author["name"],
               "tags": post_data.tags,
               "published": post_data.published,
               "created_at": datetime.now(),
               "updated_at": datetime.now(),
           }
           self.posts.append(new_post)
           self.next_post_id += 1
           return Post(**new_post)

       def get_posts(self, published_only: bool = False) -> List[Post]:
           posts = self.posts
           if published_only:
               posts = [p for p in posts if p["published"]]
           return [Post(**post) for post in posts]

       def get_post(self, post_id: int) -> Optional[Post]:
           post = next((p for p in self.posts if p["id"] == post_id), None)
           return Post(**post) if post else None

       def update_post(self, post_id: int, updates: PostUpdate) -> Optional[Post]:
           post = next((p for p in self.posts if p["id"] == post_id), None)
           if not post:
               return None

           # Update only provided fields
           if updates.title is not None:
               post["title"] = updates.title
           if updates.content is not None:
               post["content"] = updates.content
           if updates.published is not None:
               post["published"] = updates.published
           if updates.tags is not None:
               post["tags"] = updates.tags
           
           post["updated_at"] = datetime.now()
           return Post(**post)

       def delete_post(self, post_id: int) -> bool:
           post = next((p for p in self.posts if p["id"] == post_id), None)
           if post:
               self.posts.remove(post)
               return True
           return False

       def search_posts(self, query: str) -> List[Post]:
           results = []
           query_lower = query.lower()
           for post in self.posts:
               if query_lower in post["title"].lower() or query_lower in post["content"].lower():
                   results.append(Post(**post))
           return results

       def get_authors(self) -> List[Author]:
           return [Author(**author) for author in self.authors]

       def add_comment(self, post_id: int, comment_data: CommentCreate) -> Optional[Comment]:
           post = next((p for p in self.posts if p["id"] == post_id), None)
           if not post:
               return None

           new_comment = {
               "id": self.next_comment_id,
               "post_id": post_id,
               "author_name": comment_data.author_name,
               "content": comment_data.content,
               "created_at": datetime.now(),
           }
           self.comments.append(new_comment)
           self.next_comment_id += 1
           return Comment(**new_comment)

       def get_comments(self, post_id: int) -> List[Comment]:
           post_comments = [c for c in self.comments if c["post_id"] == post_id]
           return [Comment(**comment) for comment in post_comments]

Creating the Posts Router
-------------------------

Now let's create our main posts router. Create `routers/posts.py`:

.. code-block:: python

   # routers/posts.py
   from typing import List, Optional
   from tatami import router, get, post, put, delete
   from tatami.param import Query
   from services.blog_service import BlogService
   from routers.models import Post, PostCreate, PostUpdate

   class Posts(router('/posts')):
       """Blog posts management"""
       
       def __init__(self, blog_service: BlogService):
           super().__init__()
           self.blog = blog_service

       @get
       def list_posts(self, published: Optional[bool] = Query(None)) -> List[Post]:
           """Get all posts, optionally filter by published status"""
           if published is not None:
               return self.blog.get_posts(published_only=published)
           return self.blog.get_posts()

       @get('/search')
       def search_posts(self, q: str = Query(...)) -> List[Post]:
           """Search posts by title or content"""
           if len(q.strip()) < 2:
               return {"error": "Search query must be at least 2 characters"}, 400
           return self.blog.search_posts(q)

       @get('/{post_id}')
       def get_post(self, post_id: int) -> Post:
           """Get a specific post by ID"""
           post = self.blog.get_post(post_id)
           if not post:
               return {"error": "Post not found"}, 404
           return post

       @post('/')
       def create_post(self, post: PostCreate) -> Post:
           """Create a new blog post"""
           try:
               return self.blog.create_post(post)
           except ValueError as e:
               return {"error": str(e)}, 400

       @put('/{post_id}')
       def update_post(self, post_id: int, updates: PostUpdate) -> Post:
           """Update an existing post"""
           post = self.blog.update_post(post_id, updates)
           if not post:
               return {"error": "Post not found"}, 404
           return post

       @delete('/{post_id}')
       def delete_post(self, post_id: int) -> dict:
           """Delete a post"""
           if self.blog.delete_post(post_id):
               return {"message": "Post deleted successfully"}
           return {"error": "Post not found"}, 404

Creating Additional Routers
---------------------------

Let's add routers for authors and comments. Create `routers/authors.py`:

.. code-block:: python

   # routers/authors.py
   from typing import List
   from tatami import router, get
   from services.blog_service import BlogService
   from routers.models import Author

   class Authors(router('/authors')):
       """Author management"""
       
       def __init__(self, blog_service: BlogService):
           super().__init__()
           self.blog = blog_service

       @get
       def list_authors(self) -> List[Author]:
           """Get all authors"""
           return self.blog.get_authors()

And create `routers/comments.py`:

.. code-block:: python

   # routers/comments.py
   from typing import List
   from tatami import router, get, post
   from services.blog_service import BlogService
   from routers.models import Comment, CommentCreate

   class Comments(router('/posts/{post_id}/comments')):
       """Post comments management"""
       
       def __init__(self, blog_service: BlogService):
           super().__init__()
           self.blog = blog_service

       @get
       def get_comments(self, post_id: int) -> List[Comment]:
           """Get all comments for a post"""
           return self.blog.get_comments(post_id)

       @post
       def add_comment(self, post_id: int, comment: CommentCreate) -> Comment:
           """Add a comment to a post"""
           result = self.blog.add_comment(post_id, comment)
           if not result:
               return {"error": "Post not found"}, 404
           return result

Running Your Blog API
---------------------

Now let's run our blog API:

.. code-block:: bash

   tatami run .

Your API is now running at http://localhost:8000!

Testing the API
---------------

Let's test our endpoints:

.. code-block:: bash

   # Get all posts
   curl http://localhost:8000/posts

   # Create a new post
   curl -X POST http://localhost:8000/posts \
        -H "Content-Type: application/json" \
        -d '{
          "title": "My First Blog Post",
          "content": "This is the content of my first post!",
          "author_id": 1,
          "tags": ["tutorial", "tatami"],
          "published": true
        }'

   # Search for posts
   curl "http://localhost:8000/posts/search?q=blog"

   # Get all authors
   curl http://localhost:8000/authors

   # Add a comment to post 1
   curl -X POST http://localhost:8000/posts/1/comments \
        -H "Content-Type: application/json" \
        -d '{
          "author_name": "John Doe",
          "content": "Great post! Thanks for sharing."
        }'

Exploring the Documentation
---------------------------

Visit http://localhost:8000/docs/ to see Tatami's documentation landing page with links to all available formats.

Then explore http://localhost:8000/docs/swagger for interactive API documentation. Notice how:

- All endpoints are automatically documented
- Request/response schemas are generated from your Pydantic models
- You can test endpoints directly from the docs
- Query parameters and path parameters are clearly shown

💡 **Pro Tip**: You can customize the documentation landing page by creating `templates/__tatami__/docs_landing.html` in your project!

What You've Learned
-------------------

In this tutorial, you've mastered:

🏗️ **Project Organization**: Separating routers, services, and models

📋 **Data Modeling**: Using Pydantic for validation and documentation

🎯 **Advanced Routing**: Query parameters, path parameters, and nested routes

- 🧠 **Service Layer**: Keeping business logic separate from HTTP concerns

- 🔍 **Search & Filtering**: Implementing search and filtering endpoints

- ❌ **Error Handling**: Returning appropriate HTTP status codes

- 🧪 **API Testing**: Testing your endpoints with curl

Next Steps
----------

Your blog API is working great! In the next tutorials, you'll learn about:

- Project structure best practices and conventions
- Advanced routing patterns and middleware
- Database integration and data persistence
- Dependency injection for better code organization
- Testing strategies for Tatami applications

Keep building amazing APIs! 🚀
