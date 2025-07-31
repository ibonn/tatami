tatami.__main__ module (CLI)
============================

The command-line interface module for Tatami. This module provides the CLI commands
for creating, running, and diagnosing Tatami projects.

**Main Commands:**

- ``tatami create <project>`` - Create a new Tatami project
- ``tatami run <project>`` - Run a Tatami application  
- ``tatami doctor <project>`` - Diagnose project issues

.. note::
   This module contains executable code and is documented manually to avoid 
   import issues during documentation build.

**Usage Examples:**

.. code-block:: bash

   # Create a new project
   tatami create my-api
   
   # Run the project
   tatami run my-api
   
   # Check project health
   tatami doctor my-api

For complete CLI documentation, see :doc:`../../cli/commands`.
