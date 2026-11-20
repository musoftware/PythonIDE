"""VS Code keybindings (``contributes.keybindings``) -> Monaco actions and IDE commands.

Each binding {key, command, when, args, win/mac/linux} is mapped to
  * a Monaco command when one with the same id exists (editor.action.commentLine, cursorDown ...): bound in
    every editor page with the when clause as a Monaco context-key expression (editorTextFocus,
    editorLangId == x, resourceExtname == .x, isWindows ... - see contrib_runtime.context_keys);
  * otherwise an IDE command (``run_command``): a Command Palette command with that id, a VS Code workbench
    command with an IDE equivalent (VSCODE_TO_IDE), or a handler in COMMAND_HANDLERS (the extension host adds
    one for commands of extensions with code). Bindings without an editor-only when clause also get a window
    shortcut (unless the IDE already uses that key).
No Qt import at module level."""
from __future__ import annotations

import re

from .contrib_common import enabled_extensions

# commands that are Monaco editor actions / commands (same id in Monaco and VS Code)
MONACO_PREFIXES = ("editor.action.", "editor.fold", "editor.unfold", "editor.toggleFold", "cursor",
                   "actions.find", "editor.debug.action.")
MONACO_COMMANDS = {"undo", "redo", "deleteLeft", "deleteRight", "deleteWordLeft", "deleteWordRight", "tab", "outdent",
                   "editor.action.selectAll", "scrollLineUp", "scrollLineDown", "scrollPageUp", "scrollPageDown",
                   "expandLineSelection", "removeSecondaryCursors", "editor.action.insertLineAfter",
                   "editor.action.insertLineBefore", "lineBreakInsert", "type", "editor.action.triggerSuggest",
                   "acceptSelectedSuggestion", "hideSuggestWidget", "closeFindWidget", "editor.foldAll",
                   "editor.unfoldAll", "editor.foldRecursively", "editor.unfoldRecursively"}

# VS Code workbench commands -> the IDE: a Command Palette id, or a menu path / item text
VSCODE_TO_IDE = {
    "workbench.action.showCommands": "palette:>",
    "workbench.action.quickOpen": "palette:",
    "workbench.action.gotoLine": "palette::",
    "workbench.action.gotoSymbol": "palette:@",
    "workbench.action.files.save": "menu:File/Save",
    "workbench.action.files.saveAll": "menu:File/Save All",
    "workbench.action.files.newUntitledFile": "menu:File/New File",
    "workbench.action.files.openFile": "menu:File/Open File...",
    "workbench.action.closeActiveEditor": "menu:File/Close",
    "workbench.action.debug.start": "menu:Debug/Start Debugging",
    "workbench.action.debug.run": "menu:Debug/Start Without Debugging",
    "workbench.action.debug.stop": "menu:Debug/Stop Debugging",
    "workbench.action.tasks.build": "menu:Build/Build Solution",
    "workbench.action.openSettings": "menu:Tools/Options...",
    "workbench.action.terminal.toggleTerminal": "menu:View/Terminal",
    "workbench.action.findInFiles": "menu:Edit/Find in Files...",
    "editor.debug.action.toggleBreakpoint": "monaco",
}

# handlers fn(command: str, args) -> bool (True = handled); the extension host appends one
COMMAND_HANDLERS: list = []


def is_monaco_command(cmd: str) -> bool:
    if VSCODE_TO_IDE.get(cmd) == "monaco":
        return True
    return cmd in MONACO_COMMANDS or cmd.startswith(MONACO_PREFIXES)


def platform_key(kb: dict) -> str:
    v = kb.get("win") or kb.get("key")
    return str(v or "").strip().lower()


def collect(extensions=None) -> list[dict]:
    """[{key, command, when, args, target: 'monaco'|'ide', ext, title}] of every enabled extension.
    A "-command" entry (VS Code: remove a binding) removes earlier bindings of that command."""
    out: list[dict] = []
    for ext in (enabled_extensions() if extensions is None else extensions):
        titles = {}
        for c in ext.contributes_list("commands"):
            if isinstance(c, dict) and isinstance(c.get("command"), str):
                t = c.get("title")
                titles[c["command"]] = f"{c.get('category')}: {t}" if c.get("category") and t else str(t or "")
        for kb in ext.contributes_list("keybindings"):
            if not isinstance(kb, dict) or not isinstance(kb.get("command"), str):
                continue
            key = platform_key(kb)
            cmd = kb["command"]
            if cmd.startswith("-"):
                out = [b for b in out if not (b["command"] == cmd[1:] and (not key or b["key"] == key))]
                continue
            if not key:
                continue
            item = {"key": key, "command": cmd, "when": str(kb.get("when") or ""), "ext": ext.id,
                    "target": "monaco" if is_monaco_command(cmd) else "ide", "title": titles.get(cmd, cmd)}
            if "args" in kb:
                item["args"] = kb["args"]
            out.append(item)
    return out


_EDITOR_WHEN = re.compile(r"\b(editor\w*|textInputFocus|inSnippetMode|suggestWidget\w*|findWidget\w*|"
                          r"resource\w*|inlineSuggestion\w*)\b")


def needs_editor(when: str) -> bool:
    """A when clause that only makes sense inside an editor (handled by the Monaco binding)."""
    return bool(when) and bool(_EDITOR_WHEN.search(when))


def qt_sequence(key: str) -> str:
    """"ctrl+shift+k ctrl+c" -> "Ctrl+Shift+K, Ctrl+C" (QKeySequence portable text)."""
    names = {"ctrl": "Ctrl", "shift": "Shift", "alt": "Alt", "meta": "Meta", "win": "Meta", "cmd": "Ctrl",
             "enter": "Return", "escape": "Esc", "esc": "Esc", "pageup": "PgUp", "pagedown": "PgDown",
             "delete": "Del", "insert": "Ins", "backspace": "Backspace", "space": "Space", "tab": "Tab",
             "up": "Up", "down": "Down", "left": "Left", "right": "Right", "home": "Home", "end": "End"}
    chords = []
    for chord in key.split():
        parts = [p for p in chord.split("+") if p]
        chords.append("+".join(names.get(p, p.upper() if len(p) == 1 else p.capitalize()) for p in parts))
    return ", ".join(chords)


# ============================================================================ running commands
def run_command(win, command: str, args=None) -> bool:
    """Run a VS Code command id in the IDE. Returns False (and says so in the status bar) when unknown."""
    try:
        from ..features import command_palette as cp
        c = next((x for x in cp.commands() if x.id == command), None)
        if c is not None:
            c.callback()
            return True
    except Exception:  # noqa: BLE001
        pass
    target = VSCODE_TO_IDE.get(command, "")
    if target.startswith("palette:"):
        try:
            from ..features import command_palette as cp
            cp.show_palette(win, target[len("palette:"):])
            return True
        except Exception:  # noqa: BLE001
            pass
    if target.startswith("menu:") and win is not None:
        if _trigger_menu(win, target[len("menu:"):]):
            return True
    for h in list(COMMAND_HANDLERS):
        try:
            if h(command, args):
                return True
        except Exception:  # noqa: BLE001 - a handler must not break the others
            continue
    try:
        win.statusBar().showMessage(f"The command '{command}' is not available in RAD IDE", 5000)
    except Exception:  # noqa: BLE001
        pass
    return False


def _trigger_menu(win, path: str) -> bool:
    try:
        from ..features import command_palette as cp
        want = [cp.clean_text(p).lower() for p in path.split("/")]
        for text, act in cp.menu_actions(win):          # labels "File: Save" (clean_text already applied)
            parts = [p.strip().lower() for p in str(text).split(": ")]
            if parts[-1] == want[-1] and parts[0] == want[0] and act.isEnabled():
                act.trigger()
                return True
    except Exception:  # noqa: BLE001
        return False
    return False


# ============================================================================ window shortcuts
_shortcuts: list = []


def install_shortcuts(win, bindings: list[dict]) -> int:
    """Window-level shortcuts for IDE commands whose when clause is not editor-only."""
    from PyQt6.QtGui import QAction, QKeySequence, QShortcut
    for s in _shortcuts:
        try:
            s.setEnabled(False)
            s.deleteLater()
        except RuntimeError:
            pass
    _shortcuts.clear()
    used = set()
    for a in win.findChildren(QAction):
        for seq in a.shortcuts():
            used.add(seq.toString())
    n = 0
    for kb in bindings:
        if kb["target"] != "ide" or needs_editor(kb["when"]):
            continue
        seq = QKeySequence(qt_sequence(kb["key"]))
        if seq.isEmpty() or seq.toString() in used:
            continue
        sc = QShortcut(seq, win)
        sc.activated.connect(lambda c=kb["command"], a=kb.get("args"): run_command(win, c, a))
        _shortcuts.append(sc)
        used.add(seq.toString())
        n += 1
    return n


__all__ = ["collect", "run_command", "install_shortcuts", "is_monaco_command", "qt_sequence", "needs_editor",
           "COMMAND_HANDLERS", "VSCODE_TO_IDE"]
