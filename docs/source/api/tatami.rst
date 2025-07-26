Tatami API Reference 📘
========================

This section covers the main API of the Tatami framework. You'll find docs for the core components: routing, endpoint declarations, and helpers.

**Quick Import Reference:**

.. code-block:: python

   # Main router classes
   from tatami import BaseRouter, ConventionRouter, DecoratedRouter, router
   
   # HTTP method decorators  
   from tatami import get, post, put, patch, delete, head, options, request

Current version: ``0.0.1-pre.1``

.. automodule:: tatami
   :members:
   :undoc-members:
   :show-inheritance:

Submodules
----------

.. toctree::
   :maxdepth: 1

   _modules/tatami.core
   _modules/tatami.router
   _modules/tatami.endpoint
