Docker Deployment 🐳
===================

Learn how to containerize and deploy your Tatami applications using Docker.

Why Docker?
-----------

Docker provides:

- ✅ **Consistent environments** across development and production  
- ✅ **Easy deployment** to any platform that supports containers  
- ✅ **Isolation** from host system dependencies  
- ✅ **Scalability** with orchestration tools  

Creating a Dockerfile
---------------------

Create a `Dockerfile` in your project root:

.. code-block:: dockerfile

   # Use Python 3.11 slim image
   FROM python:3.11-slim

   # Set working directory
   WORKDIR /app

   # Install system dependencies
   RUN apt-get update && apt-get install -y \
       gcc \
       && rm -rf /var/lib/apt/lists/*

   # Copy requirements first for better caching
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   # Copy application code
   COPY . .

   # Expose port
   EXPOSE 8000

   # Run the application
   CMD ["tatami", "run", ".", "--host", "0.0.0.0", "--port", "8000"]

Building and Running
--------------------

Build your Docker image:

.. code-block:: bash

   docker build -t my-tatami-app .

Run the container:

.. code-block:: bash

   docker run -p 8000:8000 my-tatami-app

Your API will be available at http://localhost:8000

Docker Compose for Development
------------------------------

Create `docker-compose.yml` for development with database:

.. code-block:: yaml

   version: '3.8'
   
   services:
     app:
       build: .
       ports:
         - "8000:8000"
       environment:
         - DATABASE_URL=postgresql://user:password@db:5432/myapp
         - TATAMI_MODE=dev
       volumes:
         - .:/app  # Mount source for development
       depends_on:
         - db
       command: tatami run . --mode dev --host 0.0.0.0
     
     db:
       image: postgres:13
       environment:
         POSTGRES_DB: myapp
         POSTGRES_USER: user
         POSTGRES_PASSWORD: password
       volumes:
         - postgres_data:/var/lib/postgresql/data
       ports:
         - "5432:5432"

   volumes:
     postgres_data:

Run with Docker Compose:

.. code-block:: bash

   docker-compose up

Production Deployment
---------------------

For production, create a separate `docker-compose.prod.yml`:

.. code-block:: yaml

   version: '3.8'
   
   services:
     app:
       build: .
       ports:
         - "80:8000"
       environment:
         - DATABASE_URL=postgresql://user:password@db:5432/myapp
         - TATAMI_MODE=prod
       depends_on:
         - db
       restart: unless-stopped
     
     db:
       image: postgres:13
       environment:
         POSTGRES_DB: myapp
         POSTGRES_USER: user
         POSTGRES_PASSWORD: password
       volumes:
         - postgres_data:/var/lib/postgresql/data
       restart: unless-stopped

   volumes:
     postgres_data:

Deploy to production:

.. code-block:: bash

   docker-compose -f docker-compose.prod.yml up -d

Multi-Stage Builds
------------------

Optimize your Docker image with multi-stage builds:

.. code-block:: dockerfile

   # Build stage
   FROM python:3.11-slim as builder

   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --user --no-cache-dir -r requirements.txt

   # Production stage  
   FROM python:3.11-slim

   # Copy Python packages from builder
   COPY --from=builder /root/.local /root/.local

   WORKDIR /app
   COPY . .

   # Make sure scripts in .local are usable
   ENV PATH=/root/.local/bin:$PATH

   EXPOSE 8000
   CMD ["tatami", "run", ".", "--host", "0.0.0.0", "--port", "8000"]

Environment Variables
---------------------

Configure your application using environment variables:

.. code-block:: dockerfile

   # In Dockerfile
   ENV TATAMI_MODE=prod
   ENV DATABASE_URL=sqlite:///./app.db

.. code-block:: yaml

   # In docker-compose.yml
   services:
     app:
       environment:
         - TATAMI_MODE=${ENVIRONMENT:-dev}
         - DATABASE_URL=${DATABASE_URL}
         - SECRET_KEY=${SECRET_KEY}

Create a `.env` file:

.. code-block::

   ENVIRONMENT=dev
   DATABASE_URL=postgresql://user:pass@localhost:5432/myapp
   SECRET_KEY=your-secret-key-here

Health Checks
-------------

Add health checks to your Docker containers:

.. code-block:: dockerfile

   # In Dockerfile
   HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
     CMD curl -f http://localhost:8000/health || exit 1

Create a health endpoint in your router:

.. code-block:: python

   # routers/health.py
   from tatami import router, get

   class Health(router('/health')):
       @get('/')
       def health_check(self):
           return {"status": "healthy", "service": "tatami-api"}

Cloud Deployment Examples
-------------------------

Deploy to AWS ECS
^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Build and push to ECR
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com
   docker build -t my-tatami-app .
   docker tag my-tatami-app:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/my-tatami-app:latest
   docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/my-tatami-app:latest

Deploy to Google Cloud Run
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Build and deploy
   gcloud builds submit --tag gcr.io/PROJECT-ID/my-tatami-app
   gcloud run deploy --image gcr.io/PROJECT-ID/my-tatami-app --platform managed

Deploy to Azure Container Instances
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Create container group
   az container create --resource-group myResourceGroup --name my-tatami-app --image my-tatami-app:latest --ports 8000

Best Practices
--------------

🚀 **Performance**
^^^^^^^^^^^^^^^^^

- Use slim base images to reduce size
- Leverage multi-stage builds for production
- Use .dockerignore to exclude unnecessary files

🔒 **Security**
^^^^^^^^^^^^^^

- Run as non-root user in production
- Use specific image tags, not `latest`
- Scan images for vulnerabilities

📊 **Monitoring**
^^^^^^^^^^^^^^^^

- Include health checks
- Use proper logging configuration
- Monitor container metrics

Example .dockerignore
---------------------

Create a `.dockerignore` file to exclude unnecessary files:

.. code-block::

   .git
   .gitignore
   README.md
   Dockerfile
   .dockerignore
   .pytest_cache
   __pycache__
   *.pyc
   *.pyo
   *.pyd
   .env
   .venv
   tests/
   docs/

What's Next?
------------

Learn about migration guides from other frameworks and advanced deployment strategies.
