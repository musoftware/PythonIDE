"""Command Palette (Ctrl+Shift+P) and Quick Open (Ctrl+P) - CONTRACTS 9.2.

One VS Code style "quick input" box that works in every workbench layout:
  * ">"  commands: every QAction of the menu bar (and of the tool bars) plus the extra commands that
         features register with register_command(); recently used commands come first,
  * ""   Quick Open: fuzzy search over the files of every project of the solution ("name:12" opens at line 12),
  * ":"  go to line (":42" or ":42:7") in the current editor,
  * "?"  help.

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

    @property
    def label(self) -> str:
        if not self.category or self.title.startswith(self.category + ":"):     # no "Laravel: Laravel: ..."
            return self.title
        return f"{self.category}: {self.title}"


_COMMANDS: dict[str, Command] = {}


def register_command(cmd_id: str, title: str, callback: Callable, category: str = "", shortcut: str = "",
                     enabled: Callable | None = None) -> Command:
    """Add an extra command to the palette (one that has no menu item). *enabled* is an optional
    callable returning bool. Registering the same id again replaces it."""
    c = Command(cmd_id, title, callback, category, shortcut, enabled)
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
    for c in _COMMANDS.values():
        try:
            en = bool(c.enabled()) if c.enabled else True
        except Exception:  # noqa: BLE001
            en = False
        items.append(Item(c.label, (lambda c=c: c.callback()), shortcut=c.shortcut, key="c:" + c.id, enabled=en))
    return items


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
            return self._help(), "Type one of the prefixes below"
        return self._file_results(text.strip())

    def _command_results(self, q: str):
        items = self._commands()
        if not q:
            recent = self._recent()
            by_key = {it.key: it for it in items}
            top = []
            for k in recent:
                it = by_key.get(k)
                if it is not None:
                    top.append(Item(it.label, it.run, "recently used", it.shortcut, it.key, it.enabled))
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
        rows = [(">", "Show and run commands"), ("", "Go to file (Quick Open)"),
                (":", "Go to line in the current editor"), ("?", "Help")]
        return [Item(f"{p or '…'}  {t}", (lambda p=p: QTimer.singleShot(0, lambda: self.open(p)))) for p, t in rows]

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


__all__ = ["Command", "Item", "QuickInput", "command_items", "commands", "fuzzy_match", "goto_line", "list_files",
           "menu_actions", "open_path", "project_roots", "quick_open", "register_command", "show_palette",
           "unregister_command", "current_file", "clean_text"]
