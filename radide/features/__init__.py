"""Optional IDE features. Every module in this package that defines
install(win) is installed into the main window at start-up (sorted by name).
A feature must never break the IDE: errors are logged to the Output window."""
from __future__ import annotations

import importlib
import pkgutil
import traceback


def install_all(win) -> None:
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
