"""Put first on PYTHONPATH by RAD IDE when it runs a Django project (radide/web_site/frameworks/django.py).

Django (4.1+) caches compiled templates even with DEBUG = True and only forgets them when its own
auto-reloader notices a change. The IDE reloads the Preview the moment a template is saved, and under the
debugger there is no auto-reloader at all - so with DEBUG = True (and no explicit "loaders" option) the
templates are loaded without the cached loader: every request sees the saved file.
Nothing is changed when RADIDE_DJANGO_FRESH_TEMPLATES is not "1" or for production settings.
"""
import os

if os.environ.get("RADIDE_DJANGO_FRESH_TEMPLATES") == "1":
    try:
        from django.template import engine as _engine

        _orig_init = _engine.Engine.__init__

        def _init(self, dirs=None, app_dirs=False, context_processors=None, debug=False, loaders=None,
                  *args, **kwargs):
            if loaders is None and debug:
                loaders = ["django.template.loaders.filesystem.Loader"]
                if app_dirs:
                    loaders.append("django.template.loaders.app_directories.Loader")
                app_dirs = False
            _orig_init(self, dirs, app_dirs, context_processors, debug, loaders, *args, **kwargs)

        _engine.Engine.__init__ = _init
    except Exception:  # noqa: BLE001 - Django missing / changed: run normally
        pass

# a sitecustomize of the project's own environment still runs
try:
    import importlib.util as _u
    import sys as _sys
    _here = os.path.dirname(os.path.abspath(__file__))
    for _p in _sys.path:
        if _p and os.path.abspath(_p) != _here and os.path.isfile(os.path.join(_p, "sitecustomize.py")):
            _spec = _u.spec_from_file_location("_project_sitecustomize", os.path.join(_p, "sitecustomize.py"))
            _spec.loader.exec_module(_u.module_from_spec(_spec))
            break
except Exception:  # noqa: BLE001
    pass
