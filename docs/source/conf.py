# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys
# Add the project root directory to the Python path so Sphinx can import tatami
sys.path.insert(0, os.path.abspath('../..'))

from tatami import __version__

project = 'Tatami'
copyright = '2025, Ibon'
author = 'Ibon'
version = __version__
release = __version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.napoleon', 'sphinx.ext.viewcode', 'sphinx_copybutton']

templates_path = ['_templates']
exclude_patterns = []

# -- Autodoc configuration ---------------------------------------------------
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
    'special-members': '__init__',
}

# Mock imports for modules that might not be available during doc build
autodoc_mock_imports = []

# Don't import module for some problematic modules, just document the structure
# This is useful for __main__ modules that might execute code on import
autodoc_typehints = 'description'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'shibuya'    #
html_static_path = ['_static']
html_logo = '_static/tatami-logo.png'
html_favicon = '_static/favicon.ico'
html_theme_options = {
    "light_logo": "_static/tatami-logo-black.png",
    "dark_logo": "_static/tatami-logo-white.png",
}
