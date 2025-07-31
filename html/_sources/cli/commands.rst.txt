CLI Commands 🎛️
===============

Master the Tatami command-line interface for rapid development.

Available Commands
------------------

Tatami provides several CLI commands to help you build and manage your applications.

tatami create
-------------

Create a new Tatami project with the standard structure.

**Syntax:**

.. code-block:: bash

   tatami create <project_name>

**Example:**

.. code-block:: bash

   tatami create my-blog-api

This creates a new directory `my-blog-api` with the standard Tatami project structure:

.. code-block::

   my-blog-api/
   ├── config.yaml          # Main configuration  
   ├── config-dev.yaml      # Development config
   ├── README.md            # Project documentation
   ├── favicon.ico          # API favicon
   ├── routers/             # API endpoints
   ├── services/            # Business logic  
   ├── middleware/          # Request processing
   ├── static/              # Static files
   └── templates/           # HTML templates

tatami run
----------

Run a Tatami application using the convention-based approach.

**Syntax:**

.. code-block:: bash

   tatami run <project_path> [OPTIONS]

**Options:**

- `--host HOST` - Host to bind to (default: localhost)
- `--port PORT` - Port to bind to (default: 8000) 
- `--mode MODE` - Configuration mode (loads config-{mode}.yaml)
- `--verbose, -v` - Increase verbosity (-v for info, -vv for debug)

**Examples:**

.. code-block:: bash

   # Run with defaults
   tatami run my-blog-api

   # Run on all interfaces, port 8080
   tatami run my-blog-api --host 0.0.0.0 --port 8080

   # Run in development mode with verbose output  
   tatami run my-blog-api --mode dev --verbose

   # Run with debug logging
   tatami run my-blog-api -vv

**What happens when you run:**

1. 🔧 Loads configuration from `config.yaml` (and `config-{mode}.yaml` if specified)
2. 🔍 Auto-discovers routers in the `routers/` directory
3. 🧠 Auto-discovers services in the `services/` directory  
4. 🔄 Loads middleware from the `middleware/` directory
5. 📁 Serves static files from `static/` at `/static`
6. 📄 Configures templates from the `templates/` directory
7. 🎨 Includes favicon (custom or default)
8. 📚 Sets up automatic OpenAPI documentation
9. 🚀 Starts the server with uvicorn

tatami doctor
-------------

Analyze your project structure and report potential issues.

**Syntax:**

.. code-block:: bash

   tatami doctor <project_path>

**Example:**

.. code-block:: bash

   tatami doctor my-blog-api

**Sample Output:**

.. code-block::

   🩺 Tatami is checking your project...
   ✔ Configuration file found: config.yaml
   ✔ Routers directory exists and contains 3 router(s)
   ✔ Services directory exists and contains 2 service(s)
   ✔ Static files directory configured
   ✔ Templates directory configured
   ⚠ No middleware found - consider adding authentication middleware
   ℹ Consider adding a config-prod.yaml for production settings

   ✅ Your project looks good! Minor suggestions available.

**What doctor checks:**

- ✅ **Configuration**: Valid config files and structure
- ✅ **Routers**: Proper router definitions and naming
- ✅ **Services**: Service discovery and dependencies  
- ✅ **Structure**: Correct directory organization
- ⚠️ **Best Practices**: Common patterns and recommendations
- 🔍 **Performance**: Potential optimization opportunities

Command Examples
----------------

Development Workflow
^^^^^^^^^^^^^^^^^^^^

Typical development workflow using CLI commands:

.. code-block:: bash

   # 1. Create new project
   tatami create my-api
   cd my-api

   # 2. Check project health
   tatami doctor .

   # 3. Run in development mode
   tatami run . --mode dev --verbose

   # 4. Make changes to routers/services...

   # 5. Check project again
   tatami doctor .

   # 6. Run with debug logging
   tatami run . --mode dev -vv

Production Deployment
^^^^^^^^^^^^^^^^^^^^^

Prepare for production deployment:

.. code-block:: bash

   # Check project is production-ready
   tatami doctor my-api

   # Run in production mode (using config.yaml)
   tatami run my-api --host 0.0.0.0 --port 8000

Quick Prototyping
^^^^^^^^^^^^^^^^^

Rapid development cycle:

.. code-block:: bash

   # Create and run immediately
   tatami create quick-prototype
   cd quick-prototype
   tatami run . --mode dev &

   # Open API docs
   open http://localhost:8000/docs/swagger

Configuration Modes
-------------------

The `--mode` flag loads additional configuration:

**Default (no mode):**
- Loads `config.yaml`

**Development mode (`--mode dev`):**
- Loads `config.yaml` 
- Overlays `config-dev.yaml`

**Production mode (`--mode prod`):**
- Loads `config.yaml`
- Overlays `config-prod.yaml`

**Custom mode (`--mode staging`):**
- Loads `config.yaml`
- Overlays `config-staging.yaml`

Example configuration files:

.. code-block:: yaml

   # config.yaml (base configuration)
   app:
     title: "My API"
     version: "1.0.0"
   
   server:
     host: "localhost"
     port: 8000

.. code-block:: yaml

   # config-dev.yaml (development overrides)
   server:
     port: 8080
   
   features:
     debug: true
     auto_reload: true

.. code-block:: yaml

   # config-prod.yaml (production overrides)  
   server:
     host: "0.0.0.0"
   
   features:
     debug: false
     enable_cors: false

Verbose Output
--------------

Control logging verbosity with `-v` flags:

**Normal output:**
.. code-block::

   🌱 Tatami 0.0.1-pre.1
   Running app my-api on http://localhost:8000

**Verbose (`-v`):**
.. code-block::

   🌱 Tatami 0.0.1-pre.1
   Running app my-api on http://localhost:8000
        • Config: config.yaml
        • Routers: 3 discovered
        • Services: 2 loaded
        • Middleware: 1 loaded
        • Static files: static/
        • Templates: templates/

**Debug (`-vv`):**
.. code-block::

   🌱 Tatami 0.0.1-pre.1
   DEBUG: Loading configuration from config.yaml
   DEBUG: Discovered router: Users in routers/users.py
   DEBUG: Discovered router: Posts in routers/posts.py  
   DEBUG: Discovered service: UserService in services/user_service.py
   DEBUG: Loading middleware: AuthMiddleware
   Running app my-api on http://localhost:8000

CLI Best Practices
------------------

🚀 **Development**
^^^^^^^^^^^^^^^^^

Use development mode with auto-reload:

.. code-block:: bash

   tatami run . --mode dev --verbose

🏗️ **Project Health**
^^^^^^^^^^^^^^^^^^^^^

Run `doctor` regularly to catch issues early:

.. code-block:: bash

   # Add to your development workflow
   tatami doctor . && tatami run . --mode dev

📊 **Production**
^^^^^^^^^^^^^^^^

Use production configuration:

.. code-block:: bash

   tatami run . --mode prod --host 0.0.0.0 --port 8000

🔍 **Debugging**
^^^^^^^^^^^^^^^

Use debug logging for troubleshooting:

.. code-block:: bash

   tatami run . --mode dev -vv

Troubleshooting
---------------

Common Issues
^^^^^^^^^^^^^

**"Command not found: tatami"**
- Ensure Tatami is installed: `pip install tatami`
- Check if you're in the correct virtual environment

**"No module named 'tatami'"**
- Reinstall Tatami: `pip uninstall tatami && pip install tatami`

**"Port already in use"**
- Use a different port: `tatami run . --port 8080`
- Kill existing processes: `lsof -ti:8000 | xargs kill`

**"No routers found"**
- Check router files are in `routers/` directory
- Ensure router classes inherit from `router('/path')`
- Run `tatami doctor .` for detailed analysis

Getting Help
^^^^^^^^^^^^

.. code-block:: bash

   # General help
   tatami --help

   # Command-specific help
   tatami run --help
   tatami create --help
   tatami doctor --help

What's Next?
------------

Now that you've mastered the CLI, learn about Docker deployment and production configuration.
