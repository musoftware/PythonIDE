"""User keybindings.json - VS Code's "Preferences: Open Keyboard Shortcuts (JSON)".

The file (next to the VS Code extensions' settings.json, radide/vsx/contrib_configuration.settings_path()) is a
JSON array (comments and trailing commas allowed, like VS Code's JSONC) of
    {"key": "ctrl+alt+r", "command": "workbench.action.files.revert", "when": "editorTextFocus", "args": {...}}
Rules applied in order after the extensions' contributes.keybindings (VS Code: user rules win):
  * a normal rule adds a binding;
  * "command": "-id" removes the earlier bindings of that command (only those on "key" when a key is given,
    only those with the same "when" when one is given).
contrib_keybindings.collect() calls ``apply``; the result binds in Monaco (editor commands, when clauses) and as
window shortcuts (other commands) - radide/vsx/contrib_runtime.py. No Qt import."""
from __future__ import annotations

import json
import re
from pathlib import Path

TEMPLATE = """// Place your key bindings in this file to override the defaults (VS Code format).
// Example:
//   { "key": "ctrl+alt+l", "command": "editor.action.formatDocument", "when": "editorTextFocus" },
//   { "key": "ctrl+k ctrl+w", "command": "-workbench.action.closeAllEditors" }
[
]
"""


def path() -> Path:
    from .contrib_configuration import settings_path
    return settings_path().with_name("keybindings.json")


def strip_jsonc(text: str) -> str:
    """Remove // and /* */ comments (outside strings) and trailing commas."""
    out, i, n, in_str = [], 0, len(text), False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
        else:
            out.append(c)
            i += 1
    return re.sub(r",(\s*[\]}])", r"\1", "".join(out))


def load() -> list[dict]:
    try:
        data = json.loads(strip_jsonc(path().read_text("utf-8")))
    except (OSError, ValueError):
        return []
    return [r for r in data if isinstance(r, dict) and isinstance(r.get("command"), str)] if isinstance(data, list) else []


def ensure_file() -> Path:
    p = path()
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(TEMPLATE, "utf-8")
    return p


def apply(bindings: list[dict], rules: list[dict] | None = None) -> list[dict]:
    """bindings (contrib_keybindings.collect items) with the user's rules applied."""
    from .contrib_keybindings import is_monaco_command, platform_key
    out = list(bindings)
    for r in (load() if rules is None else rules):
        cmd = r["command"]
        key = platform_key(r)
        when = str(r.get("when") or "")
        if cmd.startswith("-"):
            out = [b for b in out if not (b["command"] == cmd[1:] and (not key or b["key"] == key)
                                          and (not when or b.get("when", "") == when))]
            continue
        if not key:
            continue
        item = {"key": key, "command": cmd, "when": when, "ext": "user",
                "target": "monaco" if is_monaco_command(cmd) else "ide", "title": cmd, "user": True}
        if "args" in r:
            item["args"] = r["args"]
        out.append(item)
    return out


__all__ = ["path", "load", "apply", "ensure_file", "strip_jsonc", "TEMPLATE"]
