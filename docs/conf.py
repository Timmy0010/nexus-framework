# Configuration file for the Sphinx documentation builder.

# -- Project information -----------------------------------------------------
project = 'Nexus Framework'
copyright = '2025, Nexus Framework Team'
author = 'Nexus Framework Team'

# The full version, including alpha/beta/rc tags
release = '0.1.1'

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



# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static'] # This path should exist relative to the source directory

# -- Options for Intersphinx -------------------------------------------------

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    # Add other projects you want to link to here
}

# -- Options for MyST-Parser -------------------------------------------------
# See https://myst-parser.readthedocs.io/en/stable/configuration.html
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "html_image",
    "linkify",
    "replacements",
    "smartquotes",
    "strikethrough",
    "substitution",
    "tasklist",
]


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
