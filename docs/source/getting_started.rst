Getting Started
===============

Installation
------------

To install tatami, run:

.. code-block:: bash

   pip install tatami

Basic Usage
-----------

Here's a simple Hello World app:

.. code-block:: python

   from tatami import get, Tatami, run

   class App(Tatami):
      @get('/')
      async def hello(self):
         return 'Hello, world!'

   run(App())