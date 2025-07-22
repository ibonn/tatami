The Tatami CLI 🎛️
=============

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

The CLI is optional and meant to help smooth over common workflows. If you're more comfortable wiring things up yourself with `from tatami import run`, that's totally fine.

Want more CLI features? Open an issue or send a PR! 🛠️
