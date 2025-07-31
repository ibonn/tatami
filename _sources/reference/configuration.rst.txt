Configuration Guide 🔧
=====================

Complete guide to configuring Tatami applications.

Configuration Files
-------------------

YAML Configuration
~~~~~~~~~~~~~~~~~~

Tatami uses YAML configuration files for clean, readable configuration:

.. code-block:: yaml

   # config.yaml
   app:
     name: "My API"
     version: "1.0.0"
     debug: false
   
   server:
     host: "0.0.0.0"
     port: 8000
   
   database:
     url: "postgresql://user:pass@localhost/db"
     echo: false
   
   features:
     auto_reload: false
     cors_enabled: true

Environment-Specific Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Override settings for different environments:

.. code-block:: yaml

   # config-dev.yaml (development)
   app:
     debug: true
   
   server:
     port: 8001
   
   features:
     auto_reload: true

.. code-block:: yaml

   # config-prod.yaml (production)
   server:
     workers: 4
   
   features:
     auto_reload: false

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

Use environment variable interpolation:

.. code-block:: yaml

   app:
     secret_key: "${SECRET_KEY}"
     debug: "${DEBUG:false}"
   
   database:
     url: "${DATABASE_URL}"

Configuration Loading
---------------------

Tatami automatically loads configuration in this order:

1. ``config.yaml`` (base configuration)
2. ``config-{mode}.yaml`` (environment-specific)
3. Environment variables (overrides)

Set the mode with the ``TATAMI_MODE`` environment variable:

.. code-block:: bash

   export TATAMI_MODE=dev
   tatami run

Configuration Validation
------------------------

All configuration is validated at startup using Pydantic models.

Application Settings
--------------------

App Configuration
~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   app:
     name: "My Application"          # Application name
     version: "1.0.0"               # Version string
     description: "API description"  # OpenAPI description
     debug: false                   # Debug mode
     secret_key: "your-secret"      # Application secret

Server Configuration
~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   server:
     host: "0.0.0.0"               # Bind address
     port: 8000                    # Port number
     workers: 1                    # Worker processes
     reload: false                 # Auto-reload on changes
     log_level: "info"             # Logging level

Database Configuration
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   database:
     url: "sqlite:///app.db"       # Database URL
     echo: false                   # Log SQL queries
     pool_size: 5                  # Connection pool size
     max_overflow: 10              # Max overflow connections

Feature Toggles
~~~~~~~~~~~~~~~

.. code-block:: yaml

   features:
     auto_reload: false            # Development auto-reload
     cors_enabled: true            # Enable CORS
     openapi_enabled: true         # Generate OpenAPI docs
     metrics_enabled: false        # Enable metrics collection

Custom Configuration
--------------------

Adding Custom Settings
~~~~~~~~~~~~~~~~~~~~~~

Extend the configuration with custom sections:

.. code-block:: yaml

   # config.yaml
   custom:
     external_api_url: "https://api.example.com"
     rate_limit: 100
     feature_flags:
       new_feature: true

Accessing Configuration
~~~~~~~~~~~~~~~~~~~~~~~

Access configuration in your application:

.. code-block:: python

   from tatami.config import get_config
   
   config = get_config()
   
   # Access nested values
   api_url = config.custom.external_api_url
   rate_limit = config.custom.rate_limit
   
   # Check feature flags
   if config.custom.feature_flags.new_feature:
       # Use new feature
       pass

Configuration Schemas
~~~~~~~~~~~~~~~~~~~~~

Define schemas for custom configuration:

.. code-block:: python

   # config/schemas.py
   from pydantic import BaseModel
   
   class CustomConfig(BaseModel):
       external_api_url: str
       rate_limit: int = 100
       feature_flags: dict = {}

.. code-block:: python

   # Use in services
   class ExternalAPIService:
       def __init__(self):
           config = get_config()
           self.api_url = config.custom.external_api_url

Best Practices
--------------

Configuration Security
~~~~~~~~~~~~~~~~~~~~~~

- Never commit secrets to version control
- Use environment variables for sensitive data
- Rotate secrets regularly
- Use different secrets per environment

.. code-block:: yaml

   # ✅ Good - use environment variables
   database:
     password: "${DB_PASSWORD}"
   
   # ❌ Bad - hardcoded secrets
   database:
     password: "mypassword123"

Environment Management
~~~~~~~~~~~~~~~~~~~~~~

Organize configuration by environment:

.. code-block::

   config/
   ├── config.yaml              # Base configuration
   ├── config-dev.yaml          # Development overrides
   ├── config-staging.yaml      # Staging overrides
   ├── config-prod.yaml         # Production overrides
   └── config-test.yaml         # Test environment

Validation and Defaults
~~~~~~~~~~~~~~~~~~~~~~~

Always provide sensible defaults:

.. code-block:: yaml

   server:
     host: "${HOST:0.0.0.0}"      # Default to 0.0.0.0
     port: "${PORT:8000}"          # Default to 8000
     workers: "${WORKERS:1}"       # Default to 1 worker

Configuration Examples
----------------------

Development Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   # config-dev.yaml
   app:
     debug: true
   
   server:
     port: 8001
     reload: true
     log_level: "debug"
   
   database:
     url: "sqlite:///dev.db"
     echo: true
   
   features:
     auto_reload: true
     cors_enabled: true

Production Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   # config-prod.yaml
   app:
     debug: false
   
   server:
     host: "0.0.0.0"
     port: 8000
     workers: 4
     log_level: "warning"
   
   database:
     url: "${DATABASE_URL}"
     pool_size: 20
   
   features:
     auto_reload: false
     metrics_enabled: true

Docker Configuration
~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   # config-docker.yaml
   server:
     host: "0.0.0.0"
     port: 8000
   
   database:
     url: "${DATABASE_URL}"
   
   features:
     cors_enabled: true

Troubleshooting
---------------

Common Configuration Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Configuration file not found:**

.. code-block:: bash

   ERROR: Configuration file 'config.yaml' not found

Ensure ``config.yaml`` exists in your project root.

**Environment variable not set:**

.. code-block:: bash

   ERROR: Environment variable 'DATABASE_URL' is required

Set required environment variables:

.. code-block:: bash

   export DATABASE_URL="postgresql://..."

**Invalid configuration format:**

.. code-block:: bash

   ERROR: Invalid YAML syntax in config.yaml

Validate your YAML syntax using a YAML parser.

Configuration Validation
~~~~~~~~~~~~~~~~~~~~~~~~

Use ``tatami doctor`` to validate configuration:

.. code-block:: bash

   tatami doctor
   
   ✅ Configuration valid
   ✅ All required environment variables set
   ✅ Database connection successful
