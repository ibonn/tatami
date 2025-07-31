Tatami API Reference 📘
======================

This section covers the main API of the Tatami framework. You'll find docs for the core components: routing, endpoint declarations, and helpers.

**Quick Import Reference:**

.. code-block:: python

   # Main router classes
   from tatami import BaseRouter, ConventionRouter, DecoratedRouter, router
   
   # HTTP method decorators  
   from tatami import get, post, put, patch, delete, head, options, request
   
   # Parameter types
   from tatami import Query, Path, Header
   
   # Validation utilities
   from tatami import ValidationException, validate_parameter

Current version: ``0.0.1-pre.1``

**Core Framework Components:**

.. toctree::
   :maxdepth: 1

   _modules/tatami.__main__
   _modules/tatami._utils
   _modules/tatami.config
   _modules/tatami.convention
   _modules/tatami.core
   _modules/tatami.di
   _modules/tatami.doctor
   _modules/tatami.endpoint
   _modules/tatami.openapi
   _modules/tatami.param
   _modules/tatami.responses
   _modules/tatami.router
   _modules/tatami.validation
