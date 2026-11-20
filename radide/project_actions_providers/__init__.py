"""Project-actions providers (radide/project_actions.py, docs/PROJECT_ACTIONS.md).

Every module of this package is imported once (sorted by name, modules starting with "_" skipped) and
registers its providers with ``PROVIDERS = [MyProvider(), ...]`` (or a ``providers()`` function, or by calling
``radide.project_actions.register_provider``).  One module per area: ``generic.py`` (npm / composer scripts,
Makefile, VS Code tasks, pyproject scripts, justfile, Taskfile), ``laravel.py``, ``django.py`` ...
"""
