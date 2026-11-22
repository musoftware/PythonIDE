"""Opt-in automation channel: drive the real IDE (also the frozen RADIDE.exe, offscreen) from a test.

Never on by default. It starts only when

    RADIDE_AUTOMATION=<token>          (environment)  - every request must carry the token; exec/eval allowed
    RADIDE.exe --automation <name>     (command line) - pipe name; without the token exec/eval are refused

Other environment variables (only read when the channel is on):
    RADIDE_AUTOMATION_NAME=<name>      the QLocalServer / named pipe name (default radide-automation-<pid>)
    RADIDE_AUTOMATION_READY=<file>     written ({"name", "pid"}) once the server listens
    RADIDE_AUTOMATION_PLUGINS=<dirs>   extra command modules (*.py, os.pathsep separated); token only

Command modules: radide/automation/commands_*.py register handlers with
``radide.automation.registry.command``; ``help`` lists them. See docs/TESTING.md ("Automation channel")
and the client samples/Tests/E2E/radauto.py.
"""
from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path

BUILTIN = ("commands_core", "commands_widgets", "commands_ide", "commands_designer", "commands_editor",
           "commands_win32")
SERVER = None


def requested(cli_name: str | None = None) -> bool:
    return bool(os.environ.get("RADIDE_AUTOMATION") or cli_name)


def load_commands(extra_dirs: str = "") -> list[str]:
    loaded, errors = [], []
    for mod in BUILTIN:
        try:
            importlib.import_module(f"{__name__}.{mod}")
            loaded.append(mod)
        except Exception as e:  # noqa: BLE001 - one broken module must not stop the channel
            errors.append(f"{mod}: {e}")
    for d in [p for p in (extra_dirs or "").split(os.pathsep) if p.strip()]:
        for py in sorted(Path(d).glob("*.py"), key=lambda p: (p.stem != "widgets", p.stem)):
            if py.stem in ("__init__", "registry", "server"):
                continue
            # commands_*.py / widgets.py load as radide.automation.<name>: newer command code (e.g. this folder of
            # a source checkout) replaces the built-in module of an older build; other files are plain plugins
            same = py.stem.startswith("commands_") or py.stem == "widgets"
            try:
                name = f"{__name__}.{py.stem}" if same else f"radide_automation_plugin_{py.stem}"
                spec = importlib.util.spec_from_file_location(name, py)
                m = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = m
                spec.loader.exec_module(m)
                loaded.append(str(py))
            except Exception as e:  # noqa: BLE001
                errors.append(f"{py}: {e}")
    if errors:
        sys.__stderr__ and sys.__stderr__.write("[automation] " + "; ".join(errors) + "\n")
    return loaded


def maybe_start(win, app, cli_name: str | None = None):
    """Start the channel when requested (env / --automation); returns the server or None."""
    global SERVER
    if not requested(cli_name):
        return None
    token = os.environ.get("RADIDE_AUTOMATION", "")
    name = cli_name or os.environ.get("RADIDE_AUTOMATION_NAME") or f"radide-automation-{os.getpid()}"
    from .server import AutomationServer, write_ready_file
    load_commands(os.environ.get("RADIDE_AUTOMATION_PLUGINS", "") if token else "")
    SERVER = AutomationServer(win, app, name, token)
    try:
        win.log(f"[automation] channel open on '{name}'" + (" (token)" if token else ""))
    except Exception:  # noqa: BLE001
        pass
    ready = os.environ.get("RADIDE_AUTOMATION_READY")
    if ready:
        write_ready_file(ready, name)
    return SERVER
