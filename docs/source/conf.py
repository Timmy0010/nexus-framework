# Configuration file for the Sphinx documentation builder.

# -- Project information -----------------------------------------------------
project = 'Nexus Framework'
copyright = '2025, Nexus Framework Team'
author = 'Nexus Framework Team'

# The full version, including alpha/beta/rc tags
release = '0.1.0'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.coverage',
    'myst_parser',
]

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# -- Extension configuration -------------------------------------------------
autodoc_member_order = 'bysource'
autodoc_typehints = 'description'
intersphinx_mapping = {'python': ('https://docs.python.org/3', None)}

# -- MyST configuration ------------------------------------------------------
myst_enable_extensions = [
    'colon_fence',
    'deflist',
]
myst_heading_anchors = 3
