The Tatami CLI 🎛️
Available Commands
------------------

Here's what's currently available:

**tatami create <project_name>**
  Creates a new Tatami project with the standard directory structure.
  
  .. code-block:: bash
  
     tatami create myapi
  
  This creates:
  
  .. code-block::
  
     myapi/
     ├── config.yaml
     ├── config-dev.yaml  
     ├── README.md
     ├── favicon.ico
     ├── routers/
     ├── middleware/
     ├── mounts/
     ├── static/
     └── templates/

**tatami run <project_path>**
  Runs a Tatami project using the convention-based structure.
  
  .. code-block:: bash
  
     tatami run myapi
     tatami run myapi --host 0.0.0.0 --port 8080
     tatami run myapi --mode dev --verbose
  
  Options:
  
  - ``--host`` - Host to bind to (default: localhost)
  - ``--port`` - Port to bind to (default: 8000)  
  - ``--mode`` - Configuration mode (loads config-{mode}.yaml)
  - ``--verbose, -v`` - Increase verbosity (use -vv for debug)
  - ``--server`` - Server backend (uvicorn or gunicorn, default: uvicorn)

**tatami doctor <project_path>**
  Analyzes your project structure and reports potential issues.
  
  .. code-block:: bash
  
     tatami doctor myapi
  
  *(Note: This command is planned but not yet fully implemented)*
Tatami comes with a (very humble) command-line interface to help you get started and interact with your project more easily. It’s still in early days, but here’s what you can do with it.

.. note::

   Just like the rest of Tatami, the CLI is **experimental** — things might change, break, or disappear. Use with curiosity and caution 😄

Basic Usage
-----------

If you’ve installed Tatami (either via PyPI or `pip install -e .`), you should be able to run:

.. code-block:: bash

   tatami --help

This will show the available commands.

Available Commands
------------------

Here’s a quick overview of what’s available (or coming soon):

- ``tatami new <project_name>``  
  Creates a new Tatami project scaffold. ✨  
  _(Work in progress — for now it might just create a dummy folder!)_

- ``tatami docs``  
  Launch a live preview of your OpenAPI docs in the browser.  
  _(This is planned — let us know if you need it!)_

- ``tatami run``  
  Future command to replace manual `run()` usage.  
  _(Not implemented yet — stay tuned!)_

Under the Hood
--------------

The CLI uses Tatami's convention-based project loading system. When you run ``tatami run``, it:

1. Searches for configuration files (config.yaml, config-{mode}.yaml)
2. Automatically discovers routers in the ``routers/`` directory
3. Loads middleware from the ``middleware/`` directory  
4. Mounts static files from ``static/`` at ``/static``
5. Sets up templates from the ``templates/`` directory
6. Includes a favicon (either your custom one or the default)
7. Starts the server with automatic OpenAPI documentation

The CLI provides a zero-configuration way to run Tatami applications following the framework's conventions. For more control, you can always wire things up manually using ``BaseRouter`` and the ``app.run()`` method.
