"""Quick Actions UI: the menu (Ctrl+. / Alt+Enter / right-click / light bulb), the edit preview and the light bulb.

* ``show_menu(win, ed, line, col, actions)`` - a keyboard-navigable menu grouped like Visual Studio (Quick Fixes,
  Refactorings, Source Actions); the preferred fix is selected, Enter applies it, hovering (or arrowing to) an entry
  shows the lines it changes next to the menu (``preview_text``); install actions show their command line.
* ``apply_action(win, ed, action)`` - a built-in action's edits as one undo step (several files: the refactoring
  preview), the squiggles it fixes are removed at once, then its command (pip / npm / NuGet install with progress).
  A language server's action goes to refactor.run_code_action.
* the light bulb: after the caret rests ~350 ms the editor asks ``qfBulb`` (a cheap check: the built-in providers
  without network / project scans, or a diagnostic on the line) and shows a bulb in the glyph margin of the caret
  line; a click on it opens the same menu (the breakpoint click is not taken there). Setting "editor/lightBulb".
"""
from __future__ import annotations

import difflib
import html
import json
from pathlib import Path

from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtGui import QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import QApplication, QLabel, QMenu

from .. import editkit
from . import Action, collect, make_context, merge, norm_title

BULB_KEY = "editor/lightBulb"
BULB_SVG = ("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'>"
            "<path d='M8 1.5a4.5 4.5 0 0 0-2.6 8.2c.4.3.6.7.6 1.1V12h4v-1.2c0-.4.2-.8.6-1.1A4.5 4.5 0 0 0 8 1.5z' "
            "fill='%23FFCC00' stroke='%23A07800' stroke-width='.8'/><rect x='6' y='12.6' width='4' height='1.4' "
            "rx='.5' fill='%23777'/></svg>")
GROUPS = (("quickfix", "Quick Fixes"), ("refactor", "Refactorings"), ("source", "Source Actions"), ("", "Actions"))

JS = r"""
(function () {
  if (window.radQf || !window.radEditor || !window.radx) return;
  const ed = window.radEditor;
  const st = document.createElement('style');
  st.textContent = '.rad-bulb{background:url(' + JSON.stringify(__SVG__) + ') center center / 14px 14px no-repeat;' +
                   'cursor:pointer;}';
  document.head.appendChild(st);
  let decos = [], line = -1, timer = null, seq = 0;
  window.radQf = {
    enabled: true,
    line: () => line,
    show(l) {
      line = l;
      decos = ed.deltaDecorations(decos, l < 0 ? [] : [{ range: new monaco.Range(l + 1, 1, l + 1, 1),
        options: { glyphMarginClassName: 'rad-bulb', stickiness: 1,
                   glyphMarginHoverMessage: { value: 'Show potential fixes (Alt+Enter or Ctrl+.)' } } }]);
    },
    check() {
      const p = ed.getPosition(); const my = ++seq;
      if (!p || !this.enabled || ed.getOption(monaco.editor.EditorOption.readOnly)) { this.show(-1); return; }
      window.radx.ask('qfBulb', { line: p.lineNumber - 1, col: p.column - 1 }).then(v => {
        if (my === seq) this.show(v ? p.lineNumber - 1 : -1); });
    },
    schedule(ms) { clearTimeout(timer); timer = setTimeout(() => this.check(), ms === undefined ? 350 : ms); },
  };
  ed.onDidChangeCursorPosition(e => { if (e.position.lineNumber - 1 !== line) radQf.show(-1); radQf.schedule(); });
  ed.onDidChangeModelContent(() => radQf.schedule(600));
  ed.onMouseDown(e => {
    const el = e.target && e.target.element;
    if (e.target.type === monaco.editor.MouseTargetType.GUTTER_GLYPH_MARGIN && el && el.classList &&
        el.classList.contains('rad-bulb')) {
      if (e.target.position && e.target.position.lineNumber - 1 !== ed.getPosition().lineNumber - 1)
        ed.setPosition({ lineNumber: e.target.position.lineNumber, column: 1 });
      setTimeout(() => window.radx.cmd('codeActions'), 0);
    }
  });
  // Alt+Enter (ReSharper / Rider / VS "Show potential fixes"); Ctrl+. is the radx.quickActions action.
  // Not while the find widget is open: there Alt+Enter is Monaco's "Select All Occurrences of Find Match".
  ed.addCommand(monaco.KeyMod.Alt | monaco.KeyCode.Enter, () => window.radx.cmd('codeActions'), '!findWidgetVisible');
})();
"""


# ============================================================================ diagnostics
def editor_diagnostics(ed) -> list[dict]:
    """The squiggles the editor shows (MonacoEditor.set_diagnostics: language servers, linters, the build)."""
    return [d for d in (getattr(ed, "_diagnostics", None) or []) if isinstance(d, dict)]


def lsp_diagnostics(ed, line: int) -> list[dict]:
    from ..features import refactor
    out = []
    try:
        raw = refactor._diags_for(ed, line, line) if refactor._client(ed) is not None else []
    except Exception:  # noqa: BLE001
        raw = []
    for d in raw:
        r = d.get("range", {})
        s, e = r.get("start", {}), r.get("end", {})
        out.append({"line": s.get("line", 0), "col": s.get("character", 0), "endLine": e.get("line", 0),
                    "endCol": e.get("character", 0), "message": str(d.get("message", "")), "code": d.get("code")})
    return out


def context_for(win, ed, line: int, col: int, cheap: bool = False):
    diags = editor_diagnostics(ed)
    have = {(d.get("line"), d.get("message")) for d in diags}
    diags += [d for d in lsp_diagnostics(ed, line) if (d["line"], d["message"]) not in have]
    return make_context(ed.text(), getattr(ed, "path", "") or "untitled", line, col, diags, win=win, ed=ed,
                        cheap=cheap)


def builtin_actions(win, ed, line: int, col: int, cheap: bool = False) -> list[Action]:
    if getattr(ed, "path", None) is None:
        return []
    try:
        return collect(context_for(win, ed, line, col, cheap))
    except Exception as e:  # noqa: BLE001 - never break the menu
        print(f"[quickfix] {e}")
        return []


def clear_fixed(ed, fixes: list) -> None:
    """Remove the squiggles an applied fix resolved (the server re-checks later)."""
    if not fixes or not hasattr(ed, "set_diagnostics"):
        return
    gone = {(d.get("line"), d.get("message")) for d in fixes}
    cur = editor_diagnostics(ed)
    rest = [d for d in cur if (d.get("line"), d.get("message")) not in gone]
    if len(rest) != len(cur):
        ed.set_diagnostics(rest)


# ============================================================================ preview
def preview_text(win, ed, action: Action) -> str:
    """The changed lines of the action (- old / + new, like Visual Studio's preview), or its command."""
    if action.disabled:
        return action.disabled
    parts = []
    path = str(getattr(ed, "path", ""))
    for p, edits in (action.edits or {}).items():
        if not edits:
            continue
        old = ed.text() if editkit._key(p) == editkit._key(path) else editkit.file_text(win, p)
        new = editkit.apply_edits_to_text(old, edits)
        a, b = old.split("\n"), new.split("\n")
        lines = []
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
            if tag == "equal":
                continue
            if i1 > 0 and (not lines or not lines[-1].startswith("  ")):
                lines.append(f"  {i1:>4}  {a[i1 - 1]}")
            lines += [f"- {i + 1:>4}  {a[i]}" for i in range(i1, i2)]
            lines += [f"+ {j + 1:>4}  {b[j]}" for j in range(j1, j2)]
        if len(lines) > 16:
            lines = lines[:16] + [f"  ... {len(lines) - 16} more line(s)"]
        if editkit._key(p) != editkit._key(path):
            lines.insert(0, f"{Path(p).name}:")
        parts.append("\n".join(lines))
    if action.detail:
        parts.append(action.detail)
    if not parts and action.lsp is not None:
        cmd = action.lsp.get("command")
        parts.append(f"(language server) {cmd.get('title') or cmd.get('command') if isinstance(cmd, dict) else cmd or ''}")
    return "\n\n".join(x for x in parts if x).strip()


class Preview(QLabel):
    """The floating preview next to the menu (diff colours)."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip)
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setFont(QFont("Consolas", 9))
        self.setMargin(6)
        self.setProperty("i18n_skip", True)
        self.setStyleSheet("QLabel{background:#FFFFF0;color:#202020;border:1px solid #A0A0A0;}")
        self.plain = ""

    def set_preview(self, text: str) -> None:
        self.plain = text
        rows = []
        for ln in text.split("\n"):
            esc = html.escape(ln).replace(" ", "&nbsp;")
            if ln.startswith("- "):
                rows.append(f"<span style='background:#FFDCE0;color:#86181D'>{esc}</span>")
            elif ln.startswith("+ "):
                rows.append(f"<span style='background:#DCFFE4;color:#165C26'>{esc}</span>")
            else:
                rows.append(esc)
        self.setText("<br>".join(rows))
        self.adjustSize()


def _preview_widget(win) -> Preview:
    p = getattr(win, "_quick_preview", None)
    if p is None:
        p = Preview(None)
        win._quick_preview = p
    return p


# ============================================================================ menu
def apply_action(win, ed, action: Action) -> None:
    from ..features import refactor
    if action.disabled:
        return
    if action.lsp is not None:
        refactor.run_code_action(win, ed, action.lsp)
        return
    changes = {p: e for p, e in (action.edits or {}).items() if e}
    path = str(getattr(ed, "path", ""))
    if changes:
        if len(changes) == 1 and editkit._key(next(iter(changes))) == editkit._key(path):
            editkit.apply_edits(ed, next(iter(changes.values())))
        else:
            refactor.preview_and_apply(win, action.title, changes, force_preview=True)
        clear_fixed(ed, action.fixes)
    if action.run is not None:
        action.run(win, ed)
    try:
        win.statusBar().showMessage(action.title, 4000)
    except Exception:  # noqa: BLE001
        pass
    if hasattr(ed, "_js"):
        ed._js("window.radQf && radQf.schedule(300);")


def extra_as_actions(extras: list) -> list[Action]:
    return [Action(str(title), run=(lambda win, ed, cb=cb: cb()), provider="extra") for title, cb in extras or []]


def show_menu(win, ed, line: int, col: int, actions: list[Action], err: str = "") -> QMenu:
    from ..features import refactor
    menu = QMenu(win)
    menu.setToolTipsVisible(True)
    win._refactor_menu = menu
    win._quick_actions = list(actions)
    win._quick_menu_map = {}
    first = None
    any_ = False
    for key, title in GROUPS:
        group = [a for a in actions if (a.kind or "") == key or (key == "" and a.kind not in ("quickfix", "refactor",
                                                                                               "source"))]
        if not group:
            continue
        if any_:
            menu.addSeparator()
        head = menu.addAction(title)
        head.setEnabled(False)
        for a in group:
            act = menu.addAction("    " + a.title.replace("&", "&&"))
            if a.preferred:                   # the preferred fix in bold (the text stays translatable)
                f = act.font()
                f.setBold(True)
                act.setFont(f)
            if a.disabled:
                act.setEnabled(False)
                act.setToolTip(a.disabled)
            elif first is None:
                first = act
            act.triggered.connect(lambda _=False, a=a: apply_action(win, ed, a))
            win._quick_menu_map[id(act)] = a
        any_ = True
    if any_:
        menu.addSeparator()
    menu.addAction("Rename Symbol...\tF2", lambda: refactor.rename_symbol(win, ed, line, col))
    menu.addAction("Find All References\tShift+F12", lambda: refactor.find_references(win, ed, line, col))
    if not any(not a.disabled for a in actions):
        try:
            win.statusBar().showMessage(err or "No quick fixes or refactorings here (select code to extract it)", 6000)
        except Exception:  # noqa: BLE001
            pass
    preview = _preview_widget(win)

    def hovered(act):
        a = win._quick_menu_map.get(id(act))
        text = preview_text(win, ed, a) if a is not None else ""
        if not text:
            preview.hide()
            return
        preview.set_preview(text)
        if not menu.isVisible():
            return
        g = menu.geometry()
        scr = (menu.screen() or QApplication.primaryScreen()).availableGeometry()
        x = g.right() + 4
        if x + preview.width() > scr.right():
            x = max(scr.left(), g.left() - preview.width() - 4)
        y = min(max(scr.top(), g.top() + menu.actionGeometry(act).top()), scr.bottom() - preview.height())
        preview.move(QPoint(x, y))
        preview.show()
    menu.hovered.connect(hovered)
    menu.aboutToHide.connect(preview.hide)
    win._quick_first = first

    def pop(p):
        if getattr(win, "_refactor_no_exec", False):
            return
        if first is not None:
            QTimer.singleShot(0, lambda: (menu.setActiveAction(first), hovered(first)))
        menu.exec(p)
    refactor._caret_global(ed, pop)
    return menu


def quick_actions(win, ed, line=None, col=None) -> None:
    """Ctrl+. / Alt+Enter / the light bulb / "Quick Actions and Refactorings..." in the editor menu."""
    from ..features import refactor
    if ed is None:
        return
    if line is None:
        line, col = ed.getCursorPosition()
    builtin = builtin_actions(win, ed, line, col)
    extras = extra_as_actions(refactor._extra_actions(win, ed, line, col))

    def finish(server: list, err: str = "") -> None:
        text, path = ed.text(), getattr(ed, "path", "")
        acts = merge(builtin, server, text, path)
        titles = {norm_title(a.title) for a in acts}
        acts += [a for a in extras if norm_title(a.title) not in titles]
        show_menu(win, ed, line, col, acts, err)
    if refactor._client(ed) is None:
        finish([])
        return
    answered = []

    def got(actions, err):
        if answered:
            return
        answered.append(True)
        finish(actions or [], err)
    # a busy / indexing server must not keep the built-in fixes from showing
    QTimer.singleShot(4000, lambda: got([], "the language server did not answer"))
    refactor.request_code_actions(win, ed, line, col, got)


# ============================================================================ light bulb
def bulb_enabled() -> bool:
    try:
        from ..monaco_editor import _settings
        v = _settings().value(BULB_KEY, True)
        return v not in (False, "false", "0", 0)
    except Exception:  # noqa: BLE001
        return True


def has_actions(win, ed, line: int, col: int) -> bool:
    """Cheap: a built-in action (no network / project scan) or a diagnostic on the line."""
    if line in set(getattr(ed, "_breakpoints", ()) or ()) or getattr(ed, "_current", None) == line:
        return False                  # the glyph margin shows the breakpoint / current line there
    if any(d.get("line", -1) <= line <= d.get("endLine", d.get("line", -1)) and d.get("severity") != "info"
           for d in editor_diagnostics(ed)):
        return True
    return any(not a.disabled for a in builtin_actions(win, ed, line, col, cheap=True))


def _bulb_request(ed, req, payload) -> None:
    ok = False
    try:
        data = json.loads(payload or "{}")
        if bulb_enabled():
            ok = has_actions(ed.window(), ed, int(data.get("line", 0)), int(data.get("col", 0)))
    except Exception:  # noqa: BLE001 - the light bulb must never break the editor
        ok = False
    editkit.resolve(ed, req, bool(ok))


def _on_ready(ed) -> None:
    ed._js(JS.replace("__SVG__", json.dumps(BULB_SVG)))
    _warm(ed.window(), ed)


def _warm(win, ed) -> None:
    """Python: list the interpreter's modules in the background (the menu then needs no wait)."""
    try:
        from . import installers, language_of
        if language_of(ed.path, ed) == "python":
            from .lang_python import installed_modules
            installed_modules(installers.python_for(win, ed.path), wait=False)
    except Exception:  # noqa: BLE001
        pass


def _builtin_editor_hook(win):
    """The built-in editor (no Monaco): Ctrl+. / Alt+Enter shortcuts and the right-click entry."""
    def hook(ed):
        if editkit.is_monaco(ed) or getattr(ed, "_qf_hooked", False):
            return
        ed._qf_hooked = True
        for keys in ("Ctrl+.", "Alt+Return"):
            sc = QShortcut(QKeySequence(keys), ed)
            sc.setContext(Qt.ShortcutContext.WidgetShortcut)
            sc.activated.connect(lambda ed=ed: quick_actions(ed.window(), ed))
        sig = getattr(ed, "contextMenuAboutToShow", None)
        if sig is not None:
            sig.connect(lambda m, ed=ed: _context_entries(ed.window(), ed, m))
    return hook


def _context_entries(win, ed, menu) -> None:
    from PyQt6.QtGui import QAction
    from ..features import refactor
    first = menu.actions()[0] if menu.actions() else None
    acts = [QAction("Quick Actions and Refactorings...\tCtrl+.", menu), QAction("Rename...\tF2", menu)]
    acts[0].triggered.connect(lambda: quick_actions(win, ed))
    acts[1].triggered.connect(lambda: refactor.rename_symbol(win, ed))
    for a in acts:
        menu.insertAction(first, a)
    menu.insertSeparator(first)


_installed = False


def install(win) -> None:
    """Once per process (the handlers find the editor's own window)."""
    global _installed
    if _installed:
        return
    _installed = True
    editkit.REQUESTS["qfBulb"] = _bulb_request
    editkit.READY.append(_on_ready)
    try:
        from .. import editor as _editor
        _editor.EDITOR_HOOKS.append(_builtin_editor_hook(win))
    except Exception:  # noqa: BLE001
        pass


__all__ = ["quick_actions", "show_menu", "apply_action", "preview_text", "has_actions", "install",
           "builtin_actions", "context_for", "clear_fixed", "Preview"]
