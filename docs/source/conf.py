"""Sphinx configuration for King and Servant documentation."""

import os
import sys

sys.path.insert(0, os.path.abspath("../.."))

project = "King and Servant"
copyright = "2026, Project-sovm Team"
author = "Project-sovm Team"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

html_theme = "alabaster"
autodoc_member_order = "bysource"
napoleon_google_docstring = True
