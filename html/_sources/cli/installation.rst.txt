Installation 📦
==============

Learn how to install Tatami and set up your development environment.

Requirements
------------

- Python 3.8 or higher
- pip (Python package installer)

Installation Methods
--------------------

Install from PyPI (Recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   pip install tatami

This installs the latest stable version of Tatami.

Install Development Version
^^^^^^^^^^^^^^^^^^^^^^^^^^^

For the latest features (may be unstable):

.. code-block:: bash

   git clone https://github.com/ibonn/tatami.git
   cd tatami
   pip install -e .

Virtual Environment (Recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Always use a virtual environment:

.. code-block:: bash

   python -m venv tatami-env
   
   # Windows
   tatami-env\Scripts\activate
   
   # macOS/Linux
   source tatami-env/bin/activate
   
   pip install tatami

Verify Installation
-------------------

Check that Tatami is installed correctly:

.. code-block:: bash

   tatami --help

You should see the available commands and options.

What's Next?
------------

Learn about the Tatami CLI commands and how to use them effectively.
