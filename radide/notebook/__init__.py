"""Jupyter notebooks (.ipynb) inside RAD IDE.

* :mod:`radide.notebook.model`   - nbformat 4 documents (load / save / export to .py and HTML), no Qt.
* :mod:`radide.notebook.render`  - outputs and markdown to (sanitised) HTML, ANSI tracebacks.
* :mod:`radide.notebook.kernel`  - kernels through jupyter_client (any Python with ipykernel, other
  installed Jupyter kernels), run / interrupt / restart, completions, variables.
* :mod:`radide.notebook.view`    - the notebook editor tab (one QWebEngine page, one Monaco per cell).
* :mod:`radide.features.notebook` - IDE integration (File > New Notebook, open .ipynb, Variables dock).
"""
from __future__ import annotations

NOTEBOOK_EXT = ".ipynb"
