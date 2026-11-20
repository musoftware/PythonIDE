"""Optional IDE features. Every module in this package that defines
install(win) is installed into the main window at start-up (sorted by name).
A feature must never break the IDE: errors are logged to the Output window."""
from __future__ import annotations

import importlib
import pkgutil
import traceback


def _extensions(step: str, win) -> None:
    """Third-party extensions (radide/extensions, docs/PLUGIN_API.md), isolated like the features."""
    try:
        from .. import extensions
        extensions.preload(win) if step == "preload" else extensions.activate_all(win)
    except Exception:  # noqa: BLE001 - extensions must never stop the IDE
        try:
            win.log(f"[extensions] {step} failed:\n{traceback.format_exc()}")
        except Exception:  # noqa: BLE001
            traceback.print_exc()


def _vsx_contributions(win) -> None:
    """VS Code extensions' themes / languages / grammars / icons (radide/vsx/contrib_runtime.py): before the
    features, so Options applies a VS Code colour theme at start-up and files open with the right language."""
    try:
        from ..vsx import contrib_runtime
        contrib_runtime.install(win)
    except Exception:  # noqa: BLE001 - VS Code extensions must never stop the IDE
        try:
            win.log(f"[vsx] contributions failed:\n{traceback.format_exc()}")
        except Exception:  # noqa: BLE001
            traceback.print_exc()


def install_all(win) -> None:
    _extensions("preload", win)          # themes / languages / AI providers before the features
    _vsx_contributions(win)
    _install_features(win)
    _extensions("activate", win)         # extension code after every built-in feature


def _install_features(win) -> None:
    for mod in sorted(pkgutil.iter_modules(__path__), key=lambda m: m.name):
        if mod.name.startswith("_"):
            continue
        try:
            m = importlib.import_module(f"{__name__}.{mod.name}")
            install = getattr(m, "install", None)
            if callable(install):
                install(win)
        except Exception:  # noqa: BLE001 - a broken feature must not stop the IDE
            try:
                win.log(f"[feature {mod.name}] failed to load:\n{traceback.format_exc()}")
            except Exception:  # noqa: BLE001
                traceback.print_exc()
