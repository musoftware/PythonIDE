"""Wires the declarative VS Code contributions into the IDE (called by radide/features/__init__.py before the
features are installed, so Options applies a VS Code colour theme at start-up).

    themes        contrib_themes.register_all()   -> radide.theme (Options > Color theme, whole IDE chrome)
                  + every Monaco page gets the Monaco theme (vsxSetTheme) when the IDE theme changes
    languages     contrib_languages.refresh()     -> MONACO_LANG / MONACO_FILENAMES + Monaco languages
    grammars      vscode-textmate in the page (radide/web/vsx/vsx-contrib.js), grammar files served by the
                  "vsxc" channel object
    snippets      Monaco completion items (served by "vsxc")
    icon themes   solution_ui.FILE_ICON_PROVIDER
    keybindings   Monaco actions per page + window shortcuts (contrib_keybindings)
    configuration a "VS Code Extensions" page in Tools > Options (contrib_configuration)

``refresh(win)`` re-reads everything (radide.vsx.on_changed: install / uninstall / enable / disable)."""
from __future__ import annotations

import json
import weakref

from PyQt6.QtCore import QObject, pyqtSlot

from . import contrib_icons, contrib_keybindings, contrib_languages, contrib_themes

_editors: "weakref.WeakSet" = weakref.WeakSet()
_wins: list = []
_shared = {"spec": None, "keys": []}


# ============================================================================ the channel object
class _VsxBridge(QObject):
    """Published to the editor page as window.radChannel.objects.vsxc."""

    def __init__(self, editor):
        super().__init__()
        self._ed = weakref.ref(editor)

    @pyqtSlot(str, result=str)
    def grammar(self, scope):
        try:
            return contrib_languages.grammar_json(scope)
        except Exception as e:  # noqa: BLE001
            print(f"[vsx] grammar {scope}: {e}")
            return ""

    @pyqtSlot(str, result=str)
    def snippets(self, lang):
        try:
            return contrib_languages.snippets_json(lang)
        except Exception as e:  # noqa: BLE001
            print(f"[vsx] snippets {lang}: {e}")
            return "[]"

    @pyqtSlot(str, str)
    def runCommand(self, command, args_json):
        try:
            args = json.loads(args_json) if args_json else None
        except ValueError:
            args = None
        contrib_keybindings.run_command(_win_of(self._ed()), command, args)


def _win_of(editor):
    try:
        w = editor.window() if editor is not None else None
    except RuntimeError:
        w = None
    if w is not None and hasattr(w, "statusBar"):
        return w
    for ref in list(_wins):
        win = ref()
        if win is not None:
            return win
    return None


# ============================================================================ page spec
def _builtin_raw() -> dict:
    return {b: contrib_themes.builtin_raw_theme(b) for b in contrib_themes.BUILTIN_RAW}


def _rebuild_shared() -> None:
    reg = contrib_languages.registry()
    spec = reg.js_spec()
    spec["builtinRaw"] = _builtin_raw()
    keys = contrib_keybindings.collect()
    spec["keybindings"] = keys
    _shared["spec"] = spec
    _shared["keys"] = keys


def theme_js() -> dict | None:
    s = contrib_themes.current_spec()
    return s.js_spec() if s is not None else None


def context_keys(editor) -> dict:
    """Values for VS Code when-clause keys that Monaco does not know."""
    p = getattr(editor, "path", None)
    name = p.name if p is not None else ""
    ctx = {"resourceFilename": name, "resourceExtname": p.suffix.lower() if p is not None else "",
           "resourceLangId": editor.language_id() if hasattr(editor, "language_id") else "",
           "resourcePath": str(p) if p is not None else "", "isWindows": True, "isMac": False, "isLinux": False,
           "isWeb": False, "terminalFocus": False, "resourceScheme": "file", "isWorkspaceTrusted": True,
           "resource": p.as_uri() if p is not None and p.is_absolute() else ""}
    ctx.update(_config_keys())
    return ctx


def _config_keys() -> dict:
    """config.<setting> values the keybinding when clauses of extensions mention (Monaco context keys)."""
    import re
    out = {}
    try:
        from . import contrib_configuration as CC
        from . import contrib_keybindings as KB
        keys = set()
        for b in KB.collect():
            keys.update(re.findall(r"config\.([\w.\-]+)", str(b.get("when") or "")))
        vals = CC.values() if keys else {}
        for k in keys:
            v = vals.get(k)
            if isinstance(v, (bool, int, float, str)) or v is None:
                out["config." + k] = v
    except Exception:  # noqa: BLE001
        pass
    return out


def page_spec(editor) -> dict:
    if _shared["spec"] is None:
        _rebuild_shared()
    spec = dict(_shared["spec"])
    spec["theme"] = theme_js()
    try:
        from .. import theme as T
        spec["requested"] = T.monaco_theme()
    except Exception:  # noqa: BLE001
        pass
    spec["context"] = context_keys(editor)
    return spec


def _init_js(editor) -> str:
    spec = page_spec(editor)
    lang = editor.language_id() if hasattr(editor, "language_id") else ""
    ctx = json.dumps(spec["context"])
    return (f"(function(){{ if (!window.vsxInit) return;"
            f" const ctx = {ctx}; const ed = window.radEditor;"
            f" window.vsxContextKeys = window.vsxContextKeys || {{}};"
            f" Object.keys(ctx).forEach(k => {{ if (window.vsxContextKeys[k]) window.vsxContextKeys[k].set(ctx[k]);"
            f"  else window.vsxContextKeys[k] = ed.createContextKey(k, ctx[k]); }});"
            f" vsxInit({json.dumps(spec)});"
            f" if ({json.dumps(lang)}) radSetLanguage({json.dumps(lang)}); }})();")


def _on_editor_ready(editor) -> None:
    _editors.add(editor)
    editor._js(_init_js(editor))
    try:
        editor.languageChanged.connect(lambda _l, e=weakref.ref(editor): _ctx_update(e()))
    except Exception:  # noqa: BLE001
        pass


def _ctx_update(editor) -> None:
    if editor is None:
        return
    ctx = json.dumps(context_keys(editor))
    editor._js(f"(function(){{ const c = {ctx}; Object.keys(c).forEach(k => window.vsxContextKeys && "
               f"window.vsxContextKeys[k] && window.vsxContextKeys[k].set(c[k])); }})();")


def live_editors() -> list:
    out = []
    for ed in list(_editors):
        try:
            ed.isVisible()
            out.append(ed)
        except RuntimeError:
            continue
    return out


def _on_theme_changed(_name=None) -> None:
    contrib_icons.clear_cache()
    t = json.dumps(theme_js())
    for ed in live_editors():
        ed._js(f"if (window.vsxSetTheme) vsxSetTheme({t});")


# ============================================================================ Solution Explorer
def _tree_hook(win, root) -> None:
    """Icons for items of foreign project trees (kinds '*file' / '*folder' with a path)."""
    if contrib_icons.active() is None or root is None:
        return
    from pathlib import Path

    from ..features.solution_ui import ROLE
    stack = [root]
    while stack:
        it = stack.pop()
        data = it.data(0, ROLE)
        if data and len(data) > 1 and isinstance(data[1], str):
            kind = str(data[0])
            if kind.endswith("file") and kind not in ("webfile",):
                ic = contrib_icons.provider(Path(data[1]).name)
                if ic is not None:
                    it.setIcon(0, ic)
            elif kind.endswith(("folder", "dir")) and kind not in ("webfolder",):
                ic = contrib_icons.provider(Path(data[1]).name, True, it.isExpanded())
                if ic is not None:
                    it.setIcon(0, ic)
        stack.extend(it.child(i) for i in range(it.childCount()))


def _on_expand(win, item, expanded: bool) -> None:
    if contrib_icons.active() is None:
        return
    try:
        from pathlib import Path

        from ..features.solution_ui import ROLE
        data = item.data(0, ROLE)
        if data and str(data[0]).endswith(("folder", "dir")) and len(data) > 1 and isinstance(data[1], str):
            ic = contrib_icons.provider(Path(data[1]).name, True, expanded)
            if ic is not None:
                item.setIcon(0, ic)
    except Exception:  # noqa: BLE001
        pass


def refresh_icons(win=None) -> None:
    contrib_icons.refresh()
    for w in ([win] if win is not None else [r() for r in _wins]):
        if w is None:
            continue
        fill = getattr(w, "_fill_solution", None)
        if callable(fill) and getattr(w, "project", None) is not None:
            try:
                fill()
            except Exception as e:  # noqa: BLE001
                _log(w, f"[vsx] icons: {e}")


def _log(win, text: str) -> None:
    try:
        win.log(text)
    except Exception:  # noqa: BLE001
        print(text)


# ============================================================================ install / refresh
def preload() -> None:
    """Themes, languages and icon themes (no window needed)."""
    contrib_themes.register_all()
    contrib_languages.refresh()
    contrib_icons.refresh()
    _rebuild_shared()


def install(win) -> None:
    preload()
    _wins.append(weakref.ref(win))
    try:
        from ..monaco_editor import MonacoEditor
        MonacoEditor.channel_objects["vsxc"] = lambda ed: _VsxBridge(ed)
        if _on_editor_ready not in MonacoEditor.ready_hooks:
            MonacoEditor.ready_hooks.append(_on_editor_ready)
    except Exception as e:  # noqa: BLE001 - no QtWebEngine: themes and icons still work
        _log(win, f"[vsx] Monaco: {e}")
    from .. import theme as T
    if not getattr(install, "_theme_hooked", False):
        T.changed.connect(_on_theme_changed)
        install._theme_hooked = True
    from ..features import solution_ui
    solution_ui.FILE_ICON_PROVIDER = contrib_icons.provider
    if _tree_hook not in solution_ui.TREE_HOOKS:
        solution_ui.TREE_HOOKS.append(_tree_hook)
    tree = getattr(win, "solution", None)
    if tree is not None and hasattr(tree, "itemExpanded"):
        tree.itemExpanded.connect(lambda it: _on_expand(win, it, True))
        tree.itemCollapsed.connect(lambda it: _on_expand(win, it, False))
    from ..features import settings as S
    from . import contrib_configuration
    if contrib_configuration.options_page not in S.PAGE_HOOKS:
        S.PAGE_HOOKS.append(contrib_configuration.options_page)
    try:
        contrib_keybindings.install_shortcuts(win, _shared["keys"])
    except Exception as e:  # noqa: BLE001
        _log(win, f"[vsx] keybindings: {e}")
    _register_commands(win)
    try:
        from . import on_changed
        on_changed.connect(lambda w=weakref.ref(win): refresh(w()))
    except Exception:  # noqa: BLE001
        pass
    names = list(contrib_themes.registered())
    if names:
        _log(win, f"[vsx] colour themes: {', '.join(names)}")


def _register_commands(win) -> None:
    try:
        from ..features import command_palette as cp
    except Exception:  # noqa: BLE001
        return

    def pick_icons():
        from PyQt6.QtWidgets import QInputDialog
        try:
            from ..i18n import tr
        except Exception:  # noqa: BLE001
            def tr(s):
                return s
        items = [tr("None (RAD IDE icons)")] + [t.label for t in contrib_icons.available()]
        ids = ["none"] + [t.theme_id for t in contrib_icons.available()]
        act = contrib_icons.active()
        cur = ids.index(act.info.theme_id) if act and act.info.theme_id in ids else 0
        text, ok = QInputDialog.getItem(win, "File Icon Theme", "File icon theme:", items, cur, False)
        if ok:
            contrib_icons.choose(ids[items.index(text)])
            refresh_icons(win)
    cp.register_command("workbench.action.selectIconTheme", "File Icon Theme...", pick_icons, "Preferences")
    _register_theme_commands(win)


def _register_theme_commands(win) -> None:
    """"Preferences: Color Theme: Dracula" like the workbench's commands for the built-in themes."""
    try:
        from ..features import command_palette as cp
        from ..features.workbench import set_theme
    except Exception:  # noqa: BLE001
        return
    for name in contrib_themes.registered():
        cp.register_command(f"workbench.theme.{name}", f"Color Theme: {name}",
                            lambda n=name: set_theme(win, n), "Preferences")


def refresh(win=None) -> None:
    """Re-read every contribution (an extension was installed / removed / enabled / disabled)."""
    from .. import theme as T
    before = T.current_name()
    preload()
    wins = [win] if win is not None else [r() for r in _wins]
    for w in wins:
        if w is None:
            continue
        try:
            contrib_keybindings.install_shortcuts(w, _shared["keys"])
        except Exception as e:  # noqa: BLE001
            _log(w, f"[vsx] keybindings: {e}")
        _register_theme_commands(w)
        # the chosen theme came (back): apply it; a removed one falls back to Light inside remove_theme
        try:
            from ..features import settings as S
            want = S.get(w, "theme")
            if want != before and want in T.THEMES:
                S.apply_all(w)
        except Exception:  # noqa: BLE001
            pass
    for ed in live_editors():
        ed._js(_init_js(ed))
    _on_theme_changed()
    for w in wins:
        if w is not None:
            refresh_icons(w)


__all__ = ["install", "refresh", "preload", "page_spec", "theme_js", "live_editors", "refresh_icons",
           "context_keys"]
