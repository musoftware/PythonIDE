"""Command registry of the automation channel (radide/automation/__init__.py).

A command is a function ``handler(ctx, **args) -> JSON-able`` registered with ``@command("name")``.
Handlers run on the GUI thread. Raise ``AutomationError`` (or any exception) to answer ``{"ok": false}``.

    from radide.automation.registry import command

    @command("hello_world", doc="answers 'hi'")
    def _hello(ctx, who="world"):
        return f"hi {who}"

``token=True`` marks commands that run arbitrary code in the IDE (exec / eval): they are refused unless the
channel was started with a token (RADIDE_AUTOMATION=<token>) and the request carries the same token.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


class AutomationError(Exception):
    pass


@dataclass
class Command:
    name: str
    func: Callable[..., Any]
    doc: str = ""
    token: bool = False          # needs the secret token (runs arbitrary code)
    module: str = ""


COMMANDS: dict[str, Command] = {}


def command(name: str, doc: str = "", token: bool = False):
    def deco(func):
        COMMANDS[name] = Command(name, func, doc or (func.__doc__ or "").strip().split("\n")[0], token,
                                 getattr(func, "__module__", ""))
        return func
    return deco


@dataclass
class Context:
    """What every handler gets: the main window, the QApplication and the server (jobs, options)."""
    win: Any
    app: Any
    server: Any = None
    has_token: bool = False
    data: dict = field(default_factory=dict)      # free-form state shared by command modules
