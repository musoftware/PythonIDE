"""Tutorials ("الدروس"): the Arabic programming courses of radide/tutorials inside the IDE.

* Help > Tutorials (Ctrl+Shift+F1), a link on the Start Page and an Activity Bar entry (VS Code / Agent layouts)
  open the Tutorials dock: course list with progress + lesson viewer (QWebEngineView, Arabic typography,
  right-to-left text, left-to-right code highlighted with Pygments, Light/Dark following the IDE theme).
* Per block: "جرّبه" writes the block as a project under %LOCALAPPDATA%\\RADIDE\\tutorial-runs\\<course>\\<lesson>-<n>,
  opens it and runs it with the IDE's own run path (Ctrl+F5); C++ console programs get the lesson's
  ```text input as stdin (or what the learner types in a prompt).  "افتح في المحرر" opens it without running.
* Exercises are editable; "تحقق" runs the learner's code headless and compares it with the expected output /
  the hidden test of the solution (radide.tutorials.check).  Solutions stay hidden until clicked.  Quizzes give
  instant feedback.  Progress (lessons done, quizzes, exercises passed, code drafts) lives in QSettings.
* Help > Help Files (CHM) opens docs/chm/*.chm (tools/build_chm.py) with hh.exe: BASIC, C++, every other course
  whose CHM is built (radide.tutorials.chm_file()), the manual.
"""
from __future__ import annotations

import html as _html
import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import parse_qs

from PyQt6.QtCore import QObject, QSettings, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QIcon, QKeySequence, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (QDockWidget, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMessageBox, QSplitter,
                             QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import tutorials as T

try:
    from PyQt6.QtWebEngineCore import QWebEnginePage
    from PyQt6.QtWebEngineWidgets import QWebEngineView
except ImportError:  # pragma: no cover - the IDE normally has PyQt6-WebEngine
    QWebEnginePage = QWebEngineView = None

REPO = Path(__file__).resolve().parents[2]
WEB_DIR = REPO / "radide" / "web"
CHM_DIR = REPO / "docs" / "chm"
CHM_FILES = (("RADIDE_BASIC_ar.chm", "BASIC course (Arabic, CHM)"),
             ("RADIDE_CPP_ar.chm", "C++ course (Arabic, CHM)"),
             ("RADIDE_Manual.chm", "RAD IDE Manual (CHM)"))


def chm_files() -> list[tuple[str, str]]:
    """CHM_FILES + one entry per other course whose CHM is built (tools/build_chm.py), the manual last."""
    out = list(CHM_FILES[:2])
    known = {f for f, _t in CHM_FILES}
    for c in T.courses():
        f = T.chm_file(c.id)
        if f not in known and (CHM_DIR / f).is_file():
            out.append((f, f"{c.title_en} (Arabic, CHM)"))
            known.add(f)
    return out + list(CHM_FILES[2:])


def course_label(c, done: int, en: bool) -> str:
    """The course row of the Tutorials tree.  The tree is right-to-left: an English title is followed by a
    left-to-right mark so that "(3/24)" stays after it ("Title (3/24)", not "(3/24) Title" or "Title (24/3)")."""
    if en:
        return f"{c.title_en}‎  ({done}/{len(c.lessons)})‎"
    return f"{c.title_ar}  ({done}/{len(c.lessons)})"


KEY = "tutorials/"
SHORTCUT = "Ctrl+Shift+F1"
ROLE_REF = int(Qt.ItemDataRole.UserRole) + 1


# ===================================================================== progress (QSettings)
class Progress(QObject):
    changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._data = None

    def _settings(self) -> QSettings:
        return QSettings()

    @property
    def data(self) -> dict:
        if self._data is None:
            try:
                self._data = json.loads(self._settings().value(KEY + "progress", "{}") or "{}")
            except (TypeError, ValueError):
                self._data = {}
        return self._data

    def course(self, cid: str) -> dict:
        c = self.data.setdefault(cid, {})
        for k, v in (("done", []), ("quiz", {}), ("passed", []), ("last", "")):
            c.setdefault(k, v if not isinstance(v, (list, dict)) else type(v)())
        return c

    def save(self) -> None:
        self._settings().setValue(KEY + "progress", json.dumps(self.data, ensure_ascii=False))
        self.changed.emit()

    def reload(self) -> None:
        self._data = None

    def is_done(self, cid, lid) -> bool:
        return lid in self.course(cid)["done"]

    def set_done(self, cid, lid, on=True) -> None:
        done = self.course(cid)["done"]
        if on and lid not in done:
            done.append(lid)
        elif not on and lid in done:
            done.remove(lid)
        self.save()

    def count(self, c: T.Course) -> int:
        ids = {x.id for x in c.lessons}
        return len([x for x in self.course(c.id)["done"] if x in ids])

    def set_last(self, cid, lid) -> None:
        self.course(cid)["last"] = lid
        self.data["_last_course"] = cid
        self.save()

    def quiz(self, cid, lid) -> dict:
        return {int(k.split("#")[1]): v for k, v in self.course(cid)["quiz"].items() if k.split("#")[0] == lid}

    def set_quiz(self, cid, lid, n, choice, ok) -> None:
        self.course(cid)["quiz"][f"{lid}#{n}"] = [int(choice), bool(ok)]
        self.save()

    def set_passed(self, cid, lid, n) -> None:
        p = self.course(cid)["passed"]
        if f"{lid}#{n}" not in p:
            p.append(f"{lid}#{n}")
        self.save()

    def passed(self, cid, lid) -> set[int]:
        return {int(x.split("#")[1]) for x in self.course(cid)["passed"] if x.split("#")[0] == lid}

    # code drafts of the exercises
    def code(self, cid, lid, n) -> str | None:
        v = self._settings().value(f"{KEY}code/{cid}/{lid}/{n}")
        return v if isinstance(v, str) else None

    def set_code(self, cid, lid, n, text: str | None) -> None:
        s = self._settings()
        if text is None:
            s.remove(f"{KEY}code/{cid}/{lid}/{n}")
        else:
            s.setValue(f"{KEY}code/{cid}/{lid}/{n}", text)


PROGRESS = Progress()


# ===================================================================== helpers
def _lang() -> str:
    try:
        from .. import i18n
        return i18n.language()
    except Exception:  # noqa: BLE001
        return "en"


def _dark() -> bool:
    try:
        from .. import theme
        return theme.is_dark()
    except Exception:  # noqa: BLE001
        return False


def book_icon(color: str | None = None, size: int = 24) -> QIcon:
    """An open book (drawn, so it follows the theme like the Activity Bar icons)."""
    if color is None:
        try:
            from .. import theme
            color = theme.color("text")
        except Exception:  # noqa: BLE001
            color = "#444444"
    pm = QPixmap(size * 2, size * 2)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size * 2 / 24.0, size * 2 / 24.0)
    pen = QPen(QColor(color), 1.6)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    from PyQt6.QtGui import QPainterPath
    path = QPainterPath()
    path.moveTo(12, 6.5)
    path.cubicTo(9.5, 4.8, 6, 4.6, 3, 5.2)
    path.lineTo(3, 18.6)
    path.cubicTo(6, 18, 9.5, 18.3, 12, 20)
    path.cubicTo(14.5, 18.3, 18, 18, 21, 18.6)
    path.lineTo(21, 5.2)
    path.cubicTo(18, 4.6, 14.5, 4.8, 12, 6.5)
    path.lineTo(12, 20)
    p.drawPath(path)
    p.end()
    return QIcon(pm)


def open_chm(win, name: str) -> bool:
    """Open docs/chm/<name> with hh.exe (the Windows HTML Help viewer)."""
    path = CHM_DIR / name
    if not path.exists():
        QMessageBox.information(win, "Tutorials",
                                f"{name} is not built yet.\nRun:  python tools\\build_chm.py\n\n({path})")
        return False
    if os.environ.get("RADIDE_NO_BROWSER"):
        open_chm.last = str(path)
        return True
    hh = Path(os.environ.get("WINDIR", r"C:\Windows")) / "hh.exe"
    try:
        subprocess.Popen([str(hh) if hh.exists() else "hh.exe", str(path)])
    except OSError:
        os.startfile(str(path))  # noqa: S606 - a local help file
    open_chm.last = str(path)
    return True


open_chm.last = ""


class _Signals(QObject):
    checked = pyqtSignal(object, object)       # (key, CheckResult | Exception)


# ===================================================================== web page
if QWebEnginePage is not None:
    class _Page(QWebEnginePage):
        action = pyqtSignal(str, dict)

        def acceptNavigationRequest(self, url, nav_type, is_main):  # noqa: N802 - Qt override
            if url.host() == "radtut.action":
                q = {k: v[0] for k, v in parse_qs(url.query()).items()}
                self.action.emit(url.path().strip("/"), q)
                return False
            if url.scheme() in ("http", "https") and \
                    nav_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
                from PyQt6.QtGui import QDesktopServices
                QDesktopServices.openUrl(url)
                return False
            return super().acceptNavigationRequest(url, nav_type, is_main)

        def javaScriptConsoleMessage(self, level, message, line, source):  # noqa: N802
            if level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
                print(f"[tutorials] js: {message} ({line})", file=sys.stderr)
else:  # pragma: no cover
    _Page = None


# ===================================================================== the panel
class TutorialsPanel(QWidget):
    """Course list (left) + lesson viewer (right)."""

    lessonShown = pyqtSignal(str, str)          # course id, lesson id (tests wait for it)
    checkDone = pyqtSignal(int, bool)           # block index, ok

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.setObjectName("TutorialsPanel")
        self.courses = T.courses()
        self.lesson: T.Lesson | None = None
        self.blocks: dict[int, T.Block] = {}
        self.loaded = False
        self.last_check: T.CheckResult | None = None
        self.last_run: dict = {}
        self._sig = _Signals()
        self._sig.checked.connect(self._on_checked)
        self.font_size = int(QSettings().value(KEY + "font_size", 17) or 17)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        bar = QWidget()
        bar.setObjectName("tutBar")
        h = QHBoxLayout(bar)
        h.setContentsMargins(4, 3, 4, 3)
        h.setSpacing(3)

        def tb(text, tip, slot, check=False):
            b = QToolButton()
            b.setText(text)
            b.setToolTip(tip)
            b.setAutoRaise(True)
            b.setCheckable(check)
            b.clicked.connect(slot)
            h.addWidget(b)
            return b
        self.b_list = tb("☰", "Show / hide the course list", self._toggle_list, True)
        self.b_list.setChecked(True)
        self.b_prev = tb("Previous", "Previous lesson", lambda: self.step(-1))
        self.b_next = tb("Next", "Next lesson (marks this one as done)", lambda: self.step(1))
        self.b_done = tb("Lesson done", "Mark this lesson as done / not done", self._toggle_done, True)
        self.title = QLabel()
        self.title.setProperty("i18n_skip", True)
        self.title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        h.addWidget(self.title, 1)
        tb("A-", "Smaller text", lambda: self.zoom(-1))
        tb("A+", "Larger text", lambda: self.zoom(1))
        lay.addWidget(bar)

        self.split = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(2)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search the lessons...")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(lambda _t: self._search_timer.start(250))
        self.search.returnPressed.connect(self._do_search)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._do_search)
        lv.addWidget(self.search)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setColumnCount(1)
        self.tree.setProperty("i18n_skip_items", True)
        self.tree.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        # long course titles (English ones reach 60 characters) are elided inside the column instead of being
        # cut at its edge or pushing a horizontal scroll bar; every item has its full text as a tooltip
        self.tree.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tree.header().setStretchLastSection(True)
        self.tree.header().setSectionResizeMode(0, self.tree.header().ResizeMode.Stretch)
        self.tree.itemActivated.connect(self._on_item)
        self.tree.itemClicked.connect(self._on_item)
        lv.addWidget(self.tree, 1)
        self.split.addWidget(left)
        if QWebEngineView is not None:
            self.view = QWebEngineView()
            self.page = _Page(self.view)
            self.view.setPage(self.page)
            self.page.action.connect(self._on_action)
            self.view.loadFinished.connect(self._on_loaded)
        else:  # pragma: no cover
            self.view = QLabel("PyQt6-WebEngine is needed for the lesson viewer.")
            self.page = None
        self.split.addWidget(self.view)
        self.split.setStretchFactor(0, 0)
        self.split.setStretchFactor(1, 1)
        left.setMinimumWidth(150)
        self.split.setSizes(self._split_sizes())
        self.split.splitterMoved.connect(self._save_split)
        lay.addWidget(self.split, 1)
        PROGRESS.changed.connect(self.fill_tree)
        try:
            from .. import theme
            theme.changed.connect(self._on_theme)
        except Exception:  # noqa: BLE001
            pass
        self.fill_tree()

    def showEvent(self, e):  # noqa: N802 - Qt override: the UI language may have changed meanwhile
        super().showEvent(e)
        if getattr(self, "_tree_lang", None) != _lang():
            self.fill_tree()

    # ------------------------------------------------------------ list
    LIST_WIDTH = 300            # default width of the course list (was 210: course titles were cut)

    def _split_sizes(self) -> list[int]:
        try:
            w = int(QSettings().value(KEY + "list_width", self.LIST_WIDTH) or self.LIST_WIDTH)
        except (TypeError, ValueError):
            w = self.LIST_WIDTH
        return [max(150, min(600, w)), 760]

    def _save_split(self, *_a):
        w = self.split.sizes()[0] if self.split.count() else 0
        if w >= 150:
            QSettings().setValue(KEY + "list_width", int(w))

    def _toggle_list(self):
        self.split.widget(0).setVisible(self.b_list.isChecked())

    def fill_tree(self):
        if self.search.text().strip():
            return self._do_search()
        self.tree.clear()
        self._tree_lang = _lang()
        en = self._tree_lang == "en"
        for c in self.courses:
            done = PROGRESS.count(c)
            top = QTreeWidgetItem([course_label(c, done, en)])
            top.setToolTip(0, f"{c.title_ar}\n{c.title_en}\n{done}/{len(c.lessons)} · "
                              f"{int(100 * done / max(1, len(c.lessons)))}%")
            top.setData(0, ROLE_REF, ("course", c.id))
            f = top.font(0)
            f.setBold(True)
            top.setFont(0, f)
            self.tree.addTopLevelItem(top)
            for les in c.lessons:
                mark = "✓ " if PROGRESS.is_done(c.id, les.id) else "    "
                it = QTreeWidgetItem([f"{mark}{les.number}. {les.title_ar}"])
                it.setToolTip(0, f"{les.title_ar} ({les.minutes} min)")
                it.setData(0, ROLE_REF, ("lesson", c.id, les.id))
                if self.lesson is not None and self.lesson.course.id == c.id and self.lesson.id == les.id:
                    f2 = it.font(0)
                    f2.setBold(True)
                    it.setFont(0, f2)
                top.addChild(it)
            top.setExpanded(self.lesson is None or self.lesson.course.id == c.id)

    def _do_search(self):
        q = self.search.text().strip()
        if not q:
            return self.fill_tree()
        self.tree.clear()
        hits = T.search(q)
        top = QTreeWidgetItem([f"{len(hits)} ✱ {q}"])
        self.tree.addTopLevelItem(top)
        for c, les, snippet in hits:
            it = QTreeWidgetItem([f"{les.title_ar}  ·  {c.title_ar.split(' ')[0]} {les.number}"])
            it.setToolTip(0, f"{les.title_ar}\n{c.title_ar}\n\n{snippet}")
            it.setData(0, ROLE_REF, ("lesson", c.id, les.id, q))
            top.addChild(it)
        top.setExpanded(True)

    def _on_item(self, item, _col=0):
        ref = item.data(0, ROLE_REF)
        if not ref:
            return
        if ref[0] == "lesson":
            self.show_lesson(ref[1], ref[2], find=ref[3] if len(ref) > 3 else "")
        elif ref[0] == "course":
            c = self._course(ref[1])
            if c and c.lessons and self.lesson is None:
                last = PROGRESS.course(c.id).get("last") or c.lessons[0].id
                self.show_lesson(c.id, last)

    # ------------------------------------------------------------ lesson
    def _course(self, cid) -> T.Course | None:
        return next((c for c in self.courses if c.id == cid), None)

    def show_lesson(self, cid: str, lid: str, find: str = "") -> bool:
        c = self._course(cid)
        les = c.lesson(lid) if c else None
        if les is None:
            return False
        self.lesson = les
        self._find = find
        items = les.items()
        self.blocks = {b.index: b for k, b in items if k == "block"}
        saved = {}
        for n, b in self.blocks.items():
            if b.role == "exercise":
                s = PROGRESS.code(cid, lid, n)
                if s is not None:
                    saved[n] = s
        html = T_html().lesson_page(les, dark=_dark(), saved=saved, size=self.font_size, nav=self._nav_html())
        self.loaded = False
        if self.page is not None:
            self.view.setHtml(html, QUrl.fromLocalFile(str(WEB_DIR) + "/"))
        self.title.setText(f"{les.number}. {les.title_ar}")
        self.b_done.setChecked(PROGRESS.is_done(cid, lid))
        idx = c.lessons.index(les)
        self.b_prev.setEnabled(idx > 0)
        self.b_next.setEnabled(idx < len(c.lessons) - 1)
        PROGRESS.set_last(cid, lid)
        return True

    def _nav_html(self) -> str:
        les = self.lesson
        if les is None:
            return ""
        c = les.course
        i = c.lessons.index(les)
        prev = c.lessons[i - 1] if i > 0 else None
        nxt = c.lessons[i + 1] if i + 1 < len(c.lessons) else None
        p = (f'<a class="btn sec" href="javascript:void(0)" onclick="radAct(\'prev\',0)">→ {_html.escape(prev.title_ar)}</a>'
             if prev else "<span></span>")
        n = (f'<a class="btn" href="javascript:void(0)" onclick="radAct(\'next\',0)">{_html.escape(nxt.title_ar)} ←</a>'
             if nxt else "<span>🎉 نهاية الدورة</span>")
        return f'<div class="navfoot">{p}{n}</div>'

    def _on_loaded(self, ok: bool):
        self.loaded = True
        les = self.lesson
        if les is None or self.page is None:
            return
        for n, (choice, _ok) in PROGRESS.quiz(les.course.id, les.id).items():
            self.page.runJavaScript(f"radQuiz({n},{int(choice)},true)")
        for n in PROGRESS.passed(les.course.id, les.id):
            self.page.runJavaScript(f"radResult({n},'ok','<span class=head>✓ حللت هذا التمرين من قبل</span>')")
        if self._find:
            self.view.findText(self._find)
        self.lessonShown.emit(les.course.id, les.id)

    def step(self, delta: int):
        les = self.lesson
        if les is None:
            if self.courses:
                c = self.courses[0]
                self.show_lesson(c.id, PROGRESS.course(c.id).get("last") or c.lessons[0].id)
            return
        c = les.course
        i = c.lessons.index(les) + delta
        if 0 <= i < len(c.lessons):
            if delta > 0:
                PROGRESS.set_done(c.id, les.id, True)
            self.show_lesson(c.id, c.lessons[i].id)

    def _toggle_done(self):
        if self.lesson is not None:
            PROGRESS.set_done(self.lesson.course.id, self.lesson.id, self.b_done.isChecked())

    def zoom(self, delta: int):
        self.font_size = max(12, min(28, self.font_size + delta))
        QSettings().setValue(KEY + "font_size", self.font_size)
        if self.lesson is not None:
            self.show_lesson(self.lesson.course.id, self.lesson.id)

    def _on_theme(self, _name=""):
        if self.page is not None:
            self.page.runJavaScript(f"radTheme({'true' if _dark() else 'false'})")

    def open_last(self):
        if self.lesson is not None:
            return
        cid = PROGRESS.data.get("_last_course") or (self.courses[0].id if self.courses else "")
        c = self._course(cid)
        if c and c.lessons:
            self.show_lesson(c.id, PROGRESS.course(c.id).get("last") or c.lessons[0].id)

    # ------------------------------------------------------------ actions from the page
    def _on_action(self, verb: str, q: dict):
        try:
            n = int(q.get("b", "0"))
        except ValueError:
            n = 0
        if verb == "prev":
            return self.step(-1)
        if verb == "next":
            return self.step(1)
        b = self.blocks.get(n)
        if b is None or self.lesson is None:
            return
        if verb == "quiz":
            PROGRESS.set_quiz(self.lesson.course.id, self.lesson.id, n, int(q.get("c", 0)), q.get("ok") == "1")
        elif verb == "try":
            self.try_block(n)
        elif verb == "open":
            if b.role == "exercise":
                self.page.runJavaScript(f"radCode({n})", lambda code, n=n: self.open_block(n, code, run=False))
            else:
                self.open_block(n, None, run=False)
        elif verb == "check":
            self.page.runJavaScript(f"radCode({n})", lambda code, n=n: self.check_block(n, code))
        elif verb == "reset":
            PROGRESS.set_code(self.lesson.course.id, self.lesson.id, n, None)
            self.page.runJavaScript(f"radSetCode({n}, {json.dumps(b.code.rstrip(), ensure_ascii=False)});"
                                    f"radResult({n}, '', '')")

    def try_block(self, n: int) -> bool:
        return self.open_block(n, None, run=True)

    def open_block(self, n: int, code: str | None, run: bool) -> bool:
        """Write block *n* (or the learner's *code*) as a project, open it in the IDE and (optionally) run it."""
        les, b = self.lesson, self.blocks.get(n)
        if les is None or b is None:
            return False
        win = self.win
        if code is not None and b.role == "exercise":
            PROGRESS.set_code(les.course.id, les.id, n, code)
        stdin = None
        notebook = b.lang == "py" and "notebook" in b.info.split()
        if run and ((b.lang == "cpp" and not b.gui) or (b.lang == "ring" and not b.form)
                    or (b.lang == "py" and not b.form and not notebook)
                    or (b.lang in ("cs", "java") and not b.gui)
                    or (b.lang == "php" and "web" not in b.info.lower().split())
                    or (b.lang in getattr(T, "SCRIPT", ()) and not b.form)
                    or (b.lang in getattr(T, "JSL", ()) and not b.form)
                    or (b.lang in getattr(T, "NATIVE", ()) and not b.gui)
                    or (b.lang == "asm" and not b.gui)):
            stdin = b.check_target().stdin if b.role != "plain" else None
            if stdin is None and b.reads_stdin():
                text, ok = QInputDialog.getMultiLineText(
                    self, "المدخلات", "هذا البرنامج يقرأ من لوحة المفاتيح.\nاكتب ما تريد إدخاله (كل قيمة في سطر):", "")
                if not ok:
                    return False
                stdin = text + ("\n" if text and not text.endswith("\n") else "")
        folder = T.run_folder(les.course.id, les.id, n)
        same = win.project is not None and Path(win.project.folder).resolve() == folder.resolve()
        if same and b.role == "exercise" and not run:
            win.raise_()                           # the learner is already editing this exercise
            return True
        if win.project is not None and not win._confirm_close_project():
            return False
        try:
            if win.session is not None and win.session.running():
                win.stop_project()
            T.make_project(b, folder, code)
        except Exception as e:  # noqa: BLE001
            win.log(f"[Tutorials] cannot create the project: {e}")
            return False
        win.open_project(folder, ask=False)
        if win.project is None or Path(win.project.folder).resolve() != folder.resolve():
            return False                           # the user cancelled "Save changes?"
        self.last_run = {"folder": str(folder), "block": n, "stdin": stdin, "run": run}
        win.log(f"[Tutorials] {les.course.id} / {les.id} block {n} -> {folder}")
        if notebook and (folder / "notebook.ipynb").exists():     # Python notebook cells: the notebook editor
            view = win.open_any_file(str(folder / "notebook.ipynb"))
            if run and view is not None and hasattr(view, "run_all"):
                def go(tries=40):
                    if tries <= 0 or getattr(view, "is_ready", lambda: True)():
                        view.run_all()
                    else:
                        QTimer.singleShot(250, lambda: go(tries - 1))
                QTimer.singleShot(300, go)
            return True
        if run:
            QTimer.singleShot(150, lambda: self._run(stdin))
        return True

    def _run(self, stdin: str | None):
        win = self.win
        win.run_project(debug=False)
        s = win.session
        if stdin is not None and isinstance(getattr(s, "steps", None), list):
            # a chained session (foreign projects: build step(s), then the program - C# .csproj, Java ...):
            # the input belongs to the program, i.e. the last step, not to the build
            self._send_stdin_when_last(s, stdin, 600)
            return
        proc = getattr(s, "proc", None)
        if proc is not None and stdin is not None:
            proc.write(stdin.encode("utf-8"))
            proc.closeWriteChannel()
            win.log("[Tutorials] input sent to the program:\n" + stdin.rstrip())

    def _send_stdin_when_last(self, s, stdin: str, tries: int):
        if self.win.session is not s or tries <= 0 or not s.running():
            return
        proc = getattr(s, "proc", None)
        if not s.steps and proc is not None and proc.state() == proc.ProcessState.Running:
            proc.write(stdin.encode("utf-8"))
            proc.closeWriteChannel()
            self.win.log("[Tutorials] input sent to the program:\n" + stdin.rstrip())
            return
        QTimer.singleShot(200, lambda: self._send_stdin_when_last(s, stdin, tries - 1))

    def check_block(self, n: int, code: str | None):
        les, b = self.lesson, self.blocks.get(n)
        if les is None or b is None:
            return
        if code is not None:
            PROGRESS.set_code(les.course.id, les.id, n, code)
        folder = T.run_folder(les.course.id, les.id, n)
        use_folder = None
        p = self.win.project
        if p is not None and Path(p.folder).resolve() == folder.resolve():
            self.win.save_all()                    # the learner edits the opened project: check those files
            use_folder = folder
        self.page.runJavaScript(f"radResult({n}, 'busy', 'جارٍ التشغيل والمقارنة...')")
        work = T.runs_root() / "_check" / f"{les.course.id}-{les.id}-{n}"
        key = (les.course.id, les.id, n)

        def job():
            try:
                r = T.check(b, code, use_folder, work)
            except Exception as e:  # noqa: BLE001
                r = e
            self._sig.checked.emit(key, r)
        threading.Thread(target=job, daemon=True).start()

    def _on_checked(self, key, r):
        cid, lid, n = key
        if isinstance(r, Exception):
            r = T.CheckResult(False, "", None, [f"خطأ داخلي: {r}"])
        self.last_check = r
        if r.ok:
            PROGRESS.set_passed(cid, lid, n)
        if self.lesson is None or (self.lesson.course.id, self.lesson.id) != (cid, lid):
            self.checkDone.emit(n, r.ok)
            return
        esc = _html.escape
        head = ("✓ أحسنت! الناتج مطابق للمطلوب." if r.ok and r.expected is not None else
                "✓ " + (r.note or "أحسنت!") if r.ok else "✗ لم يتحقق المطلوب بعد.")
        parts = [f'<div class="head">{esc(head)}</div>']
        for p in r.problems:
            parts.append(f"<div>• {esc(p)}</div>")
        if not r.ok and r.expected is not None:
            parts.append(f'<div>المطلوب:</div><pre class="out">{esc(r.expected.rstrip())}</pre>')
        if r.output.strip() and (not r.ok or r.expected is None):
            parts.append(f'<div>ناتج برنامجك:</div><pre class="out">{esc(r.output.rstrip()[-3000:])}</pre>')
        self.page.runJavaScript(f"radResult({n}, {json.dumps('ok' if r.ok else 'bad')}, "
                                f"{json.dumps(''.join(parts), ensure_ascii=False)})")
        self.checkDone.emit(n, r.ok)


def T_html():
    from ..tutorials import html as th
    return th


# ===================================================================== install
def show_tutorials(win, course_id: str | None = None, lesson_id: str | None = None):
    dock = ensure_dock(win)
    dock.show()
    dock.raise_()
    fit_dock(win, dock)
    QTimer.singleShot(0, lambda: fit_dock(win, dock))
    panel = win.tutorials
    if course_id:
        c = panel._course(course_id)
        if c and c.lessons:
            panel.show_lesson(course_id, lesson_id or PROGRESS.course(course_id).get("last") or c.lessons[0].id)
    else:
        panel.open_last()
    return panel


def fit_dock(win, dock) -> None:
    """Keep the lesson readable: when the dock was squeezed into a stack of other docks (e.g. by a layout
    switch) it gets its own full-height column again; the first time it is shown it gets half the window."""
    if dock.isFloating() or not dock.isVisible():
        return
    try:
        area = win.dockWidgetArea(dock)
        stacked = any(d is not dock and d.isVisible() and not d.isFloating() and win.dockWidgetArea(d) == area
                      and abs(d.x() - dock.x()) < 30 and not win.tabifiedDockWidgets(dock).count(d)
                      for d in win.findChildren(QDockWidget))
        if stacked and area in (Qt.DockWidgetArea.RightDockWidgetArea, Qt.DockWidgetArea.LeftDockWidgetArea):
            win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock, Qt.Orientation.Horizontal)
            dock._rad_sized = False
        if not getattr(dock, "_rad_sized", False):
            dock._rad_sized = True
            want = max(700, int(win.width() * 0.5))
            if dock.width() < want - 40:
                win.resizeDocks([dock], [want], Qt.Orientation.Horizontal)
    except Exception:  # noqa: BLE001 - layout cosmetics only
        pass


def ensure_dock(win) -> QDockWidget:
    dock = getattr(win, "dock_tutorials", None)
    if dock is not None:
        return dock
    panel = TutorialsPanel(win)
    dock = QDockWidget("Tutorials", win)
    dock.setObjectName("dock_tutorials")
    dock.setWidget(panel)
    # its own full-height column of the right dock area, wide enough to read next to the editor
    win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock, Qt.Orientation.Horizontal)
    win.tutorials = panel
    win.dock_tutorials = dock
    return dock


def _start_page_links(win) -> None:
    try:
        from ..app import StartPage
    except Exception:  # noqa: BLE001
        return
    for i in range(win.tabs.count()):
        page = win.tabs.widget(i)
        if isinstance(page, StartPage) and not getattr(page, "_rad_tutorials", False) and hasattr(page, "add_section"):
            sec = page.add_section("Learn Programming")
            # English source text only: i18n.tr() leaves any text that already contains Arabic untranslated
            page.add_link(sec, "Arabic lessons: BASIC and C++...", lambda: show_tutorials(win),
                          f"Help > Tutorials ({SHORTCUT})")
            for c in T.courses():
                page.add_link(sec, c.title_en, lambda _=False, cid=c.id: show_tutorials(win, cid), c.title_ar)
            page._rad_tutorials = True


def install(win) -> None:
    win.show_tutorials = lambda course_id=None, lesson_id=None: show_tutorials(win, course_id, lesson_id)
    help_menu = next((a.menu() for a in win.menuBar().actions() if a.menu() is not None
                      and a.text().replace("&", "") == "Help"), None)
    if help_menu is None:
        help_menu = win.menuBar().addMenu("&Help")
    act = QAction("&Tutorials (Arabic lessons)...", win)
    act.setShortcut(QKeySequence(SHORTCUT))
    act.setIcon(book_icon())
    act.setToolTip("Arabic programming courses: BASIC and C++")
    act.triggered.connect(lambda: show_tutorials(win))
    from PyQt6.QtWidgets import QMenu
    sub_acts = []
    acts = help_menu.actions()
    before = acts[2] if len(acts) > 2 else None        # after RAD IDE Help / Context Help
    help_menu.insertAction(before, act)
    chm_menu = QMenu("Help Files (CHM)", help_menu)
    help_menu.insertMenu(before, chm_menu)
    win.tutorials_chm_menu = chm_menu

    def fill_chm_menu():
        chm_menu.clear()
        sub_acts.clear()
        for fname, title in chm_files():
            a = QAction(title, win)
            a.triggered.connect(lambda _=False, f=fname: open_chm(win, f))
            chm_menu.addAction(a)
            sub_acts.append(a)
    fill_chm_menu()
    chm_menu.aboutToShow.connect(fill_chm_menu)          # CHMs built while the IDE runs show up too
    win.a_tutorials = act
    win.a_tutorials_chm = sub_acts
    win.addAction(act)
    try:
        _start_page_links(win)
        win.tabs.currentChanged.connect(lambda _i: _start_page_links(win))
    except Exception as e:  # noqa: BLE001
        win.log(f"[Tutorials] start page: {e}")
    try:
        from . import workbench
        workbench.register_view("tutorials", "Tutorials", icon=book_icon(), action=lambda w: show_tutorials(w),
                                modes=("vscode", "agent"), area="side", order=96,
                                tooltip=f"Tutorials - Arabic programming lessons ({SHORTCUT})")
    except Exception as e:  # noqa: BLE001
        win.log(f"[Tutorials] activity bar: {e}")


__all__ = ["PROGRESS", "TutorialsPanel", "book_icon", "chm_files", "ensure_dock", "install", "open_chm",
           "show_tutorials"]
