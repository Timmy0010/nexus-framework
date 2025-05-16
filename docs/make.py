#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shutil

# Add the project root to Python's module path.
sys.path.insert(0, os.path.abspath('..'))

# -- Path setup --------------------------------------------------------------
from sphinx.cmd.build import build_main
from sphinx.ext import apidoc

# -- Project information -----------------------------------------------------
project = 'Nexus Framework'
copyright = '2025, Nexus Framework Team'
author = 'Nexus Framework Team'
release = '0.1.0'

# -- API documentation generation --------------------------------------------
def run_apidoc(_):
    # Generate API documentation
    modules = ['../nexus_framework']
    output_path = 'source/api'
    apidoc.main(['--force', '-o', output_path] + modules)

# -- General configuration ---------------------------------------------------
def setup(app):
    app.connect('builder-inited', run_apidoc)

# -- Generate HTML ----------------------------------------------------------
if __name__ == '__main__':
    # Create build directory if it doesn't exist
    if not os.path.exists('build'):
        os.makedirs('build')
    
    # Run Sphinx build
    sys.argv = ['sphinx-build', '-b', 'html', 'source', 'build/html']
    build_main(sys.argv)
    
    print('Documentation built successfully. Output in build/html/')
