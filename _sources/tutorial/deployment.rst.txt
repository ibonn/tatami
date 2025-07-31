Deployment 🚀
============

Learn how to deploy your Tatami applications to production environments.

Production Deployment
---------------------

Deploy your Tatami app with proper production settings.

Docker Deployment
-----------------

Create a Docker container for your Tatami application:

.. code-block:: dockerfile

   # Dockerfile
   FROM python:3.11-slim

   WORKDIR /app

   COPY requirements.txt .
   RUN pip install -r requirements.txt

   COPY . .

   EXPOSE 8000

   CMD ["tatami", "run", ".", "--host", "0.0.0.0", "--port", "8000"]

Build and run:

.. code-block:: bash

   docker build -t my-tatami-app .
   docker run -p 8000:8000 my-tatami-app

Using Docker Compose
--------------------

For more complex deployments with databases:

.. code-block:: yaml

   # docker-compose.yml
   version: '3.8'
   
   services:
     app:
       build: .
       ports:
         - "8000:8000"
       environment:
         - DATABASE_URL=postgresql://user:pass@db:5432/myapp
       depends_on:
         - db
     
     db:
       image: postgres:13
       environment:
         POSTGRES_DB: myapp
         POSTGRES_USER: user
         POSTGRES_PASSWORD: pass
       volumes:
         - postgres_data:/var/lib/postgresql/data

   volumes:
     postgres_data:

Run with:

.. code-block:: bash

   docker-compose up

Cloud Deployment
----------------

Deploy to various cloud platforms using the Docker container approach.

What's Next?
------------

Explore advanced topics and class-based router patterns.
