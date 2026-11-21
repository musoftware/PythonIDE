"""Translation of the IDE's own user interface (English source text -> other languages).

The IDE code is written in English and stays that way.  This module translates what the
user *sees* without touching the rest of the code base:

* ``tr(text)``                 - translate one English string (catalog radide/i18n/<lang>.json,
                                 keyed by the English text; f-string shapes like ``"Branch: {}"``
                                 are matched as patterns).  Mnemonics (&File), a trailing
                                 ``\\tShortcut``, ``...`` and ``:`` are kept.
* ``set_language(app, lang)``  - switch at run time: loads the catalog and Qt's own translation
                                 (standard buttons, file dialogs), sets the layout direction
                                 (right-to-left for Arabic; code editors, the form designer and web
                                 views stay left-to-right) and translates every open window.
                                 ``set_language(app, "en")`` restores the English text.
* While a language other than English is active, an application event filter translates
  every widget when it is shown and every action when it is added to a menu / tool bar,
  and the common text setters (``QAction.setText``, ``QLabel.setText``, ``setWindowTitle``,
  ``setTabText``, ``showMessage``, ``QMessageBox.information`` ...) translate their argument.
* **Code keeps seeing English.**  The getters (``QAction.text()``, ``QMenu.title()``,
  ``QAbstractButton.text()``, ``QLabel.text()``, ``windowTitle()``, ``tabText()``,
  ``QTreeWidgetItem.text()`` ...) return the original English text of anything that was
  translated, so lookups such as ``a.text().replace("&", "") == "Tools"`` and tests that look
  for English action texts keep working in Arabic.  ``shown(obj)`` returns what is on screen.

Widgets that show the *user's* content are never translated: the form designer surface,
code editors, the mobile / game previews, and widgets (or their children) with the dynamic
property ``i18n_skip`` = True (``i18n_skip_items`` = True keeps only the items of a list /
tree untranslated, e.g. Properties, Toolbox, Locals).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from PyQt6.QtCore import QEvent, QLibraryInfo, QObject, Qt, QTimer, QTranslator

HERE = Path(__file__).resolve().parent
LANGUAGES: list[tuple[str, str]] = [("en", "English"), ("ar", "العربية")]
RTL_LANGUAGES = {"ar", "fa", "he", "ur"}
SETTING = "options/ui_language"

_lang = "en"
_strings: dict[str, str] = {}
_patterns: list[tuple[re.Pattern, str]] = []
_missing: set[str] = set()
_filter = None
_qt_translators: list[QTranslator] = []
_patched = False
_ORIG: dict[tuple[type, str], object] = {}

MAP_PROP = "i18n_map"                       # dynamic property: {shown text: English text}
ROLE_EN = int(Qt.ItemDataRole.UserRole) + 0x7A10     # item roles that keep the English text
ROLE_SHOWN = ROLE_EN + 64

# widget classes whose subtree shows the user's own content (never translated)
SKIP_CLASSES = {"Surface", "FormFrame", "Overlay", "ComponentTray", "TabControlPreview", "MobilePreview",
                "SceneCanvas", "MonacoEditor", "CodeEditor", "QsciScintilla"}
ITEM_SKIP_CLASSES = {"PropertiesPanel", "Toolbox", "MenuEditor", "CompletionPopup"}
# these stay left-to-right in a right-to-left IDE (code and the user's forms)
LTR_CLASSES = {"DesignerView", "CodeEditor", "MonacoEditor", "QsciScintilla", "QWebEngineView", "SceneCanvas",
               "TerminalWidget", "QPlainTextEdit", "MobilePreview", "Margin"}

_ARABIC = re.compile(r"[֐-ࣿיִ-﻿]")
_MNEMONIC = re.compile(r"&(?!&)(\w)")


# ===================================================================== catalog
def language() -> str:
    return _lang


def is_rtl(lang: str | None = None) -> bool:
    return (lang or _lang) in RTL_LANGUAGES


def catalog_path(lang: str) -> Path:
    return HERE / f"{lang}.json"


def available() -> list[tuple[str, str]]:
    return [(c, n) for c, n in LANGUAGES if c == "en" or catalog_path(c).exists()]


def _compile(pat: str) -> re.Pattern:
    parts = re.split(r"(\{\})", pat)
    rx = "".join("(.*?)" if p == "{}" else re.escape(p.replace("{{", "{").replace("}}", "}")) for p in parts)
    return re.compile("^" + rx + "$", re.S)


def load(lang: str) -> None:
    """Load the catalog of `lang` ("en" = no translation)."""
    global _lang, _strings, _patterns
    _strings, _patterns = {}, []
    _missing.clear()
    if lang != "en":
        try:
            data = json.loads(catalog_path(lang).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            lang, data = "en", {}
        _strings = {k: v for k, v in data.get("strings", {}).items() if v}
        pats = [(k, v) for k, v in data.get("patterns", {}).items() if v and "{}" in k]
        pats.sort(key=lambda kv: -len(kv[0].replace("{}", "")))      # most specific first
        _patterns = [(_compile(k), v) for k, v in pats]
    _lang = lang


def _fill(template: str, values: list[str]) -> str:
    t = template.replace("{{", "\x00").replace("}}", "\x01")       # literal braces of format strings
    if re.search(r"\{\d+\}", t):
        t = re.sub(r"\{(\d+)\}", lambda m: values[int(m.group(1))] if int(m.group(1)) < len(values) else "", t)
    else:
        it = iter(values)
        t = re.sub(r"\{\}", lambda m: next(it, ""), t)
    return t.replace("\x00", "{").replace("\x01", "}")


def _lookup(core: str, depth: int = 0) -> str | None:
    t = _strings.get(core)
    if t is not None:
        return t
    s = core.strip()
    if s != core and s:
        t = _lookup(s, depth)
        if t is not None:
            return core[:len(core) - len(core.lstrip())] + t + core[len(core.rstrip()):]
        return None
    if "  " in s:
        # labels spaced for layout ("NES  (cc65 / ca65)" in File > New Project) use the catalog's
        # single-spaced key ("NES (cc65 / ca65)")
        t = _lookup(re.sub(r" {2,}", " ", s), depth)
        if t is not None:
            return t
    for suf in ("...", "…", ":", " :", " *", "*", ".", "!"):
        if s.endswith(suf) and len(s) > len(suf):
            t = _strings.get(s[:-len(suf)])
            if t is not None:
                return t + (suf if suf != " :" else ":")
    for rx, template in _patterns:
        m = rx.match(s)
        if m:
            # the values may be translatable too ("Layout: VS Code", a status inside a description)
            # (single words are left alone: they are usually names - a project called "Data")
            vals = [(_lookup(v, depth + 1) if depth < 2 and " " in v.strip() else None) or v for v in m.groups()]
            return _fill(template, vals)
    return None


_MARKUP = re.compile(r"(<[^>]*>|&#?\w+;)")
_LATIN_TOKEN = re.compile(r"[^\s֐-ࣿיִ-﻿‎‏<>]+")
LRM = "‎"


def _bidi(text: str) -> str:
    """Keep Latin words with leading/trailing symbols (C#, C++, .NET, *.bas, @file:, (Ctrl+S)) in
    one piece inside right-to-left text: wrap them in LEFT-TO-RIGHT MARKs (outside HTML tags)."""
    if not _ARABIC.search(text):
        return text

    def fix(m):
        tok = m.group(0)
        core = tok.lstrip("([{\"'").rstrip(")]}\"',;")     # brackets / quotes belong to the sentence
        if not core or not re.search(r"[A-Za-z0-9]", core) or (core[0].isalnum() and core[-1].isalnum()):
            return tok
        i = tok.index(core)
        return tok[:i] + LRM + core + LRM + tok[i + len(core):]
    parts = _MARKUP.split(text)
    return "".join(p if i % 2 else _LATIN_TOKEN.sub(fix, p) for i, p in enumerate(parts))


def tr(text, menubar: bool = False):
    """Translate an English UI string into the current language (unchanged when not found)."""
    if _lang == "en" or not text or not isinstance(text, str) or _ARABIC.search(text):
        return text
    shortcut = ""
    if "\t" in text:
        text, _, sc = text.partition("\t")
        shortcut = "\t" + sc
    m = _MNEMONIC.search(text)
    core = _MNEMONIC.sub(r"\1", text).replace("&&", "&") if m else text.replace("&&", "&")
    out = _lookup(core)
    if out is None:
        if len(_missing) < 5000 and re.search(r"[A-Za-z]{2,}", core):
            _missing.add(core)
        return text + shortcut
    out = out.replace("&", "&&") if "&" in core and "&&" in text else out
    if _lang in RTL_LANGUAGES:
        out = _bidi(out)
    if m and menubar:
        out = f"{out} (&{m.group(1).upper()})"
    return out + shortcut


def missing() -> list[str]:
    """English texts seen on screen that the catalog does not translate (for translators)."""
    return sorted(_missing)


# ===================================================================== English kept for the code
def _map(obj) -> dict:
    try:
        m = QObject.property(obj, MAP_PROP)
    except Exception:  # noqa: BLE001
        return {}
    return m if isinstance(m, dict) else {}


def _remember(obj, shown: str, english: str) -> None:
    m = dict(_map(obj))
    m[shown] = english
    if len(m) > 64:                                    # labels with changing data: keep it small
        m = dict(list(m.items())[-48:])
    QObject.setProperty(obj, MAP_PROP, m)


def english(obj, shown: str) -> str:
    """The English source of `shown` (a text displayed by obj), or `shown` itself."""
    if not shown or not isinstance(shown, str):
        return shown
    return _map(obj).get(shown, shown)


def _orig(cls, name):
    return _ORIG.get((cls, name)) or getattr(cls, name)


def shown(obj, attr: str = "text") -> str:
    """What the user actually sees (the translated text), bypassing the English getters."""
    from PyQt6.QtGui import QAction
    from PyQt6.QtWidgets import QAbstractButton, QLabel, QMenu, QWidget
    for cls in (QAction, QAbstractButton, QLabel, QMenu, QWidget):
        if isinstance(obj, cls) and (cls, attr) in _ORIG:
            return _ORIG[(cls, attr)](obj)
    return getattr(obj, attr)()


def _skipped(w, items: bool = False) -> bool:
    """True when w (a QWidget) shows the user's content (designer, editors, previews)."""
    from PyQt6 import sip
    p, depth = w, 0
    while p is not None and depth < 40:
        if sip.isdeleted(p):
            return True
        name = type(p).__name__
        if name in SKIP_CLASSES or p.property("i18n_skip"):
            return True
        if items and (name in ITEM_SKIP_CLASSES or p.property("i18n_skip_items")):
            return True
        if name == "DesignerView" and p is not w:
            return True
        p = p.parentWidget()
        depth += 1
    return False


# ===================================================================== patches
def _patch_all() -> None:
    """Install the translating setters and English-returning getters (once)."""
    global _patched
    if _patched:
        return
    _patched = True
    from PyQt6.QtGui import QAction
    from PyQt6.QtWidgets import (QAbstractButton, QFileDialog, QGroupBox, QInputDialog, QLabel, QLineEdit,
                                 QListWidgetItem, QMenu, QMessageBox, QStatusBar, QTabBar, QTabWidget,
                                 QTableWidget, QTreeWidget, QTreeWidgetItem, QWidget)

    def keep(cls, name):
        _ORIG[(cls, name)] = getattr(cls, name)
        return _ORIG[(cls, name)]

    # ---- getters: return the English source of a translated text
    def getter(cls, name, holder=None):
        orig = keep(cls, name)

        def g(self, *a):
            v = orig(self, *a)
            if v and isinstance(v, str):
                h = holder(self) if holder else self
                m = _map(h) if h is not None else {}
                if m:
                    return m.get(v, v)
            return v
        setattr(cls, name, g)

    # ---- setters: translate the argument (only while a translation is active)
    def setter(cls, name, idx=0, holder=None, menubar=None, guard=None):
        orig = keep(cls, name)

        def s(self, *a):
            if _lang != "en" and len(a) > idx and isinstance(a[idx], str) and a[idx]:
                if guard is None or not guard(self):
                    en = a[idx]
                    t = tr(en, menubar=bool(menubar and menubar(self)))
                    if t != en:
                        _remember(holder(self) if holder else self, t, en)
                        a = a[:idx] + (t,) + a[idx + 1:]
            return orig(self, *a)
        setattr(cls, name, s)

    def is_menubar_action(a):
        try:
            return any(type(w).__name__ == "QMenuBar" for w in a.associatedObjects())
        except Exception:  # noqa: BLE001
            return False

    for n in ("text", "toolTip", "statusTip", "iconText"):
        getter(QAction, n)
    setter(QAction, "setText", menubar=is_menubar_action)
    for n in ("setToolTip", "setStatusTip", "setIconText"):
        setter(QAction, n)

    def menu_action(m):
        return m.menuAction()
    getter(QMenu, "title", holder=menu_action)
    orig_set_title = keep(QMenu, "setTitle")

    def set_title(self, title):
        if _lang != "en" and title:
            QAction.setText(self.menuAction(), title)          # translates + remembers
        else:
            orig_set_title(self, title)
    QMenu.setTitle = set_title

    w_guard = _skipped
    getter(QAbstractButton, "text")
    setter(QAbstractButton, "setText", guard=w_guard)
    getter(QLabel, "text")
    setter(QLabel, "setText", guard=w_guard)
    getter(QGroupBox, "title")
    setter(QGroupBox, "setTitle", guard=w_guard)
    getter(QLineEdit, "placeholderText")
    setter(QLineEdit, "setPlaceholderText", guard=w_guard)
    getter(QWidget, "windowTitle")
    setter(QWidget, "setWindowTitle", guard=w_guard)
    getter(QWidget, "toolTip")
    setter(QWidget, "setToolTip", guard=w_guard)
    setter(QStatusBar, "showMessage")

    # tabs: the English map lives on the QTabBar (QTabWidget forwards to it)
    def bar_of(tw):
        return tw.tabBar()
    getter(QTabBar, "tabText")
    getter(QTabBar, "tabToolTip")
    setter(QTabBar, "setTabText", idx=1, guard=w_guard)
    setter(QTabBar, "setTabToolTip", idx=1, guard=w_guard)
    getter(QTabWidget, "tabText", holder=bar_of)
    getter(QTabWidget, "tabToolTip", holder=bar_of)
    setter(QTabWidget, "setTabText", idx=1, holder=bar_of, guard=w_guard)
    setter(QTabWidget, "setTabToolTip", idx=1, holder=bar_of, guard=w_guard)
    for name in ("addTab", "insertTab"):
        orig_tab = keep(QTabWidget, name)

        def add(self, *a, _orig=orig_tab):
            if _lang != "en" and not _skipped(self):
                i = len(a) - 1
                if a and isinstance(a[i], str):
                    t = tr(a[i])
                    if t != a[i]:
                        _remember(self.tabBar(), t, a[i])
                        a = a[:i] + (t,) + a[i + 1:]
            return _orig(self, *a)
        setattr(QTabWidget, name, add)

    # header labels (display only)
    for cls, name in ((QTreeWidget, "setHeaderLabels"), (QTableWidget, "setHorizontalHeaderLabels")):
        orig_h = keep(cls, name)

        def hdr(self, labels, _orig=orig_h):
            if _lang != "en" and not _skipped(self):
                labels = [tr(x) if isinstance(x, str) else x for x in labels]
            return _orig(self, labels)
        setattr(cls, name, hdr)

    # list / tree items: English kept in an item role
    def item_text_getter(cls, has_col):
        orig = keep(cls, "text")

        def g(self, *a):
            v = orig(self, *a)
            if v:
                col = a[0] if has_col and a else 0
                try:
                    if self.data(col, ROLE_SHOWN) == v if has_col else self.data(ROLE_SHOWN) == v:
                        return self.data(col, ROLE_EN) if has_col else self.data(ROLE_EN)
                except Exception:  # noqa: BLE001
                    pass
            return v
        setattr(cls, "text", g)
    item_text_getter(QTreeWidgetItem, True)
    item_text_getter(QListWidgetItem, False)

    # static dialogs: translate titles / labels before Qt shows them
    def static(cls, name, idxs):
        orig = keep(cls, name)

        def f(*a, **kw):
            if _lang != "en":
                a = tuple(tr(x) if i in idxs and isinstance(x, str) else x for i, x in enumerate(a))
                for k in ("caption", "title", "text", "label"):
                    if isinstance(kw.get(k), str):
                        kw[k] = tr(kw[k])
            return orig(*a, **kw)
        setattr(cls, name, staticmethod(f))
    for n in ("information", "warning", "critical", "question", "about"):
        static(QMessageBox, n, {1, 2})
    for n in ("getText", "getItem", "getInt", "getDouble", "getMultiLineText"):
        static(QInputDialog, n, {1, 2})
    for n in ("getOpenFileName", "getSaveFileName", "getExistingDirectory", "getOpenFileNames"):
        static(QFileDialog, n, {1})


# ===================================================================== translating widgets
def _set_text(obj, cls, get_name, set_name, english_text: str, menubar=False, holder=None):
    """Show tr(english_text) on obj (or the English itself when no translation is active)."""
    orig_get = _orig(cls, get_name)
    orig_set = _orig(cls, set_name)
    cur = orig_get(obj)
    want = tr(english_text, menubar=menubar) if _lang != "en" else english_text
    if want != english_text:
        _remember(holder or obj, want, english_text)
    if cur != want:
        orig_set(obj, want)


def translate_action(a, menubar: bool | None = None) -> None:
    from PyQt6.QtGui import QAction
    from PyQt6 import sip
    if a is None or sip.isdeleted(a) or a.isSeparator():
        return
    try:
        if menubar is None:
            menubar = any(type(w).__name__ == "QMenuBar" for w in a.associatedObjects())
        en = QAction.text(a)                         # patched getter -> English
        if en:
            _set_text(a, QAction, "text", "setText", en, menubar=menubar)
        tip = QAction.toolTip(a)
        if tip and tip != en.replace("&", "") and _MNEMONIC.sub(r"\1", en) != tip:
            _set_text(a, QAction, "toolTip", "setToolTip", tip)
        st = QAction.statusTip(a)
        if st:
            _set_text(a, QAction, "statusTip", "setStatusTip", st)
    except RuntimeError:
        pass


def _items(w) -> None:
    """Translate list / tree items and headers of an item widget."""
    from PyQt6.QtWidgets import QListWidget, QTableWidget, QTreeWidget
    if isinstance(w, QTreeWidget):
        hi = w.headerItem()
        if hi is not None and not w.isHeaderHidden():
            for c in range(hi.columnCount()):
                _item_set(hi, c, True)
        if not _skipped(w, items=True):
            n, stack = 0, [w.topLevelItem(i) for i in range(w.topLevelItemCount())]
            blocked = w.blockSignals(True)
            try:
                while stack and n < 3000:
                    it = stack.pop()
                    if it is None:
                        continue
                    n += 1
                    for c in range(it.columnCount()):
                        _item_set(it, c, True)
                    stack.extend(it.child(i) for i in range(it.childCount()))
            finally:
                w.blockSignals(blocked)
    elif isinstance(w, QListWidget):
        if not _skipped(w, items=True):
            blocked = w.blockSignals(True)
            try:
                for i in range(min(w.count(), 2000)):
                    _item_set(w.item(i), 0, False)
            finally:
                w.blockSignals(blocked)
    elif isinstance(w, QTableWidget):
        for c in range(w.columnCount()):
            it = w.horizontalHeaderItem(c)
            if it is not None:
                _item_set(it, 0, False)


def _item_set(it, col: int, has_col: bool) -> None:
    from PyQt6.QtWidgets import QListWidgetItem, QTableWidgetItem, QTreeWidgetItem
    if it is None:
        return
    if has_col:
        cur = _ORIG.get((QTreeWidgetItem, "text"), QTreeWidgetItem.text)(it, col)
        en = it.data(col, ROLE_EN) if it.data(col, ROLE_SHOWN) == cur and cur else cur
    else:
        cur = it.text() if isinstance(it, QTableWidgetItem) else \
            _ORIG.get((QListWidgetItem, "text"), QListWidgetItem.text)(it)
        en = it.data(ROLE_EN) if it.data(ROLE_SHOWN) == cur and cur else cur
    if not en or not isinstance(en, str):
        return
    want = tr(en) if _lang != "en" else en
    if want == cur:
        return
    if has_col:
        it.setData(col, ROLE_EN, en)
        it.setData(col, ROLE_SHOWN, want)
        it.setText(col, want)
    else:
        it.setData(ROLE_EN, en)
        it.setData(ROLE_SHOWN, want)
        it.setText(want)


def translate_widget(w) -> None:
    """Translate one widget's own texts (not its children)."""
    from PyQt6 import sip
    from PyQt6.QtWidgets import (QAbstractButton, QAbstractItemView, QDockWidget, QGroupBox, QLabel, QLineEdit,
                                 QMenu, QMenuBar, QPlainTextEdit, QTabBar, QTabWidget, QTextEdit, QToolBar,
                                 QWidget)
    if w is None or sip.isdeleted(w) or not isinstance(w, QWidget):
        return
    try:
        if is_rtl() and type(w).__name__ in LTR_CLASSES and w.layoutDirection() != Qt.LayoutDirection.LeftToRight:
            w.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        if _skipped(w):
            return
        if isinstance(w, (QMenu, QMenuBar, QToolBar)):
            for a in w.actions():
                translate_action(a, menubar=True if isinstance(w, QMenuBar) else None)   # None: a menu-bar menu shown elsewhere keeps (&F)
            if isinstance(w, QMenu):
                translate_action(w.menuAction(), menubar=None)
        if w.isWindow() or isinstance(w, (QDockWidget, QToolBar)):
            t = QWidget.windowTitle(w)
            if t:
                _set_text(w, QWidget, "windowTitle", "setWindowTitle", t)
        tip = QWidget.toolTip(w)
        if tip:
            _set_text(w, QWidget, "toolTip", "setToolTip", tip)
        if isinstance(w, QAbstractButton):
            t = QAbstractButton.text(w)
            if t:
                _set_text(w, QAbstractButton, "text", "setText", t)
        elif isinstance(w, QLabel):
            t = QLabel.text(w)
            if t:
                _set_text(w, QLabel, "text", "setText", t)
        elif isinstance(w, QGroupBox):
            t = QGroupBox.title(w)
            if t:
                _set_text(w, QGroupBox, "title", "setTitle", t)
        elif isinstance(w, QLineEdit):
            t = QLineEdit.placeholderText(w)
            if t:
                _set_text(w, QLineEdit, "placeholderText", "setPlaceholderText", t)
        elif isinstance(w, (QPlainTextEdit, QTextEdit)):
            t = w.placeholderText()
            if t:
                en = english(w, t)
                want = tr(en)
                if want != en:
                    _remember(w, want, en)
                if want != t:
                    w.setPlaceholderText(want)
        elif isinstance(w, QTabBar):
            for i in range(w.count()):
                t = QTabBar.tabText(w, i)
                if t:
                    want = tr(t) if _lang != "en" else t
                    if want != t:
                        _remember(w, want, t)
                    if _ORIG.get((QTabBar, "tabText"), QTabBar.tabText)(w, i) != want:
                        _ORIG.get((QTabBar, "setTabText"), QTabBar.setTabText)(w, i, want)
                tt = QTabBar.tabToolTip(w, i)
                if tt:
                    want = tr(tt) if _lang != "en" else tt
                    if want != tt:
                        _remember(w, want, tt)
                    if _ORIG.get((QTabBar, "tabToolTip"), QTabBar.tabToolTip)(w, i) != want:
                        _ORIG.get((QTabBar, "setTabToolTip"), QTabBar.setTabToolTip)(w, i, want)
        elif isinstance(w, QTabWidget):
            translate_widget(w.tabBar())
        elif isinstance(w, QAbstractItemView):
            _items(w)
            _watch_rows(w)
    except RuntimeError:
        pass


def _watch_rows(w) -> None:
    """Translate items added later to a visible list / tree (once per widget)."""
    from PyQt6.QtWidgets import QListWidget, QTreeWidget
    if not isinstance(w, (QListWidget, QTreeWidget)) or w.property("i18n_rows"):
        return
    w.setProperty("i18n_rows", True)
    pending = {"on": False}

    def later(*_):
        if pending["on"] or _lang == "en":
            return
        pending["on"] = True

        def run():
            pending["on"] = False
            from PyQt6 import sip
            if not sip.isdeleted(w):
                _items(w)
        QTimer.singleShot(0, run)
    try:
        w.model().rowsInserted.connect(later)
        w.model().modelReset.connect(later)
    except (RuntimeError, AttributeError):
        pass


def translate_tree(root) -> None:
    """Translate a widget and all its children (and the actions they own)."""
    from PyQt6.QtGui import QAction
    from PyQt6.QtWidgets import QWidget
    if root is None:
        return
    translate_widget(root)
    for w in root.findChildren(QWidget):
        translate_widget(w)
    for a in root.findChildren(QAction):
        translate_action(a)


def translate_all(app=None) -> None:
    from PyQt6.QtWidgets import QApplication
    app = app or QApplication.instance()
    if app is None:
        return
    for w in app.topLevelWidgets():
        translate_tree(w)


class _Filter(QObject):
    """Translates widgets when they are shown and actions when they are added."""

    def eventFilter(self, obj, ev):  # noqa: N802 - Qt API
        try:
            t = ev.type()
            if t == QEvent.Type.Show:
                translate_widget(obj)
            elif t == QEvent.Type.ActionAdded:
                from PyQt6.QtWidgets import QMenuBar, QWidget
                if isinstance(obj, QWidget) and not _skipped(obj):
                    translate_action(ev.action(), menubar=True if isinstance(obj, QMenuBar) else None)
        except Exception:  # noqa: BLE001 - translation must never break the IDE
            pass
        return False


# ===================================================================== switching
QT_CONTEXTS = {"QPlatformTheme", "QDialogButtonBox", "QMessageBox", "QInputDialog", "QFileDialog", "QWizard",
               "QColorDialog", "QFontDialog", "QLineEdit", "QWidgetTextControl", "QShortcut"}


class _QtOverrides(QTranslator):
    """Qt's own texts (standard buttons OK / Cancel / Yes ..., line-edit menus) from our catalog first;
    whatever the catalog lacks falls through to Qt's qtbase_<lang>.qm."""

    def translate(self, context, source, disambiguation=None, n=-1):  # noqa: D401 - Qt API
        if _lang == "en" or context not in QT_CONTEXTS or not source:
            return None
        core = _MNEMONIC.sub(r"\1", source).replace("&&", "&").split("\t")[0]
        t = _strings.get(core)
        if t is None:
            return None
        return _bidi(t) + (("\t" + source.split("\t", 1)[1]) if "\t" in source else "")

    def isEmpty(self):  # noqa: N802 - Qt API
        return False


def _install_qt_translations(app, lang: str) -> None:
    for t in _qt_translators:
        app.removeTranslator(t)
    _qt_translators.clear()
    if lang == "en":
        return
    folder = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    for base in ("qtbase", "qt"):
        t = QTranslator(app)
        if t.load(f"{base}_{lang}", folder):
            app.installTranslator(t)
            _qt_translators.append(t)
            break
    ours = _QtOverrides(app)            # installed last = asked first
    app.installTranslator(ours)
    _qt_translators.append(ours)


def set_language(app, lang: str, translate_open: bool = True) -> str:
    """Switch the IDE to `lang` ("en", "ar") at run time.  Returns the language in effect."""
    global _filter
    if lang not in dict(LANGUAGES):
        lang = "en"
    if lang != "en":
        _patch_all()
    load(lang)
    lang = _lang
    _install_qt_translations(app, lang)
    # QLocale stays as it is: numbers keep Western digits (0-9) in spin boxes, the designer and code
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft if is_rtl(lang) else Qt.LayoutDirection.LeftToRight)
    if lang != "en" and _filter is None:
        _filter = _Filter(app)
        app.installEventFilter(_filter)
    elif lang == "en" and _filter is not None:
        app.removeEventFilter(_filter)
        _filter.deleteLater()
        _filter = None
    if translate_open:
        translate_all(app)        # also restores English (the maps remember every original text)
    return lang


def saved_language(settings) -> str:
    try:
        v = str(settings.value(SETTING, "en") or "en")
    except Exception:  # noqa: BLE001
        v = "en"
    return v if v in dict(LANGUAGES) else "en"


__all__ = ["tr", "set_language", "language", "is_rtl", "english", "shown", "translate_tree", "translate_all",
           "translate_widget", "translate_action", "available", "LANGUAGES", "SETTING", "saved_language", "missing"]
