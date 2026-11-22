"""Command Palette (Ctrl+Shift+P) and Quick Open (Ctrl+P) - CONTRACTS 9.2.

One VS Code style "quick input" box that works in every workbench layout:
  * ">"  commands: every QAction of the menu bar (and of the tool bars), the extra commands that features and
         VS Code extensions register with register_command() (hidden while their `visible` / when clause is
         false, keybindings shown) and VS Code's own palette commands RAD IDE runs (radide/vsx/vscode_commands:
         "Format Document", "View: Toggle Word Wrap", "Go Back" ...); recently used commands come first,
  * ""   Quick Open: fuzzy search over the files of every project of the solution ("name:12" opens at line 12),
  * ":"  go to line (":42" or ":42:7") in the current editor (Ctrl+G when the IDE does not use it),
  * "@"  go to symbol in editor (Ctrl+Shift+O; "@:" by kind) - language server / extension symbols, the plugin's
         outline or a declaration scan,  "#"  go to symbol in workspace (Ctrl+T),
  * "view " open view, "edt " open editors, "term " terminals, "task " run task (tasks.json + task providers),
    "debug " launch.json configurations, "ext " / "ext install " extensions, "recent " recent projects,
  * "?"  help.
install_vscode_keys() binds VS Code's default keys of those workbench commands where the IDE has no shortcut.

API for other features:
    from radide.features import command_palette as cp
    cp.register_command("ai.explain", "Explain Selection", callback, category="AI", shortcut="Ctrl+Alt+E")
    cp.show_palette(win)          # commands
    cp.quick_open(win)            # files
    cp.fuzzy_match(query, text) -> (score, [matched positions]) | None
"""
from __future__ import annotations

import html
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QEvent, QObject, QRectF, QSize, Qt, QTimer
from PyQt6.QtGui import QAction, QColor, QKeySequence, QPainter, QTextDocument
from PyQt6.QtWidgets import (QApplication, QFrame, QGraphicsDropShadowEffect, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QMenu, QStyle, QStyledItemDelegate, QToolBar, QVBoxLayout)

# ============================================================================ fuzzy matching
_SEP = set(" _-./\\:()[]>,+&@#")


def _word_start(t: str, i: int) -> bool:
    if i <= 0:
        return True
    a, b = t[i - 1], t[i]
    return a in _SEP or (b.isupper() and a.islower()) or (b.isdigit() and not a.isdigit())


def _is_subseq(q: str, tl: str, start: int = 0) -> bool:
    j = start
    for ch in q:
        j = tl.find(ch, j)
        if j < 0:
            return False
        j += 1
    return True


def _score(t: str, pos: list[int]) -> float:
    s = 0.0
    prev = -2
    for p in pos:
        s += 1
        if p == prev + 1:
            s += 5
        elif prev >= 0:
            s -= min(3.0, 0.15 * (p - prev - 1))
        if _word_start(t, p):
            s += 7
        if p == 0:
            s += 5
        prev = p
    return s - 0.01 * len(t)


def _match_word(q: str, t: str, tl: str):
    if not _is_subseq(q, tl):
        return None
    # contiguous: prefer an occurrence that starts a word
    i = tl.find(q)
    if i >= 0:
        best = i
        j = i
        while j >= 0:
            if _word_start(t, j):
                best = j
                break
            j = tl.find(q, j + 1)
        pos = list(range(best, best + len(q)))
        return _score(t, pos) + 4 + 2 * len(q), pos
    # subsequence: continue a run > jump to a word start (when the rest still fits) > nearest
    pos: list[int] = []
    cur = 0
    for k, ch in enumerate(q):
        rest = q[k + 1:]
        if pos and cur < len(tl) and tl[cur] == ch and _is_subseq(rest, tl, cur + 1):
            pick = cur
        else:
            pick = -1
            j = tl.find(ch, cur)
            nearest = j
            while j >= 0:
                if _word_start(t, j) and _is_subseq(rest, tl, j + 1):
                    pick = j
                    break
                j = tl.find(ch, j + 1)
            if pick < 0:
                pick = nearest
        if pick < 0:
            return None
        pos.append(pick)
        cur = pick + 1
    return _score(t, pos), pos


def fuzzy_match(query: str, text: str):
    """VS Code like fuzzy match. Space separated words must all match (any order).
    Returns (score, sorted matched character positions) or None."""
    words = query.lower().split()
    if not words:
        return 0.0, []
    tl = text.lower()
    total, pos = 0.0, set()
    for w in words:
        r = _match_word(w, text, tl)
        if r is None:
            return None
        total += r[0]
        pos.update(r[1])
    return total, sorted(pos)


# ============================================================================ commands
@dataclass
class Command:
    id: str
    title: str
    callback: Callable
    category: str = ""
    shortcut: str = ""
    enabled: Callable | None = None
    visible: Callable | None = None          # VS Code: commandPalette `when` / `enablement` false -> not listed
    detail: str = ""

    @property
    def label(self) -> str:
        if not self.category or self.title.startswith(self.category + ":"):     # no "Laravel: Laravel: ..."
            return self.title
        return f"{self.category}: {self.title}"


_COMMANDS: dict[str, Command] = {}


def register_command(cmd_id: str, title: str, callback: Callable, category: str = "", shortcut: str = "",
                     enabled: Callable | None = None, visible: Callable | None = None, detail: str = "") -> Command:
    """Add an extra command to the palette (one that has no menu item). *enabled* is an optional
    callable returning bool (False: listed greyed); *visible* likewise (False: not listed - VS Code's when /
    enablement of extension commands). Registering the same id again replaces it."""
    c = Command(cmd_id, title, callback, category, shortcut, enabled, visible, detail)
    _COMMANDS[cmd_id] = c
    return c


def unregister_command(cmd_id: str) -> None:
    _COMMANDS.pop(cmd_id, None)


def commands() -> list[Command]:
    return list(_COMMANDS.values())


def clean_text(text: str) -> str:
    text = text.split("\t", 1)[0]
    return text.replace("&&", "\0").replace("&", "").replace("\0", "&").replace("...", "").strip()


@dataclass
class Item:
    label: str
    run: Callable | None = None
    detail: str = ""
    shortcut: str = ""
    key: str = ""
    enabled: bool = True
    score: float = 0.0
    pos: list = field(default_factory=list)          # matched positions in label
    dpos: list = field(default_factory=list)         # matched positions in detail


def _shortcut_text(a: QAction) -> str:
    sc = a.shortcut()
    if not sc.isEmpty():
        return sc.toString(QKeySequence.SequenceFormat.NativeText)
    t = a.text()
    return t.split("\t", 1)[1] if "\t" in t else ""


def _shown(a: QAction) -> str:
    """The label on screen (translated when the IDE is not in English - radide/i18n)."""
    from .. import i18n
    return i18n.shown(a) if i18n.language() != "en" else a.text()


def menu_actions(win) -> list[tuple[str, QAction]]:
    """(label, action) for every runnable action of the menu bar and the tool bars, VS Code style
    labels "Menu: Sub menu: Action"."""
    out: list[tuple[str, QAction]] = []
    seen: set[int] = set()

    def walk(menu: QMenu, path: list[str], depth=0):
        if depth > 6:
            return
        try:
            menu.aboutToShow.emit()            # dynamic menus fill / enable their items here
        except Exception:  # noqa: BLE001
            pass
        for a in menu.actions():
            if a.isSeparator() or not a.isVisible() or a.property("wbNoPalette"):
                continue
            t = clean_text(_shown(a))
            sub = a.menu()
            if sub is not None:
                walk(sub, path + [t], depth + 1)
                continue
            if not t or id(a) in seen:
                continue
            seen.add(id(a))
            out.append((": ".join(path + [t]), a))

    for a in win.menuBar().actions():
        if a.menu() is not None and a.isVisible() and not a.property("wbNoPalette"):
            walk(a.menu(), [clean_text(_shown(a))])
    for tb in win.findChildren(QToolBar):
        for a in tb.actions():
            if a.isSeparator() or a.menu() is not None or id(a) in seen or not clean_text(a.text()):
                continue
            if a.property("wbNoPalette"):
                continue
            seen.add(id(a))
            out.append((f"{clean_text(tb.windowTitle()) or 'Toolbar'}: {clean_text(_shown(a))}", a))
    return out


def command_items(win) -> list[Item]:
    items = []
    for label, a in menu_actions(win):
        def run(a=a):
            if a.isEnabled():
                a.trigger()
            else:
                win.statusBar().showMessage(f"'{clean_text(a.text())}' is not available right now", 4000)
        items.append(Item(label, run, shortcut=_shortcut_text(a), key="a:" + label, enabled=a.isEnabled()))
    keys = _extension_keys()
    seen_labels = {it.label.lower() for it in items}
    for c in _COMMANDS.values():
        try:
            if c.visible is not None and not c.visible():
                continue
        except Exception:  # noqa: BLE001
            continue
        try:
            en = bool(c.enabled()) if c.enabled else True
        except Exception:  # noqa: BLE001
            en = False
        label = _tr_label(c.label)
        items.append(Item(label, (lambda c=c: c.callback()), detail=c.detail, shortcut=c.shortcut or keys.get(c.id, ""),
                          key="c:" + c.id, enabled=en))
        seen_labels.add(label.lower())
    items += builtin_items(win, seen_labels)
    return items


def _tr_label(label: str) -> str:
    try:
        from .. import i18n
        return i18n.tr(label) if i18n.language() != "en" else label
    except Exception:  # noqa: BLE001
        return label


def _extension_keys() -> dict:
    """command id -> keybinding text of the extensions' contributes.keybindings / the user's keybindings.json."""
    out: dict = {}
    try:
        from ..vsx import contrib_keybindings as KB
        for b in KB.collect():
            out.setdefault(b["command"], KB.qt_sequence(b["key"]))
    except Exception:  # noqa: BLE001
        pass
    return out


BOUND_VSCODE_KEYS: dict = {}       # VS Code command id -> key text bound as a window shortcut (install_vscode_keys)


def builtin_items(win, seen_labels: set | None = None) -> list[Item]:
    """VS Code's own palette commands that RAD IDE runs (radide/vsx/vscode_commands.py): "View: Toggle Primary
    Side Bar Visibility", "Format Document", "Go Back" ... Editor commands only while an editor is active."""
    try:
        from ..vsx import vscode_commands as VC
    except Exception:  # noqa: BLE001
        return []
    has_editor = VC.active_editor(win) is not None
    seen = seen_labels if seen_labels is not None else set()
    out = []
    for e in VC.palette_entries(win):
        if e["editor"] and not has_editor:
            continue
        label = (e["category"] + ": " if e["category"] else "") + e["title"]
        label = _tr_label(label)
        if label.lower() in seen:
            continue
        seen.add(label.lower())
        key = BOUND_VSCODE_KEYS.get(e["id"]) or (VC.display_key(e["key"]) if e["editor"] else "")
        out.append(Item(label, (lambda cid=e["id"]: VC.execute(win, cid)), shortcut=key, key="v:" + e["id"],
                        detail=""))
    return out


# ============================================================================ files
SKIP_DIRS = {".git", ".svn", ".hg", "node_modules", "__pycache__", ".venv", "venv", "env", ".radide", ".idea",
             ".vs", ".vscode", ".mypy_cache", ".pytest_cache", ".tox", "bin", "obj", "target", "dist", "build",
             ".next", ".cache", "vendor", ".gradle", ".dart_tool"}
MAX_FILES = 20000


def project_roots(win) -> list[Path]:
    roots = []
    try:
        projects = win.projects() if hasattr(win, "projects") else []
    except Exception:  # noqa: BLE001
        projects = []
    if not projects and getattr(win, "project", None) is not None:
        projects = [win.project]
    for p in projects:
        try:
            roots.append(Path(p.folder).resolve())
        except (OSError, AttributeError):
            pass
    roots.sort(key=lambda r: len(str(r)))
    out: list[Path] = []
    for r in roots:            # a project inside another project's folder is listed once
        if not any(r == o or o in r.parents for o in out):
            out.append(r)
    return out


def list_files(roots: list[Path]) -> list[tuple[Path, str]]:
    """(absolute path, path shown) of the files below *roots* (VCS/build/package folders skipped)."""
    out: list[tuple[Path, str]] = []
    multi = len(roots) > 1
    for root in roots:
        stack = [root]
        while stack and len(out) < MAX_FILES:
            d = stack.pop()
            try:
                entries = list(os.scandir(d))
            except OSError:
                continue
            for e in entries:
                try:
                    if e.is_dir(follow_symlinks=False):
                        if e.name not in SKIP_DIRS and not e.name.endswith(".egg-info"):
                            stack.append(Path(e.path))
                    elif e.is_file():
                        p = Path(e.path)
                        rel = p.relative_to(root).as_posix()
                        out.append((p, f"{root.name}/{rel}" if multi else rel))
                except (OSError, ValueError):
                    continue
    return out


def open_path(win, path: Path, line: int | None = None) -> None:
    """Open a file of the solution in the IDE (forms in their designer)."""
    path = Path(path)
    if path.suffix.lower() == ".form":
        for st in (win.project_states() if hasattr(win, "project_states") else []):
            proj = st["project"]
            try:
                same_dir = Path(proj.folder).resolve() == path.parent.resolve()
            except OSError:
                same_dir = False
            if same_dir and path.stem in proj.forms:
                win.activate_project(proj)
                win.open_designer(path.stem)
                return
    opener = getattr(win, "open_file", None)
    if callable(opener):
        opener(str(path), line)
        return
    ed = win._editor_for_file(str(path))
    if ed is not None and line:
        ed.goto_line(line - 1)
    elif ed is None:
        win.statusBar().showMessage(f"Cannot open {path.name} here", 4000)


def current_file(win) -> Path | None:
    w = win.tabs.currentWidget() if hasattr(win, "tabs") else None
    for obj in (w, getattr(w, "editor", None)):
        p = getattr(obj, "path", None)
        if p:
            try:
                return Path(p).resolve()
            except OSError:
                return Path(p)
    return None



# ============================================================================ quick access helpers
def _t(text: str) -> str:
    """UI text of the palette (radide/i18n translates it in the Arabic UI)."""
    try:
        from .. import i18n
        return i18n.tr(text) if i18n.language() != "en" else text
    except Exception:  # noqa: BLE001
        return text


SYMBOL_KINDS = {1: "file", 2: "module", 3: "namespace", 4: "package", 5: "class", 6: "method", 7: "property",
                8: "field", 9: "constructor", 10: "enum", 11: "interface", 12: "function", 13: "variable",
                14: "constant", 15: "string", 16: "number", 17: "boolean", 18: "array", 19: "object", 20: "key",
                21: "null", 22: "enum member", 23: "struct", 24: "event", 25: "operator", 26: "type parameter"}
CODE_SUFFIXES = {".py", ".pyw", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".cs", ".vb", ".bas", ".frm", ".cls", ".java",
                 ".c", ".h", ".cpp", ".hpp", ".cc", ".rs", ".go", ".php", ".rb", ".lua", ".dart", ".pas", ".dpr",
                 ".kt", ".swift", ".ring", ".pl", ".ps1"}
_DECL = re.compile(
    r"^[ \t]*(?:(?:public|private|protected|friend|static|export|default|async|abstract|internal|sealed|final|"
    r"partial|virtual|override|pub(?:\([^)]*\))?|unsafe|extern|inline)[ \t]+)*"
    r"(?P<kw>def|class|function|func|fn|sub|property\s+(?:get|let|set)|type|struct|enum|interface|trait|impl|module|"
    r"namespace|procedure|record|object|const\s+fn)[ \t]+(?P<name>[A-Za-z_$][\w$]*)", re.I | re.M)


def scan_symbols(text: str) -> list[dict]:
    """Declarations found by a language-neutral scan (def / class / function / Sub / Function / fn / struct ...)
    - the outline when no language server or plugin gives one."""
    out = []
    for m in _DECL.finditer(text or ""):
        kw = m.group("kw").split()[0].lower()
        kind = {"def": "function", "func": "function", "fn": "function", "sub": "method", "property": "property",
                "impl": "class", "trait": "interface", "procedure": "function", "record": "struct",
                "object": "class", "const": "function", "type": "class"}.get(kw, kw)
        out.append({"name": m.group("name"), "kind": kind, "line": text.count("\n", 0, m.start())})
    return out


def _plugin_symbols(win, ed, text: str) -> list[dict]:
    plugin = None
    try:
        fp = getattr(win, "plugin_for_file", None)
        plugin = fp(str(ed.path)) if callable(fp) and getattr(ed, "path", None) else getattr(win, "plugin", None)
    except Exception:  # noqa: BLE001
        plugin = getattr(win, "plugin", None)
    out = []

    def walk(items, prefix=""):
        for s in items or []:
            if not isinstance(s, dict) or not s.get("name"):
                continue
            out.append({"name": str(s["name"]), "kind": str(s.get("kind") or ""), "line": int(s.get("line") or 0),
                        "detail": prefix})
            walk(s.get("children"), str(s["name"]))
    try:
        walk(plugin.document_symbols(text) if plugin is not None else [])
    except Exception:  # noqa: BLE001
        return []
    return out


def _lsp_symbols(res) -> list[dict]:
    """LSP DocumentSymbol[] / SymbolInformation[] -> [{name, kind, line, detail, path?}]."""
    out = []

    def walk(items, container=""):
        for s in items or []:
            if not isinstance(s, dict) or not s.get("name"):
                continue
            kind = SYMBOL_KINDS.get(s.get("kind"), "")
            if "location" in s:
                loc = s["location"] or {}
                rng = (loc.get("range") or {}).get("start") or {}
                uri = loc.get("uri") or ""
                path = ""
                if uri.startswith("file:"):
                    from urllib.parse import unquote, urlparse
                    u = urlparse(uri)
                    path = unquote(u.path)
                    if re.match(r"^/[A-Za-z]:", path):
                        path = path[1:]
                out.append({"name": s["name"], "kind": kind, "line": int(rng.get("line") or 0),
                            "detail": s.get("containerName") or kind, "path": path})
            else:
                rng = ((s.get("selectionRange") or s.get("range") or {}).get("start")) or {}
                out.append({"name": s["name"], "kind": kind, "line": int(rng.get("line") or 0),
                            "detail": (container + "  " if container else "") + kind})
                walk(s.get("children"), s["name"])
    walk(res if isinstance(res, list) else [])
    return out


def _read_jsonc(path: Path):
    import json
    try:
        from ..vsx.user_keybindings import strip_jsonc
        return json.loads(strip_jsonc(path.read_text("utf-8")))
    except (OSError, ValueError, ImportError):
        return None


def _workspace_folders(win) -> list[Path]:
    svc = getattr(win, "vsx_host", None)
    try:
        return [Path(f) for f in svc.folders()] if svc is not None else project_roots(win)
    except Exception:  # noqa: BLE001
        return project_roots(win)


def workspace_tasks(win) -> list[tuple[str, str]]:
    """(label, source) of the tasks in .vscode/tasks.json of the workspace folders."""
    out = []
    for f in _workspace_folders(win):
        data = _read_jsonc(f / ".vscode" / "tasks.json")
        for t in (data or {}).get("tasks", []) if isinstance(data, dict) else []:
            if isinstance(t, dict) and (t.get("label") or t.get("taskName")):
                out.append((str(t.get("label") or t.get("taskName")), f"tasks.json ({f.name})"))
    return out


def launch_configs(win) -> list[dict]:
    """configurations of .vscode/launch.json of the workspace folders."""
    out = []
    for f in _workspace_folders(win):
        data = _read_jsonc(f / ".vscode" / "launch.json")
        for c in (data or {}).get("configurations", []) if isinstance(data, dict) else []:
            if isinstance(c, dict):
                out.append(c)
    return out


# ============================================================================ the widget
ROLE = Qt.ItemDataRole.UserRole + 1


def _colors() -> dict:
    try:
        from .. import theme
        t = theme.current()
    except Exception:  # noqa: BLE001
        t = {}
    g = t.get
    return {"back": g("menu", "#FAFAF7"), "text": g("menu_text", "#000000"), "border": g("menu_border", "#8A8A8A"),
            "sel": g("menu_sel", "#C1D2EE"), "sel_text": g("menu_sel_text", "#000000"), "muted": g("muted", "#5A5A5A"),
            "match": g("link", "#0645AD"), "input": g("base", "#FFFFFF"), "input_text": g("text", "#000000"),
            "focus": g("highlight", "#316AC5"), "disabled": g("disabled", "#8A8A8A"), "key": g("button", "#ECECE6"),
            "dark": bool(g("dark", False))}


def _hl(text: str, pos, color: str) -> str:
    if not pos:
        return html.escape(text)
    ps = set(pos)
    out = []
    for i, ch in enumerate(text):
        e = html.escape(ch)
        out.append(f'<span style="color:{color};font-weight:700">{e}</span>' if i in ps else e)
    return "".join(out)


class _Delegate(QStyledItemDelegate):
    H = 26

    def sizeHint(self, opt, idx):
        return QSize(opt.rect.width(), self.H)

    def paint(self, p: QPainter, opt, idx):
        it: Item = idx.data(ROLE)
        if it is None:
            return super().paint(p, opt, idx)
        c = _colors()
        sel = bool(opt.state & QStyle.StateFlag.State_Selected)
        r = opt.rect
        p.save()
        if sel:
            p.fillRect(r, QColor(c["sel"]))
        text = c["sel_text"] if sel else (c["text"] if it.enabled else c["disabled"])
        match = c["sel_text"] if sel else c["match"]
        muted = c["sel_text"] if sel else c["muted"]
        # shortcut on the right
        right = r.right() - 8
        if it.shortcut:
            f = opt.font
            p.setFont(f)
            fm = p.fontMetrics()
            w = fm.horizontalAdvance(it.shortcut) + 10
            box = QRectF(right - w, r.top() + 4, w, r.height() - 8)
            p.setPen(QColor(muted))
            p.setBrush(QColor(c["key"]) if not sel else Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(box, 3, 3)
            p.setPen(QColor(text))
            p.drawText(box, Qt.AlignmentFlag.AlignCenter, it.shortcut)
            right -= w + 8
        doc = QTextDocument()
        doc.setDefaultFont(opt.font)
        doc.setDocumentMargin(0)
        body = f'<span style="color:{text}">{_hl(it.label, it.pos, match)}</span>'
        if it.detail:
            body += f'&nbsp;&nbsp;<span style="color:{muted}">{_hl(it.detail, it.dpos, match)}</span>'
        doc.setHtml(f"<div style='white-space:pre'>{body}</div>")
        avail = max(10, right - r.left() - 10)
        p.translate(r.left() + 10, r.top() + (r.height() - doc.size().height()) / 2)
        p.setClipRect(QRectF(0, 0, avail, r.height()))
        doc.drawContents(p, QRectF(0, 0, avail, r.height()))
        p.restore()


class QuickInput(QFrame):
    """The VS Code quick input box (child overlay of the main window)."""
    MAX_ROWS = 13
    LIMIT = 300

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setObjectName("radQuickInput")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.edit = QLineEdit(self)
        self.edit.setObjectName("radQuickInputEdit")
        self.hint = QLabel(self)
        self.hint.setObjectName("radQuickInputHint")
        self.list = QListWidget(self)
        self.list.setObjectName("radQuickInputList")
        self.list.setItemDelegate(_Delegate(self.list))
        self.list.setUniformItemSizes(True)
        self.list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.itemClicked.connect(lambda _it: self.accept())
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(4)
        lay.addWidget(self.edit)
        lay.addWidget(self.hint)
        lay.addWidget(self.list)
        sh = QGraphicsDropShadowEffect(self)
        sh.setBlurRadius(18)
        sh.setOffset(0, 4)
        sh.setColor(QColor(0, 0, 0, 110))
        self.setGraphicsEffect(sh)
        self.edit.textChanged.connect(self._refresh)
        self.edit.installEventFilter(self)
        self._files: list[tuple[Path, str]] | None = None
        self._files_at = 0.0
        self._files_roots: list[Path] = []
        self._cmd_cache: list[Item] | None = None
        self.hide()
        self.restyle()
        try:
            from .. import theme
            from PyQt6 import sip
            theme.changed.connect(lambda *_: None if sip.isdeleted(self) else self.restyle())
        except Exception:  # noqa: BLE001
            pass
        app = QApplication.instance()
        if app is not None:
            app.focusChanged.connect(self._on_focus)

    # ------------------------------------------------------------------ look
    def restyle(self):
        c = _colors()
        self.setStyleSheet(f"""
QFrame#radQuickInput {{ background: {c['back']}; border: 1px solid {c['border']}; border-radius: 6px; }}
QLineEdit#radQuickInputEdit {{ background: {c['input']}; color: {c['input_text']}; border: 1px solid {c['focus']};
                               padding: 4px 6px; border-radius: 3px; font-size: 10pt; }}
QLabel#radQuickInputHint {{ color: {c['muted']}; padding: 0 4px; }}
QListWidget#radQuickInputList {{ background: {c['back']}; color: {c['text']}; border: none; outline: none; }}
""")

    # ------------------------------------------------------------------ open / close
    def open(self, text: str = ""):
        self._cmd_cache = None
        self._async_cache = {}                # symbols / tasks are asked again each time the box opens
        if not text.startswith(">"):
            self._files = None            # re-list the files (cheap) every time Quick Open opens
        self._place()
        self.show()
        self.raise_()
        self.edit.blockSignals(True)
        self.edit.setText(text)
        self.edit.blockSignals(False)
        self._refresh()
        self.edit.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.edit.setCursorPosition(len(text))

    def close_box(self):
        if self.isVisible():
            self.hide()

    def _place(self):
        w = self.win
        width = int(min(680, max(420, w.width() * 0.5)))
        width = min(width, max(200, w.width() - 20))
        top = w.menuBar().geometry().bottom() + 6 if w.menuBar().isVisible() else 8
        rows = max(1, min(self.MAX_ROWS, self.list.count()))
        h = 6 + self.edit.sizeHint().height() + 4 + (self.hint.sizeHint().height() + 4 if self.hint.isVisible()
                                                     else 0) + rows * _Delegate.H + 10
        self.setGeometry((w.width() - width) // 2, top, width, h)

    def _on_focus(self, _old, new):
        if not self.isVisible():
            return
        if new is None or (new is not self and not self.isAncestorOf(new)):
            self.hide()

    def eventFilter(self, obj, ev):
        if obj is self.edit and ev.type() == QEvent.Type.KeyPress:
            k = ev.key()
            if k == Qt.Key.Key_Escape:
                self.hide()
                return True
            if k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.accept()
                return True
            if k in (Qt.Key.Key_Down, Qt.Key.Key_Up, Qt.Key.Key_PageDown, Qt.Key.Key_PageUp):
                n = self.list.count()
                if n:
                    step = {Qt.Key.Key_Down: 1, Qt.Key.Key_Up: -1, Qt.Key.Key_PageDown: 10,
                            Qt.Key.Key_PageUp: -10}[k]
                    row = self.list.currentRow()
                    row = (row + step) % n if abs(step) == 1 else max(0, min(n - 1, row + step))
                    self.list.setCurrentRow(row)
                return True
        return super().eventFilter(obj, ev)

    # ------------------------------------------------------------------ data
    def _commands(self) -> list[Item]:
        if self._cmd_cache is None:
            self._cmd_cache = command_items(self.win)
        return self._cmd_cache

    def files(self) -> list[tuple[Path, str]]:
        roots = project_roots(self.win)
        if self._files is None or roots != self._files_roots or time.monotonic() - self._files_at > 15:
            self._files = list_files(roots)
            self._files_roots = roots
            self._files_at = time.monotonic()
        return self._files

    def _recent(self) -> list[str]:
        try:
            v = self.win.settings.value("workbench/palette/recent", [])
        except Exception:  # noqa: BLE001
            return []
        if isinstance(v, str):
            v = [v]
        return [str(x) for x in (v or [])]

    def _remember(self, key: str):
        if not key:
            return
        r = [k for k in self._recent() if k != key]
        r.insert(0, key)
        try:
            self.win.settings.setValue("workbench/palette/recent", r[:12])
        except Exception:  # noqa: BLE001
            pass

    def _items(self, text: str) -> tuple[list[Item], str]:
        if text.startswith(">"):
            return self._command_results(text[1:].strip())
        if text.startswith(":"):
            return self._line_results(text[1:].strip())
        if text.startswith("?"):
            return self._help(), _t("Type one of the prefixes below")
        if text.startswith("@"):
            return self._symbol_results(text[1:])
        if text.startswith("#"):
            return self._workspace_symbol_results(text[1:].strip())
        for prefix, fn in (("view ", self._view_results), ("task ", self._task_results),
                           ("debug ", self._debug_results), ("ext install ", self._ext_install_results),
                           ("ext ", self._ext_results), ("edt ", self._editor_results),
                           ("term ", self._terminal_results), ("recent ", self._recent_results)):
            if text.startswith(prefix):
                return fn(text[len(prefix):].strip())
        return self._file_results(text.strip())

    # ------------------------------------------------------------------ VS Code quick access providers
    def _filter(self, items: list[Item], q: str, empty_hint: str):
        if not q:
            return items[:self.LIMIT], ""
        out = []
        for it in items:
            m = fuzzy_match(q, it.label)
            if m is not None:
                it.score, it.pos = m[0], m[1]
                out.append(it)
            elif it.detail and fuzzy_match(q, it.detail) is not None:
                it.score, it.pos = -1, []
                out.append(it)
        out.sort(key=lambda i: -i.score)
        return out[:self.LIMIT], ("" if out else empty_hint)

    def _editor(self):
        try:
            from ..vsx.vscode_commands import active_editor
            return active_editor(self.win)
        except Exception:  # noqa: BLE001
            cv = self.win._current_code() if hasattr(self.win, "_current_code") else None
            return getattr(cv, "editor", None)

    def _async(self, key: str, start):
        """Results that arrive later (language servers / the extension host): start(cb) once per key."""
        cache = self.__dict__.setdefault("_async_cache", {})
        if key in cache:
            return cache[key]
        cache[key] = None

        def done(items, key=key):
            from PyQt6 import sip
            if sip.isdeleted(self):
                return
            cache[key] = items or []
            if self.isVisible():
                self._refresh()
        try:
            start(done)
        except Exception:  # noqa: BLE001
            cache[key] = []
        return cache[key]

    def _symbol_results(self, q: str):
        """@ - Go to Symbol in Editor (Ctrl+Shift+O): the language server's / extensions' document symbols,
        else the language plugin's outline, else a declaration scan. "@:" groups by kind."""
        ed = self._editor()
        if ed is None:
            return [Item(_t("Open an editor first to go to a symbol"), None, enabled=False)], ""
        by_kind = q.startswith(":")
        q = q[1:].strip() if by_kind else q.strip()
        path = str(getattr(ed, "path", ""))
        text = ed.text() if hasattr(ed, "text") else ""
        key = f"doc:{path}:{hash(text)}"
        lsp = getattr(ed, "lsp", None)
        syms = None
        if lsp is not None and hasattr(lsp, "_request"):
            def start(cb, lsp=lsp, path=path):
                from pathlib import Path as _P
                lsp._request("textDocument/documentSymbol", {"textDocument": {"uri": _P(path).resolve().as_uri()}},
                             lambda r: cb(_lsp_symbols(r)))
            syms = self._async(key, start)
        if not syms:
            syms = _plugin_symbols(self.win, ed, text) or scan_symbols(text)
        items = []
        for s in syms:
            line = s["line"]
            items.append(Item(s["name"], (lambda line=line: self._goto(ed, line)), s.get("detail") or s.get("kind", ""),
                              key=""))
        if by_kind:
            items.sort(key=lambda i: (i.detail, i.label.lower()))
        res, hint = self._filter(items, q, _t("No matching symbols"))
        if not syms:
            hint = _t("Loading symbols...") if self.__dict__.get("_async_cache", {}).get(key, 0) is None else \
                _t("No symbols in this editor")
        return res, hint

    def _goto(self, ed, line: int):
        try:
            ed.goto_line(line)
            ed.setFocus()
        except Exception:  # noqa: BLE001
            pass

    def _workspace_symbol_results(self, q: str):
        """# - Go to Symbol in Workspace (Ctrl+T): workspace/symbol of the language servers + a declaration
        scan of the solution's code files."""
        if not q:
            return [Item(_t("Type the name of a symbol to search the workspace"), None, enabled=False)], ""
        items: list[Item] = []
        ed = self._editor()
        lsp = getattr(ed, "lsp", None) if ed is not None else None
        if lsp is not None and hasattr(lsp, "_request"):
            got = self._async(f"ws:{q}", lambda cb, lsp=lsp: lsp._request("workspace/symbol", {"query": q},
                                                                         lambda r: cb(_lsp_symbols(r))))
            for s in got or []:
                p = s.get("path")
                if p:
                    items.append(Item(s["name"], (lambda p=p, ln=s["line"]: open_path(self.win, Path(p), ln + 1)),
                                      f"{s.get('kind', '')}  {Path(p).name}"))
        seen = {(i.label, i.detail) for i in items}
        for p, shown in self.files()[:4000]:
            if p.suffix.lower() not in CODE_SUFFIXES:
                continue
            try:
                if p.stat().st_size > 400_000:
                    continue
                text = p.read_text("utf-8", errors="replace")
            except OSError:
                continue
            for s in scan_symbols(text):
                if fuzzy_match(q, s["name"]) is None:
                    continue
                d = f"{s['kind']}  {shown}"
                if (s["name"], d) not in seen:
                    items.append(Item(s["name"], (lambda p=p, ln=s["line"]: open_path(self.win, p, ln + 1)), d))
            if len(items) > 2000:
                break
        return self._filter(items, q, _t("No matching workspace symbols"))

    def _view_results(self, q: str):
        """view - Open View: the IDE's tool windows and the extensions' views."""
        from PyQt6.QtWidgets import QDockWidget
        items = []
        for d in self.win.findChildren(QDockWidget):
            title = d.windowTitle().replace("&", "")
            if not title:
                continue
            shown = _tr_label(title)

            def show(d=d):
                d.show()
                d.raise_()
                if d.widget() is not None:
                    d.widget().setFocus()
            items.append(Item(shown, show, _t("Panel") if "Output" in title or "Terminal" in title else _t("View")))
        svc = getattr(self.win, "vsx_host", None)
        try:
            for vid, info in (svc.views.all_views() if svc is not None and hasattr(svc.views, "all_views") else []):
                from ..vsx import vscode_commands as VC
                items.append(Item(str(info.get("name") or vid), (lambda vid=vid: VC.execute(self.win, vid + ".focus")),
                                  str(info.get("container") or "Extension")))
        except Exception:  # noqa: BLE001
            pass
        items.sort(key=lambda i: i.label.lower())
        return self._filter(items, q, _t("No matching views"))

    def _task_results(self, q: str):
        """task - Run Task: .vscode/tasks.json of the workspace and the extensions' task providers."""
        items = []
        svc = getattr(self.win, "vsx_host", None)
        for label, src in workspace_tasks(self.win):
            items.append(Item(label, (lambda label=label: self._run_task(label)), src))
        if svc is not None and svc.host.running():
            got = self._async("tasks", lambda cb: svc.execute("_radide.listTasks", [], lambda r: cb(
                [Item(t.get("name", ""), (lambda t=t: self._run_task(t.get("name", ""))), t.get("source", ""))
                 for t in (r or []) if isinstance(t, dict)])))
            labels = {i.label for i in items}
            items += [i for i in (got or []) if i.label not in labels]
        if not items:
            return [Item(_t("No tasks found - add .vscode/tasks.json or install an extension with tasks"), None,
                         enabled=False)], ""
        return self._filter(items, q, _t("No matching tasks"))

    def _run_task(self, label: str):
        svc = getattr(self.win, "vsx_host", None)
        if svc is not None:
            svc.execute("workbench.action.tasks.runTask", [label])

    def _debug_results(self, q: str):
        """debug - Select and Start Debugging: launch.json configurations, then Start Debugging."""
        items = []
        svc = getattr(self.win, "vsx_host", None)
        for cfg in launch_configs(self.win):
            name = str(cfg.get("name") or cfg.get("type") or "?")

            def go(cfg=cfg):
                if svc is not None:
                    svc.debug_start(config=cfg)
            items.append(Item(name, go, str(cfg.get("type") or "")))
        from ..vsx import contrib_keybindings as KB
        items.append(Item(_t("Start Debugging"), lambda: KB.run_command(self.win, "workbench.action.debug.start"), "F5"))
        items.append(Item(_t("Run Without Debugging"), lambda: KB.run_command(self.win, "workbench.action.debug.run"),
                          "Ctrl+F5"))
        items.append(Item(_t("Add Configuration..."), lambda: __import__("radide.vsx.vscode_commands", fromlist=["x"])
                          .execute(self.win, "workbench.action.debug.configure"), "launch.json"))
        return self._filter(items, q, _t("No matching launch configurations"))

    def _ext_results(self, q: str):
        """ext - the Extensions commands (VS Code: "ext " lists the extension management commands)."""
        from ..vsx import vscode_commands as VC
        items = [Item(_t("Extensions: Install Extensions"), lambda: VC.execute(self.win, "workbench.view.extensions")),
                 Item(_t("Extensions: Show Installed Extensions"),
                      lambda: VC.execute(self.win, "workbench.extensions.action.showInstalledExtensions")),
                 Item(_t("Extensions: Check for Extension Updates"),
                      lambda: VC.execute(self.win, "workbench.extensions.action.checkForUpdates")),
                 Item(_t("Extensions: Install from VSIX..."), lambda: self._vsx_view_action("install_from_vsix")),
                 Item(_t("Developer: Restart Extension Host"),
                      lambda: VC.execute(self.win, "workbench.action.restartExtensionHost"))]
        for it in self._commands():
            if it.label.lower().startswith(("extensions:", "extension:")) and it.label not in {i.label for i in items}:
                items.append(it)
        return self._filter(items, q, _t("No matching commands"))

    def _vsx_view_action(self, name: str):
        try:
            from . import vsx_market
            vsx_market.show_view(self.win)
            getattr(self.win.vsx_view, name)()
        except Exception as e:  # noqa: BLE001
            self.win.log(f"[command palette] {e}")

    def _ext_install_results(self, q: str):
        """ext install <id or words> - search Open VSX in the Extensions view."""
        def go():
            from ..vsx import ide_commands
            ide_commands._extensions_view(self.win, q)
        label = _t("Search Open VSX for") + f" '{q}'" if q else _t("Type an extension name or id to install")
        return [Item(label, go if q else None, "Open VSX", enabled=bool(q))], ""

    def _editor_results(self, q: str):
        """edt - Show All Editors (open tabs)."""
        items = []
        tabs = getattr(self.win, "tabs", None)
        for i in range(tabs.count() if tabs is not None else 0):
            w = tabs.widget(i)
            p = getattr(w, "path", None) or getattr(getattr(w, "editor", None), "path", None)
            items.append(Item(tabs.tabText(i).rstrip("*"), (lambda i=i: tabs.setCurrentIndex(i)),
                              str(Path(p).parent) if p else ""))
        for word in ("mru ", "active "):
            if q.startswith(word.strip()):
                q = q[len(word.strip()):].strip()
        return self._filter(items, q, _t("No matching editors"))

    def _terminal_results(self, q: str):
        """term - the terminals of the Terminal panel (and New Terminal)."""
        from ..vsx import vscode_commands as VC
        items = [Item(_t("Create New Terminal"), lambda: VC.execute(self.win, "workbench.action.terminal.new"))]
        svc = getattr(self.win, "vsx_host", None)
        panel = getattr(getattr(svc, "workbench", None), "terminals", None) if svc is not None else None
        tabs = getattr(panel, "tabs", None)
        for i in range(tabs.count() if tabs is not None else 0):
            def show(i=i):
                tabs.setCurrentIndex(i)
                d = panel.ensure_dock()
                d.show()
                d.raise_()
            items.append(Item(tabs.tabText(i), show, _t("Terminal")))
        return self._filter(items, q, _t("No matching terminals"))

    def _recent_results(self, q: str):
        """recent - File > Open Recent (solutions / projects / folders)."""
        items = []
        try:
            recent = self.win.recent_projects() if hasattr(self.win, "recent_projects") else []
        except Exception:  # noqa: BLE001
            recent = []
        for r in recent:
            p = Path(r)
            items.append(Item(p.name, (lambda p=p: self.win.open_project(p)), str(p.parent)))
        return self._filter(items, q, _t("No matching recent projects"))

    def _command_results(self, q: str):
        items = self._commands()
        if not q:
            recent = self._recent()
            by_key = {it.key: it for it in items}
            top = []
            for k in recent:
                it = by_key.get(k)
                if it is not None:
                    top.append(Item(it.label, it.run, _t("recently used"), it.shortcut, it.key, it.enabled))
            rest = sorted((it for it in items if it.key not in set(recent)), key=lambda i: i.label.lower())
            for it in rest:
                it.pos = []
            return top + rest, f"{len(items)} commands - type to filter"
        out = []
        for it in items:
            m = fuzzy_match(q, it.label)
            if m is not None:
                it.score, it.pos = m[0] + (0 if it.enabled else -5), m[1]
                out.append(it)
        out.sort(key=lambda i: (-i.score, len(i.label)))
        return out[:self.LIMIT], ("" if out else "No matching commands")

    def _file_results(self, q: str):
        if not project_roots(self.win):
            return [Item("Open a project or solution first", None, enabled=False)], ""
        line = None
        if ":" in q:
            head, _, tail = q.rpartition(":")
            if tail.isdigit() and head:
                q, line = head, int(tail)
        files = self.files()
        if not q:
            seen, out = set(), []
            for i in range(self.win.tabs.count()):        # open editors first
                w = self.win.tabs.widget(i)
                p = getattr(w, "path", None) or getattr(getattr(w, "editor", None), "path", None)
                if p and str(p) not in seen:
                    seen.add(str(p))
                    out.append(Item(Path(p).name, (lambda p=Path(p): open_path(self.win, p)), "open editor"))
            for p, shown in files[:self.LIMIT]:
                if str(p) not in seen:
                    d = shown.rpartition("/")[0]
                    out.append(Item(p.name, (lambda p=p: open_path(self.win, p)), d))
            return out[:self.LIMIT], f"{len(files)} files - type to search (name:line opens at a line)"
        out = []
        want_path = "/" in q or "\\" in q
        qn = q.replace("\\", "/")
        for p, shown in files:
            name = p.name
            d = shown[:len(shown) - len(name) - 1] if len(shown) > len(name) else ""
            m = None if want_path else fuzzy_match(qn, name)
            if m is not None:
                score, pos, dpos = m[0] * 2 + 10, m[1], []
            else:
                m = fuzzy_match(qn, shown)
                if m is None:
                    continue
                cut = len(shown) - len(name)
                score = m[0]
                pos = [i - cut for i in m[1] if i >= cut]
                dpos = [i for i in m[1] if i < len(d)]
            out.append(Item(name, (lambda p=p: open_path(self.win, p, line)), d, score=score - 0.02 * len(shown),
                            pos=pos, dpos=dpos))
        out.sort(key=lambda i: (-i.score, len(i.detail), i.label.lower()))
        return out[:self.LIMIT], ("" if out else "No matching files")

    def _line_results(self, q: str):
        cv = self.win._current_code() if hasattr(self.win, "_current_code") else None
        ed = getattr(cv, "editor", None)
        if ed is None:
            return [Item("Open an editor first to go to a line", None, enabled=False)], ""
        try:
            total = ed.lines() if hasattr(ed, "lines") else ed.blockCount()
        except Exception:  # noqa: BLE001
            total = 0
        parts = q.replace(",", ":").split(":")
        if not parts[0].isdigit():
            return [Item(f"Type a line number between 1 and {total}", None, enabled=False)], ""
        line = max(1, min(int(parts[0]), total or int(parts[0])))
        col = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None

        def go():
            if col and hasattr(ed, "setCursorPosition"):
                ed.setCursorPosition(line - 1, col - 1)
                if hasattr(ed, "ensureLineVisible"):
                    ed.ensureLineVisible(line - 1)
                ed.setFocus()
            else:
                ed.goto_line(line - 1)
        label = f"Go to line {line}" + (f", column {col}" if col else "")
        return [Item(label, go, f"of {total}")], ""

    def _help(self) -> list[Item]:
        rows = [("", "Go to File", "Ctrl+P"), (">", "Show and Run Commands", "Ctrl+Shift+P"),
                ("@", "Go to Symbol in Editor", "Ctrl+Shift+O"), ("@:", "Go to Symbol in Editor by Category", ""),
                ("#", "Go to Symbol in Workspace", "Ctrl+T"), (":", "Go to Line/Column", "Ctrl+G"),
                ("view ", "Open View", ""), ("edt ", "Show All Opened Editors By Appearance", ""),
                ("term ", "Show All Opened Terminals", ""), ("task ", "Run Task", ""),
                ("debug ", "Start Debugging", ""), ("ext ", "Manage Extensions", ""),
                ("ext install ", "Install or Search Extensions", ""), ("recent ", "Open Recent", ""),
                ("?", "Help", "")]
        return [Item(f"{p or '…'}  {_t(t)}", (lambda p=p: QTimer.singleShot(0, lambda: self.open(p))), shortcut=k)
                for p, t, k in rows]

    # ------------------------------------------------------------------ list
    def _refresh(self):
        text = self.edit.text()
        try:
            items, hint = self._items(text)
        except Exception as e:  # noqa: BLE001 - the palette must never break
            items, hint = [Item(f"Error: {e}", None, enabled=False)], ""
        self.list.clear()
        for it in items:
            li = QListWidgetItem()
            li.setData(ROLE, it)
            li.setToolTip(it.label + (f"  ({it.detail})" if it.detail else ""))
            self.list.addItem(li)
        if self.list.count():
            self.list.setCurrentRow(0)
        self.hint.setText(hint)
        self.hint.setVisible(bool(hint))
        self._place()

    def current_items(self) -> list[Item]:
        return [self.list.item(i).data(ROLE) for i in range(self.list.count())]

    def accept(self):
        li = self.list.currentItem()
        it: Item | None = li.data(ROLE) if li is not None else None
        if it is None or it.run is None:
            return
        self.hide()
        if it.key:
            self._remember(it.key)

        def run():
            try:
                it.run()
            except Exception as e:  # noqa: BLE001
                self.win.log(f"[command palette] {it.label}: {e}")
        QTimer.singleShot(0, run)


# ============================================================================ install
def _box(win) -> QuickInput:
    box = getattr(win, "command_palette", None)
    if box is None:
        box = QuickInput(win)
        win.command_palette = box
    return box


def show_palette(win, text: str = ">") -> QuickInput:
    box = _box(win)
    box.open(text if text.startswith(">") else ">" + text)
    return box


def quick_open(win, text: str = "") -> QuickInput:
    box = _box(win)
    box.open(text)
    return box


def goto_line(win) -> QuickInput:
    box = _box(win)
    box.open(":")
    return box


class _Resize(QObject):
    def __init__(self, win):
        super().__init__(win)
        self.win = win

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Type.Resize:
            box = getattr(self.win, "command_palette", None)
            if box is not None and box.isVisible():
                box._place()
        return False


def install(win) -> None:
    _box(win)
    win._palette_resize = _Resize(win)
    win.installEventFilter(win._palette_resize)
    a1 = QAction("Command &Palette...", win)
    a1.setShortcut(QKeySequence("Ctrl+Shift+P"))
    a1.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
    a1.triggered.connect(lambda: show_palette(win))
    a1.setProperty("wbNoPalette", True)
    a2 = QAction("&Quick Open (Go to File)...", win)
    a2.setShortcut(QKeySequence("Ctrl+P"))
    a2.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
    a2.triggered.connect(lambda: quick_open(win))
    a2.setProperty("wbNoPalette", True)
    for a in (a1, a2):
        win.addAction(a)            # keep the shortcuts alive even with the menu bar hidden (Zen mode)
    win.a_command_palette, win.a_quick_open = a1, a2
    view = next((x.menu() for x in win.menuBar().actions() if x.text().replace("&", "") == "View"), None)
    if view is not None:
        first = view.actions()[0] if view.actions() else None
        view.insertAction(first, a1)
        view.insertAction(first, a2)
        view.insertSeparator(first)
    register_command("workbench.gotoLine", "Go to Line/Column...", lambda: goto_line(win), "Go")
    # VS Code's other quick access keys - only where the IDE does not use the key already
    for key, text, name in (("Ctrl+G", ":", "a_vsc_goto_line"), ("Ctrl+Shift+O", "@", "a_vsc_goto_symbol"),
                            ("Ctrl+T", "#", "a_vsc_workspace_symbol")):
        if _key_in_use(win, key):
            continue
        a = QAction(text, win)
        a.setShortcut(QKeySequence(key))
        a.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        a.triggered.connect(lambda _=False, t=text: quick_open(win, t))
        a.setProperty("wbNoPalette", True)
        win.addAction(a)
        setattr(win, name, a)
    QTimer.singleShot(2500, lambda: install_vscode_keys(win))       # after every feature added its shortcuts


def _key_in_use(win, key: str) -> bool:
    want = QKeySequence(key).toString()
    for a in win.findChildren(QAction):
        if any(sc.toString() == want for sc in a.shortcuts()):
            return True
    try:
        from PyQt6.QtGui import QShortcut
        for sc in win.findChildren(QShortcut):
            if sc.key().toString() == want and sc.isEnabled():
                return True
    except Exception:  # noqa: BLE001
        pass
    return False


def install_vscode_keys(win) -> int:
    """VS Code's default keybindings of the workbench commands RAD IDE runs (Ctrl+B side bar, Ctrl+J panel,
    Alt+Left go back, Ctrl+Shift+T reopen closed editor, Ctrl+K Ctrl+S keyboard shortcuts ...) as window
    shortcuts - only keys the IDE does not use (its own Visual Studio keys win). Editor commands keep Monaco's
    bindings. Returns how many were added; BOUND_VSCODE_KEYS shows them in the palette."""
    from PyQt6 import sip
    if sip.isdeleted(win):
        return 0
    try:
        from ..vsx import vscode_commands as VC
    except Exception:  # noqa: BLE001
        return 0
    n = 0
    for e in VC.palette_entries(win):
        if e["editor"] or not e["key"]:
            continue
        # only unconditional single chords with Ctrl / Alt: a chord (ctrl+k ...) would swallow Monaco's chords,
        # a "when"-bound or unmodified key belongs to a list / widget that RAD IDE does not have
        kb = next((k for k in VC.reference().get(e["id"], {}).get("keybinding") or []
                   if (k.get("win") or k.get("key") or "").lower() == e["key"]), {})
        if " " in e["key"] or not any(m in e["key"] for m in ("ctrl+", "alt+")) or \
                str(kb.get("when") or "undefined") not in ("undefined", "", "None"):
            continue
        seq_text = VC.display_key(e["key"])
        seq = QKeySequence(seq_text)
        if seq.isEmpty() or _key_in_use(win, seq_text):
            continue
        a = QAction(e["title"], win)
        a.setShortcut(seq)
        a.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        a.setProperty("wbNoPalette", True)
        a.setObjectName("vscodeKey:" + e["id"])
        a.triggered.connect(lambda _=False, cid=e["id"]: VC.execute(win, cid))
        win.addAction(a)
        BOUND_VSCODE_KEYS[e["id"]] = seq.toString(QKeySequence.SequenceFormat.NativeText)
        n += 1
    return n


__all__ = ["Command", "Item", "QuickInput", "command_items", "commands", "fuzzy_match", "goto_line", "list_files",
           "menu_actions", "open_path", "project_roots", "quick_open", "register_command", "show_palette",
           "unregister_command", "current_file", "clean_text"]
