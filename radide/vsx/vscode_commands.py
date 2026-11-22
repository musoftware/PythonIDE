"""VS Code's built-in commands in RAD IDE's window: Command Palette entries, keybindings, execution.

``execute(win, id, args)`` runs a VS Code command id from the IDE side (Command Palette, keybindings.json,
contributes.keybindings, menus) - the same routing an extension's ``vscode.commands.executeCommand`` gets:
  1. a command registered in the Command Palette (extension commands, IDE features: ``command_palette``),
  2. an editor command on the active Monaco editor (Monaco's own ids + radide/vsx/editor_commands.py),
  3. a workbench command with a RAD IDE implementation (radide/vsx/ide_commands.py, workbench_ui),
  4. VSCODE_TO_IDE menu equivalents (contrib_keybindings),
  5. the extension host's own built-ins (host/main.js, host/commands.js) when it runs.

``palette_entries(win)`` lists the built-in commands VS Code shows in its Command Palette (``f1`` actions and
editor actions with a title, radide/vsx/reference/commands.json) that RAD IDE can run, with VS Code's title,
category and default keybinding, so the palette offers "View: Toggle Primary Side Bar Visibility  Ctrl+B",
"Format Document  Shift+Alt+F" ... No Qt import at module level."""
from __future__ import annotations

import json
import re
from pathlib import Path

REF = Path(__file__).resolve().parent / "reference"

CATEGORIES = {"Categories.View": "View", "Categories.Developer": "Developer", "Categories.Help": "Help",
              "Categories.File": "File", "Categories.Test": "Test", "Categories.Preferences": "Preferences",
              "TASKS_CATEGORY": "Tasks", "DEBUG_COMMAND_CATEGORY": "Debug", "EXTENSIONS_CATEGORY": "Extensions",
              "ExtensionsLocalizedLabel": "Extensions", "Problems": "Problems", "Output": "Output", "REPL": "Debug",
              "Comments": "Comments", "Developer": "Developer", "LOCAL_HISTORY_CATEGORY": "Local History",
              "diffEditorCategory": "Diff Editor", "workspacesCategory": "Workspaces", "Accounts": "Accounts",
              "PROFILES_CATEGORY": "Profiles", "imagePreviewCategory": "Image Preview", "TERMINAL_CATEGORY": "Terminal",
              "terminalStrings.actionCategory": "Terminal", "SCM_CATEGORY": "Source Control",
              "category": ""}
# commands the host implements itself (main.js / commands.js) and that make sense from the palette
HOST_PALETTE = {"workbench.action.files.newUntitledFile", "workbench.action.closeAllEditors",
                "workbench.action.closeOtherEditors", "workbench.action.nextEditor", "workbench.action.previousEditor",
                "workbench.action.terminal.new", "workbench.action.terminal.kill", "workbench.action.tasks.runTask",
                "workbench.action.tasks.reRunTask", "workbench.action.pinEditor", "workbench.action.unpinEditor",
                "copyFilePath", "copyRelativeFilePath"}

# VS Code's Command Palette labels of commands whose title / category the source inventory cannot resolve
# (a variable, a localize() key, a title on another menu) - as VS Code 1.10x shows them
LABELS = {
    "editor.action.commentLine": ("", "Toggle Line Comment"), "editor.action.blockComment": ("", "Toggle Block Comment"),
    "workbench.action.openGlobalKeybindingsFile": ("Preferences", "Open Keyboard Shortcuts (JSON)"),
    "workbench.action.openGlobalKeybindings": ("Preferences", "Open Keyboard Shortcuts"),
    "workbench.action.openSettings2": ("Preferences", "Open Settings (UI)"),
    "workbench.action.openSettingsJson": ("Preferences", "Open User Settings (JSON)"),
    "workbench.action.openApplicationSettingsJson": ("Preferences", "Open Application Settings (JSON)"),
    "workbench.action.openWorkspaceSettingsFile": ("Preferences", "Open Workspace Settings (JSON)"),
    "workbench.action.openSettings": ("Preferences", "Open Settings"),
    "workbench.action.selectTheme": ("Preferences", "Color Theme"),
    "workbench.action.navigateBack": ("", "Go Back"), "workbench.action.navigateForward": ("", "Go Forward"),
    "workbench.action.navigateLast": ("", "Go Previous"),
    "workbench.action.navigateToLastEditLocation": ("", "Go to Last Edit Location"),
    "workbench.action.showCommands": ("", "Show All Commands"), "workbench.action.quickOpen": ("", "Go to File..."),
    "workbench.action.gotoLine": ("", "Go to Line/Column..."), "workbench.action.gotoSymbol": ("", "Go to Symbol in Editor..."),
    "workbench.action.showAllSymbols": ("", "Go to Symbol in Workspace..."),
    "workbench.action.files.save": ("File", "Save"), "workbench.action.files.saveAll": ("File", "Save All"),
    "workbench.action.files.saveAs": ("File", "Save As..."), "workbench.action.files.revert": ("File", "Revert File"),
    "workbench.action.files.newUntitledFile": ("File", "New Untitled Text File"),
    "workbench.action.files.openFile": ("File", "Open File..."), "workbench.action.files.openFolder": ("File", "Open Folder..."),
    "workbench.action.openRecent": ("File", "Open Recent..."),
    "workbench.action.closeActiveEditor": ("View", "Close Editor"),
    "workbench.action.reopenClosedEditor": ("View", "Reopen Closed Editor"),
    "workbench.action.togglePanel": ("View", "Toggle Panel Visibility"),
    "workbench.action.toggleSidebarVisibility": ("View", "Toggle Primary Side Bar Visibility"),
    "workbench.action.toggleAuxiliaryBar": ("View", "Toggle Secondary Side Bar Visibility"),
    "workbench.action.toggleZenMode": ("View", "Toggle Zen Mode"), "workbench.action.toggleFullScreen": ("View", "Toggle Full Screen"),
    "workbench.action.zoomIn": ("View", "Zoom In"), "workbench.action.zoomOut": ("View", "Zoom Out"),
    "workbench.action.zoomReset": ("View", "Reset Zoom"),
    "editor.action.toggleWordWrap": ("View", "Toggle Word Wrap"), "editor.action.toggleMinimap": ("View", "Toggle Minimap"),
    "editor.action.toggleRenderWhitespace": ("View", "Toggle Render Whitespace"),
    "editor.action.toggleRenderControlCharacter": ("View", "Toggle Control Characters"),
    "editor.action.toggleStickyScroll": ("View", "Toggle Editor Sticky Scroll"),
    "workbench.action.findInFiles": ("Search", "Find in Files"), "workbench.action.replaceInFiles": ("Search", "Replace in Files"),
    "workbench.view.search": ("View", "Show Search"), "workbench.view.explorer": ("View", "Show Explorer"),
    "workbench.view.scm": ("View", "Show Source Control"), "workbench.view.debug": ("View", "Show Run and Debug"),
    "workbench.view.extensions": ("View", "Show Extensions"),
    "workbench.actions.view.problems": ("View", "Focus Problems (Errors, Warnings, Infos)"),
    "workbench.action.terminal.new": ("Terminal", "Create New Terminal"),
    "workbench.action.terminal.toggleTerminal": ("View", "Toggle Terminal"),
    "workbench.action.terminal.kill": ("Terminal", "Kill the Active Terminal Instance"),
    "workbench.action.debug.start": ("Debug", "Start Debugging"), "workbench.action.debug.run": ("Debug", "Run Without Debugging"),
    "workbench.action.debug.stop": ("Debug", "Stop"), "workbench.action.debug.restart": ("Debug", "Restart"),
    "workbench.action.debug.selectandstart": ("Debug", "Select and Start Debugging"),
    "workbench.action.debug.configure": ("Debug", "Open 'launch.json'"),
    "workbench.action.tasks.runTask": ("Tasks", "Run Task"), "workbench.action.tasks.build": ("Tasks", "Run Build Task"),
    "workbench.action.tasks.reRunTask": ("Tasks", "Rerun Last Task"),
    "workbench.action.restartExtensionHost": ("Developer", "Restart Extension Host"),
    "workbench.action.reloadWindow": ("Developer", "Reload Window"),
    "workbench.extensions.action.installExtensions": ("Extensions", "Install Extensions"),
    "workbench.extensions.action.showInstalledExtensions": ("Extensions", "Show Installed Extensions"),
    "workbench.extensions.action.checkForUpdates": ("Extensions", "Check for Extension Updates"),
    "editor.action.marker.nextInFiles": ("", "Go to Next Problem in Files (Error, Warning, Info)"),
    "editor.action.marker.prevInFiles": ("", "Go to Previous Problem in Files (Error, Warning, Info)"),
    "workbench.action.quickOpenView": ("View", "Open View"),
    "workbench.action.showAllEditors": ("View", "Show All Editors By Appearance"),
    "workbench.action.nextEditor": ("View", "Open Next Editor"), "workbench.action.previousEditor": ("View", "Open Previous Editor"),
    "workbench.action.closeAllEditors": ("View", "Close All Editors"),
    "workbench.action.closeOtherEditors": ("View", "Close Other Editors in Group"),
    "editor.action.insertFinalNewLine": ("", "Insert Final New Line"), "editor.action.reverseLines": ("", "Reverse Lines"),
    "copyFilePath": ("File", "Copy Path of Active File"), "copyRelativeFilePath": ("File", "Copy Relative Path of Active File"),
    "revealFileInOS": ("File", "Reveal in File Explorer"),
}

_REF: dict | None = None


def reference() -> dict:
    """id -> commands.json entry (cached)."""
    global _REF
    if _REF is None:
        try:
            _REF = {c["id"]: c for c in json.loads((REF / "commands.json").read_text("utf-8"))["commands"]}
        except (OSError, ValueError, KeyError):
            _REF = {}
    return _REF


def clean_title(t: str) -> str:
    t = re.sub(r"&&(\w)", r"\1", str(t or "")).replace("&&", "&")
    return t.replace("...", "…").strip()


def category(entry: dict) -> str:
    c = entry.get("category") or ""
    if c in CATEGORIES:
        return CATEGORIES[c]
    if re.fullmatch(r"[A-Z][a-z]+( [A-Z][a-z]+)*", c):          # a plain word ("Problems", "Refactor Preview")
        return c
    return ""


def default_key(entry: dict) -> str:
    """VS Code's default Windows keybinding ("ctrl+shift+p"), "" when none."""
    for kb in entry.get("keybinding") or []:
        k = kb.get("win") or kb.get("key") or kb.get("primary")
        if isinstance(k, str) and k and not k.startswith(("KeyMod", "KeyCode")):
            return k.lower()
    return ""


def display_key(key: str) -> str:
    from .contrib_keybindings import qt_sequence
    return qt_sequence(key) if key else ""


# ============================================================================ who runs what
def _svc(win):
    return getattr(win, "vsx_host", None)


def is_editor_command(cid: str) -> bool:
    from .contrib_keybindings import is_monaco_command
    return is_monaco_command(cid)


def ide_handles(cid: str) -> bool:
    from . import ide_commands as IC
    from .contrib_keybindings import VSCODE_TO_IDE
    if IC.handles(cid):
        return True
    t = VSCODE_TO_IDE.get(cid, "")
    return bool(t) and t != "monaco"


def can_run(win, cid: str) -> bool:
    if is_editor_command(cid) or ide_handles(cid):
        return True
    svc = _svc(win)
    return cid in HOST_PALETTE and svc is not None


def active_editor(win):
    svc = _svc(win)
    ed = svc.active_editor() if svc is not None else None
    if ed is None:
        tabs = getattr(win, "tabs", None)
        cur = tabs.currentWidget() if tabs is not None else None
        ed = getattr(cur, "editor", None)
        if ed is not None and not hasattr(ed, "_js"):
            ed = None
    return ed


def execute(win, cid: str, args=None) -> bool:
    """Run VS Code command *cid* in the IDE. True when something ran it."""
    args = args if isinstance(args, list) else ([] if args is None else [args])
    try:
        from ..features import command_palette as cp
        c = next((x for x in cp.commands() if x.id == cid), None)
        if c is not None:
            c.callback()
            return True
    except Exception:  # noqa: BLE001
        pass
    if execute_core(win, cid, args, host=False):
        return True
    from . import contrib_keybindings as KB
    t = KB.VSCODE_TO_IDE.get(cid, "")
    if t and t != "monaco" and KB.run_command(win, cid, args, fallback=False):
        return True
    for h in list(KB.COMMAND_HANDLERS):
        try:
            if h(cid, args):
                return True
        except Exception:  # noqa: BLE001
            continue
    return execute_core(win, cid, args, editor=False, ide=False)


def execute_core(win, cid: str, args=None, editor: bool = True, ide: bool = True, host: bool = True) -> bool:
    """Steps 2, 3 and 5 of execute (no Command Palette / menu lookup)."""
    args = args if isinstance(args, list) else ([] if args is None else [args])
    from . import ide_commands as IC
    if editor and is_editor_command(cid) and not IC.handles(cid):
        from . import editor_commands as EC
        ed = active_editor(win)
        if ed is not None and EC.run(ed, cid, args, win=win):
            return True
    svc = _svc(win)
    wb = getattr(svc, "workbench", None) if svc is not None else None
    if ide and wb is not None:
        try:
            r = wb.exec_command(cid, args)
        except Exception as e:  # noqa: BLE001
            r = None
            try:
                svc.log(f"command {cid}: {e}")
            except Exception:  # noqa: BLE001
                pass
        if r is not None:
            from .ide_commands import Deferred
            if isinstance(r, Deferred):
                r.fn(lambda _res: None)
            return True
    if host and svc is not None and (cid in HOST_PALETTE or svc.host.running()):
        svc.execute(cid, args)
        return True
    return False


# ============================================================================ Command Palette entries
def palette_entries(win) -> list[dict]:
    """[{id, title, category, key, editor}] - VS Code's palette commands RAD IDE runs."""
    out = []
    ref = reference()
    for cid in list(ref) + [c for c in LABELS if c not in ref]:
        e = ref.get(cid, {})
        title = e.get("title")
        if cid in LABELS:
            cat, title = LABELS[cid]
        elif not title or cid.startswith("_"):
            continue
        else:
            cat = category(e)
            if not (bool(e.get("f1")) or "EditorAction" in (e.get("sources") or [])):
                continue
        if not can_run(win, cid):
            continue
        out.append({"id": cid, "title": clean_title(title), "category": cat, "key": default_key(e),
                    "editor": is_editor_command(cid)})
    return out


__all__ = ["execute", "palette_entries", "can_run", "reference", "default_key", "display_key", "clean_title"]
