"""Assembly Checks window: "Check by running", "Explain this line" and the What-if console (IDE side of
radide/asm_sim).

* **Debug > Assembly Checks > Check by Running** (Ctrl+Shift+F5): runs the current assembly file in a sandboxed
  emulator (Unicorn for NASM x86 / x64, the IDE's 8086 emulator for 16-bit DOS code) with the input typed in the
  window, and shows every runtime mistake - stack not balanced at ``ret``, null / invalid memory access, divide
  error, endless loop, write past the end of a buffer, uninitialised stack read, misaligned / shadow-space-less
  call, changed callee-saved register - as editor markers (rule ids ``sim.*``), Error List rows and a Findings
  list with the bilingual "what happened / how to fix / reference" text.
* **Check This Procedure** runs only the procedure under the cursor (register values from the Registers box),
  **Check Selection** only the selected lines.
* **Explain This Line** (Ctrl+Shift+F1): what the instruction under the cursor does, with the concrete
  before -> after values of registers / flags / memory of its last execution (or execution #n), the reason for
  every flag and whether the following conditional jump is taken.
* **What-If Console**: type instructions and initial register values, see each step explained + a flags table.

The markers go through radide/asm_lint's external-diagnostics hook when the analyzer provides one
(``publish_external(editor, "sim", issues)``, see docs/ASSEMBLY.md "Smart checks"), otherwise they are set on
the Monaco model with their own owner (``rad-asm-sim``) so they never replace the analyzer's markers. Explanations
follow the IDE language (Arabic / English) and show the other language below.
"""
from __future__ import annotations

import hashlib
import html
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (QComboBox, QDockWidget, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPlainTextEdit,
                             QPushButton, QSpinBox, QSplitter, QTableWidget, QTableWidgetItem, QTabWidget,
                             QTextBrowser, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

MARKER_OWNER = "rad-asm-sim"
SEV_TITLES = {"error": ("Error", "خطأ"), "warning": ("Warning", "تحذير"), "info": ("Note", "ملاحظة")}


def _lang() -> str:
    try:
        from .. import i18n
        return "ar" if i18n.language() == "ar" else "en"
    except Exception:  # noqa: BLE001
        return "en"


def _tr(text: str) -> str:
    try:
        from .. import i18n
        return i18n.tr(text)
    except Exception:  # noqa: BLE001
        return text


def _current_editor(win):
    try:
        from .editor_extras import current_editor
        return current_editor(win)
    except Exception:  # noqa: BLE001
        return None


def _is_asm(ed) -> bool:
    if ed is None:
        return False
    if getattr(getattr(ed, "plugin", None), "asm_intel", False):
        return True
    p = str(getattr(ed, "path", "") or "").lower()
    return p.endswith((".asm", ".nasm", ".s", ".inc", ".a86", ".8086"))


def _cursor_line(ed) -> int:
    """1-based line of the cursor."""
    try:
        return int(ed.getCursorPosition()[0]) + 1
    except Exception:  # noqa: BLE001
        return 1


def _selection_lines(ed):
    try:
        sel = getattr(ed, "_selection", None)
        if sel and (sel[0] != sel[2]):
            l1, l2 = sorted((sel[0], sel[2]))
            return l1 + 1, l2 + 1
    except Exception:  # noqa: BLE001
        pass
    return None


class _Signals(QObject):
    done = pyqtSignal(object, object)          # (kind, payload)


# ============================================================================ the window
class AsmChecksPanel(QWidget):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.result = None
        self.result_for = None                  # (path, text hash)
        self.editor = None
        self._busy = False
        self.sig = _Signals()
        self.sig.done.connect(self._on_done)
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 4, 4, 4)
        bar = QHBoxLayout()
        self.b_run = QPushButton("Check by Running")
        self.b_run.setToolTip("Run the program in a safe emulator and report runtime mistakes (Ctrl+Shift+F5)")
        self.b_proc = QPushButton("Check Procedure")
        self.b_proc.setToolTip("Run only the procedure under the cursor (arguments from the Registers box)")
        self.b_explain = QPushButton("Explain Line")
        self.b_explain.setToolTip("Explain the instruction under the cursor with its real values (Ctrl+Shift+F1)")
        self.b_install = QPushButton("Install Unicorn")
        self.b_install.setToolTip("pip install unicorn (official PyPI) - needed for 32 / 64-bit programs")
        self.b_install.setVisible(False)
        for b in (self.b_run, self.b_proc, self.b_explain, self.b_install):
            bar.addWidget(b)
        bar.addStretch(1)
        v.addLayout(bar)
        row = QHBoxLayout()
        row.addWidget(QLabel("Input:"))
        self.ed_input = QLineEdit("5")
        self.ed_input.setToolTip("What the program reads (scanf / ReadConsole / INT 21h): use \\n between lines")
        row.addWidget(self.ed_input, 2)
        row.addWidget(QLabel("Registers:"))
        self.ed_regs = QLineEdit()
        self.ed_regs.setPlaceholderText("rcx=5 rdx=0x10")
        self.ed_regs.setToolTip("Start values for 'Check Procedure' (its arguments), e.g. rcx=10 rdx=3")
        row.addWidget(self.ed_regs, 1)
        v.addLayout(row)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        v.addWidget(self.status)
        self.tabs = QTabWidget()
        v.addWidget(self.tabs, 1)
        # findings
        fw = QSplitter(Qt.Orientation.Vertical)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Severity", "Line", "Problem"])
        self.tree.setRootIsDecorated(False)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.details = QTextBrowser()
        self.details.setOpenExternalLinks(False)
        self.details.anchorClicked.connect(self._open_link)
        fw.addWidget(self.tree)
        fw.addWidget(self.details)
        self.tabs.addTab(fw, "Findings")
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.tabs.addTab(self.output, "Program Output")
        # explain
        ew = QWidget()
        ev = QVBoxLayout(ew)
        ev.setContentsMargins(0, 0, 0, 0)
        er = QHBoxLayout()
        er.addWidget(QLabel("Execution #"))
        self.sp_iter = QSpinBox()
        self.sp_iter.setRange(0, 9999)
        self.sp_iter.setSpecialValueText("last")
        self.sp_iter.setToolTip("Which execution of the line to explain (0 = the last one)")
        er.addWidget(self.sp_iter)
        er.addStretch(1)
        ev.addLayout(er)
        self.explain = QTextBrowser()
        self.explain.setOpenExternalLinks(False)
        self.explain.anchorClicked.connect(self._open_link)
        ev.addWidget(self.explain, 1)
        self.tabs.addTab(ew, "Explain")
        # what-if
        ww = QWidget()
        wv = QVBoxLayout(ww)
        wv.setContentsMargins(0, 0, 0, 0)
        w1 = QHBoxLayout()
        w1.addWidget(QLabel("Mode:"))
        self.cb_bits = QComboBox()
        self.cb_bits.addItems(["64-bit", "32-bit", "16-bit"])
        w1.addWidget(self.cb_bits)
        w1.addWidget(QLabel("Start values:"))
        self.ed_values = QLineEdit("eax=5 ebx=7")
        self.ed_values.setToolTip("Registers, flags and memory before the code runs: eax=5 ebx=0x10 CF=1 [0x2000]=1,2,3")
        w1.addWidget(self.ed_values, 1)
        self.b_whatif = QPushButton("Run")
        w1.addWidget(self.b_whatif)
        wv.addLayout(w1)
        self.ed_code = QPlainTextEdit("add eax, ebx\ncmp eax, 10\njle small\nsub eax, 10\nsmall:")
        self.ed_code.setMaximumHeight(110)
        wv.addWidget(self.ed_code)
        ws = QSplitter(Qt.Orientation.Horizontal)
        self.whatif_out = QTextBrowser()
        self.flags_table = QTableWidget(0, 3)
        self.flags_table.setHorizontalHeaderLabels(["Flag", "Value", "Meaning"])
        self.flags_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.flags_table.verticalHeader().setVisible(False)
        ws.addWidget(self.whatif_out)
        ws.addWidget(self.flags_table)
        ws.setSizes([600, 400])
        wv.addWidget(ws, 1)
        self.tabs.addTab(ww, "What-If")
        self.b_run.clicked.connect(lambda: self.run_check())
        self.b_proc.clicked.connect(lambda: self.run_check(proc=True))
        self.b_explain.clicked.connect(lambda: self.explain_line())
        self.b_whatif.clicked.connect(self.run_whatif)
        self.b_install.clicked.connect(self.install_unicorn)
        self.tree.currentItemChanged.connect(lambda cur, _prev: self._show_finding(cur))
        self.tree.itemDoubleClicked.connect(lambda it, _c: self._goto(it))

    # ------------------------------------------------------------ helpers
    def _editor(self):
        ed = _current_editor(self.win)
        if _is_asm(ed):
            self.editor = ed
            return ed
        if self.editor is not None:
            try:
                self.editor.text()
                return self.editor
            except RuntimeError:
                self.editor = None
        return None

    def _stdin(self) -> str:
        t = self.ed_input.text().replace("\\n", "\n")
        return t if t.endswith("\n") else t + "\n"

    def _regs(self) -> dict:
        from ..asm_sim.whatif import parse_values
        return parse_values(self.ed_regs.text())[0]

    def _set_busy(self, on: bool, text: str = "") -> None:
        self._busy = on
        for b in (self.b_run, self.b_proc, self.b_explain, self.b_whatif):
            b.setEnabled(not on)
        if text:
            self.status.setText(text)

    def _start(self, kind, fn) -> None:
        def work():
            try:
                payload = fn()
            except Exception as e:  # noqa: BLE001 - shown in the window
                import traceback
                payload = e
                traceback.print_exc()
            self.sig.done.emit(kind, payload)
        threading.Thread(target=work, daemon=True, name=f"asm-sim-{kind}").start()

    # ------------------------------------------------------------ check
    def run_check(self, proc: bool = False, selection: bool = False, wait: bool = False):
        ed = self._editor()
        if ed is None:
            self.status.setText(_tr("Open an assembly file first."))
            return None
        if self._busy:
            return None
        text, path = ed.text(), str(ed.path or "untitled.asm")
        line = _cursor_line(ed)
        lines = _selection_lines(ed) if selection else None
        stdin, regs = self._stdin(), self._regs() if proc else None
        self.result_for = (path, hashlib.sha1(text.encode("utf-8", "replace")).hexdigest(), ed)
        self._set_busy(True, _tr("Running the program in the emulator..."))
        self.tabs.setCurrentIndex(0)

        def fn():
            from ..asm_sim.check import check
            return check(text, path, stdin=stdin, proc_line=line if proc else None, lines=lines,
                         init_regs=regs, max_steps=500_000, timeout=12.0)
        if wait:
            res = fn()
            self._on_done("check", res)
            return res
        self._start("check", fn)
        return None

    def _on_done(self, kind, payload) -> None:
        self._set_busy(False)
        if isinstance(payload, Exception):
            self.status.setText(f"{_tr('The check failed')}: {payload}")
            return
        if kind == "check":
            self.show_result(payload)
        elif kind == "explain":
            self.show_explain(payload)
        elif kind == "whatif":
            self.show_whatif(payload)
        elif kind == "install":
            self.b_install.setVisible(not payload)
            self.status.setText(_tr("Unicorn is installed.") if payload else _tr("Installing Unicorn failed."))

    def show_result(self, res) -> None:
        lang = _lang()
        self.result = res
        self.b_install.setVisible(res.status == "unavailable")
        self.status.setText(res.summary(lang) if res.status not in ("asm_error",) else res.note(lang))
        self.tree.clear()
        for f in sorted(res.findings, key=lambda x: ({"error": 0, "warning": 1}.get(x.severity, 2), x.line)):
            sev = SEV_TITLES.get(f.severity, ("Note", "ملاحظة"))[1 if lang == "ar" else 0]
            it = QTreeWidgetItem([sev, str(f.line), f.message(lang)])
            it.setData(0, Qt.ItemDataRole.UserRole, f)
            colour = {"error": Qt.GlobalColor.darkRed, "warning": Qt.GlobalColor.darkYellow}.get(f.severity)
            if colour is not None:
                it.setForeground(0, colour)
            self.tree.addTopLevelItem(it)
        if res.errors:
            for e in res.errors[:20]:
                self.tree.addTopLevelItem(QTreeWidgetItem([_tr("Error"), "", e]))
        if self.tree.topLevelItemCount():
            self.tree.setCurrentItem(self.tree.topLevelItem(0))
        else:
            self.details.setHtml("<p>" + html.escape(
                "لم يجد الفحص أخطاء أثناء التشغيل." if lang == "ar" else "No runtime problems were found.") + "</p>")
        out = res.output or ""
        if res.calls:
            out += "\n\n---- " + _tr("calls") + " ----\n" + "\n".join(
                f"line {c.line}: {c.name}({c.args}) -> {c.result}" for c in res.calls[:200])
        self.output.setPlainText(out)
        self.publish(res)

    def _show_finding(self, it) -> None:
        f = it.data(0, Qt.ItemDataRole.UserRole) if it is not None else None
        if f is None:
            self.details.setHtml(html.escape(it.text(2)) if it is not None else "")
            return
        self.details.setHtml(finding_html(f, _lang()))

    def _goto(self, it) -> None:
        f = it.data(0, Qt.ItemDataRole.UserRole)
        if f is None or not f.line:
            return
        ed = self.result_for[2] if self.result_for else self._editor()
        try:
            ed.goto_line(f.line - 1)
            ed.setFocus()
        except Exception:  # noqa: BLE001
            pass

    def _open_link(self, url) -> None:
        import os
        if os.environ.get("RADIDE_NO_BROWSER"):
            return
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(url)

    # ------------------------------------------------------------ markers + Error List
    def publish(self, res) -> None:
        if not self.result_for:
            return
        path, _h, ed = self.result_for
        lang = _lang()
        mine = [f for f in res.findings if not f.file or _same(f.file, path)]
        issues = [f.issue_dict(lang) for f in mine]
        done = False
        try:
            from .. import asm_lint
            hook = getattr(asm_lint, "publish_external", None)
            if callable(hook):
                hook(ed, "sim", issues)
                done = True
        except Exception:  # noqa: BLE001
            done = False
        if not done:
            set_markers(ed, mine, lang)
        self._error_list(res, path)

    def _error_list(self, res, path) -> None:
        el = getattr(self.win, "error_list", None)
        if el is None:
            return
        for i in reversed(range(el.topLevelItemCount())):
            if el.topLevelItem(i).text(1).startswith("sim."):
                el.takeTopLevelItem(i)
        lang = _lang()
        for f in res.findings:
            if f.severity == "info":
                continue
            sev = "Error" if f.severity == "error" else "Warning"
            it = QTreeWidgetItem([sev, f"{f.rule}: {f.message(lang)}", f.file or path, str(max(1, f.line))])
            it.setForeground(0, Qt.GlobalColor.darkRed if sev == "Error" else Qt.GlobalColor.darkYellow)
            el.addTopLevelItem(it)
        if res.problems and hasattr(self.win, "dock_errors"):
            self.win.dock_errors.show()

    def diag_rows(self) -> list:
        """tools.run_checks provider: the last findings while the checked text is unchanged."""
        if not self.result or not self.result_for:
            return []
        path, h, ed = self.result_for
        try:
            if hashlib.sha1(ed.text().encode("utf-8", "replace")).hexdigest() != h:
                return []
        except RuntimeError:
            return []
        from ..tools import Diag
        lang = _lang()
        return [Diag("Error" if f.severity == "error" else "Warning", f"{f.rule}: {f.message(lang)}", f.file or path,
                     max(1, f.line)) for f in self.result.findings if f.severity in ("error", "warning")]

    # ------------------------------------------------------------ explain
    def explain_line(self, wait: bool = False):
        ed = self._editor()
        if ed is None:
            self.status.setText(_tr("Open an assembly file first."))
            return None
        if self._busy:
            return None
        text, path, line = ed.text(), str(ed.path or "untitled.asm"), _cursor_line(ed)
        it = self.sp_iter.value()
        stdin, regs = self._stdin(), self._regs()
        self.tabs.setCurrentIndex(2)
        self._set_busy(True, _tr("Running the program to explain the line..."))

        def fn():
            from ..asm_sim.check import explain_line
            return explain_line(text, path, line, stdin=stdin, iteration=(it - 1) if it > 0 else -1,
                                init_regs=regs or None)
        if wait:
            r = fn()
            self._on_done("explain", r)
            return r
        self._start("explain", fn)
        return None

    def show_explain(self, info: dict) -> None:
        lang = _lang()
        self.explain.setHtml(explain_html(info, lang))
        if info.get("ok"):
            self.status.setText((f"السطر {info['line']}: التنفيذ رقم {info['iteration']} من {info['count']}" if lang == "ar"
                                 else f"Line {info['line']}: execution {info['iteration']} of {info['count']}"))
        else:
            self.status.setText(info.get("note_ar" if lang == "ar" else "note_en") or "")

    # ------------------------------------------------------------ what-if
    def run_whatif(self, wait: bool = False):
        code, values = self.ed_code.toPlainText(), self.ed_values.text()
        bits = {0: 64, 1: 32, 2: 16}[self.cb_bits.currentIndex()]
        self._set_busy(True)

        def fn():
            from ..asm_sim.whatif import whatif
            return whatif(code, values, bits)
        if wait:
            r = fn()
            self._on_done("whatif", r)
            return r
        self._start("whatif", fn)
        return None

    def show_whatif(self, r: dict) -> None:
        lang = _lang()
        parts = []
        if r.get("error"):
            parts.append(f"<p style='color:#c62828'><b>{html.escape(r.get('error_ar') if lang == 'ar' and r.get('error_ar') else r['error'])}</b></p>")
        for s in r.get("steps", []):
            parts.append(step_html(s, lang))
        if r.get("regs"):
            regs = " ".join(f"{k.upper()}={v:#x}" for k, v in r["regs"].items() if k != "eflags" and v)
            parts.append(f"<p><b>{'المسجلات في النهاية' if lang == 'ar' else 'Registers at the end'}:</b> "
                         f"<code>{html.escape(regs)}</code></p>")
        self.whatif_out.setHtml("".join(parts))
        self.flags_table.setRowCount(0)
        for flag, value, en, ar in r.get("flags", []):
            row = self.flags_table.rowCount()
            self.flags_table.insertRow(row)
            self.flags_table.setItem(row, 0, QTableWidgetItem(flag))
            self.flags_table.setItem(row, 1, QTableWidgetItem(str(value)))
            self.flags_table.setItem(row, 2, QTableWidgetItem(ar if lang == "ar" else en))
        self.tabs.setCurrentIndex(3)

    def install_unicorn(self):
        self._set_busy(True, _tr("Installing Unicorn from PyPI..."))

        def fn():
            from ..asm_sim.check import install_unicorn
            return install_unicorn(log=lambda t: None)
        self._start("install", fn)


# ============================================================================ HTML / markers
def _same(a, b) -> bool:
    try:
        return Path(a).resolve() == Path(b).resolve()
    except OSError:
        return str(a).lower() == str(b).lower()


def finding_html(f, lang: str) -> str:
    other = "en" if lang == "ar" else "ar"
    ref = f.reference()

    def block(lg):
        rtl = lg == "ar"
        L = (("ماذا حدث؟", "كيف أصلحه؟", "التعليمة") if rtl else ("What happened?", "How to fix", "Instruction"))
        s = [f"<div dir='{'rtl' if rtl else 'ltr'}'>",
             f"<p><b>{html.escape(f.message(lg))}</b> <small>({f.rule})</small></p>",
             f"<p><b>{L[0]}</b> {html.escape(f.why(lg))}</p>",
             f"<p><b>{L[1]}</b> {html.escape(f.fix(lg))}</p>"]
        if f.instr:
            s.append(f"<p>{L[2]}: <code>{html.escape(f.instr)}</code></p>")
        s.append("</div>")
        return "".join(s)

    out = block(lang) + "<hr>" + block(other)
    if ref.get("url"):
        title = ref.get("title_ar") if lang == "ar" else ref.get("title_en")
        out += f"<p><a href='{ref['url']}'>{html.escape(title or ref.get('topic', ''))}</a></p>"
    return out


def step_html(s: dict, lang: str) -> str:
    from ..asm_sim.explain import to_html
    return to_html(s, lang, both=False)


def explain_html(info: dict, lang: str) -> str:
    from ..asm_sim.explain import to_html
    parts = []
    if not info.get("ok"):
        note = info.get("note_ar") if lang == "ar" else info.get("note_en")
        if note:
            parts.append(f"<p style='color:#8d6e00'>{html.escape(note)}</p>")
    if info.get("source"):
        parts.append(f"<p><code>{html.escape(info['source'])}</code></p>")
    for s in info.get("steps", []):
        parts.append(to_html(s, lang, both=True))
    if info.get("flags"):
        rows = "".join(f"<tr><td><b>{fl}</b></td><td>{v}</td><td>{html.escape(ar if lang == 'ar' else en)}</td></tr>"
                       for fl, v, en, ar in info["flags"])
        parts.append(f"<table border='0' cellspacing='4'>{rows}</table>")
    return "".join(parts)


def set_markers(ed, findings, lang: str) -> None:
    """Monaco markers with their own owner (the analyzer's 'rad' markers are left alone)."""
    import json
    items = []
    for f in findings:
        if not f.line:
            continue
        msg = f"{f.rule}: {f.message(lang)}\n\n{f.why(lang)}\n\n" + (
            "كيف أصلحه؟ " if lang == "ar" else "How to fix: ") + f.fix(lang)
        items.append({"startLineNumber": f.line, "startColumn": 1, "endLineNumber": f.line, "endColumn": 1000,
                      "message": msg, "severity": {"error": 8, "warning": 4}.get(f.severity, 2),
                      "source": "Check by running", "code": f.rule})
    if hasattr(ed, "_js"):
        ed._js("(function(){try{monaco.editor.setModelMarkers(radEditor.getModel(), %s, %s);}catch(e){}})();"
               % (json.dumps(MARKER_OWNER), json.dumps(items)))
    ed._asm_sim_markers = items


# ============================================================================ install
def ensure_panel(win) -> AsmChecksPanel:
    hub = getattr(win, "asm_checks", None)
    if hub is not None:
        return hub
    panel = AsmChecksPanel(win)
    dock = QDockWidget("Assembly Checks", win)
    dock.setObjectName("AsmChecks")
    dock.setWidget(panel)
    win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
    dock.hide()
    panel.dock = dock
    win.asm_checks = panel
    return panel


def show_panel(win) -> AsmChecksPanel:
    p = ensure_panel(win)
    p.dock.show()
    p.dock.raise_()
    return p


def _used_shortcuts(win) -> set:
    out = set()
    for a in win.findChildren(QAction):
        for s in a.shortcuts():
            out.add(s.toString())
    return out


def _context_menu(ed, menu, win) -> None:
    if not _is_asm(ed):
        return
    menu.addSeparator()
    menu.addAction(_tr("Explain This Line"), lambda: (show_panel(win).explain_line()))
    menu.addAction(_tr("Check by Running"), lambda: (show_panel(win).run_check()))
    menu.addAction(_tr("Check This Procedure"), lambda: (show_panel(win).run_check(proc=True)))


def _on_editor_ready(ed) -> None:
    if not _is_asm(ed) or getattr(ed, "_asm_sim_hooked", False):
        return
    sig = getattr(ed, "contextMenuAboutToShow", None)
    if sig is None:
        return
    ed._asm_sim_hooked = True
    try:
        sig.connect(lambda m, ed=ed: _context_menu(ed, m, ed.window()))
    except Exception:  # noqa: BLE001
        pass


def install(win) -> None:
    mb = win.menuBar() if hasattr(win, "menuBar") else None
    if mb is None:
        return
    debug = next((x.menu() for x in mb.actions() if x.menu() is not None and x.text().replace("&", "") == "Debug"),
                 None)
    if debug is None:
        return
    used = _used_shortcuts(win)
    sub = debug.addMenu("Assembly Checks")
    sub.setObjectName("AsmChecksMenu")

    def act(text, tip, fn, key=""):
        a = QAction(text, win)
        a.setStatusTip(tip)
        if key and key not in used:
            a.setShortcut(QKeySequence(key))
            a.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        a.triggered.connect(fn)
        sub.addAction(a)
        return a

    win.a_asm_check_run = act("Check by Running", "Run the assembly program in a safe emulator and report runtime "
                              "mistakes", lambda: show_panel(win).run_check(), "Ctrl+Shift+F5")
    win.a_asm_check_proc = act("Check This Procedure", "Run only the procedure under the cursor",
                               lambda: show_panel(win).run_check(proc=True))
    win.a_asm_check_sel = act("Check Selection", "Run only the selected lines",
                              lambda: show_panel(win).run_check(selection=True))
    sub.addSeparator()
    win.a_asm_explain = act("Explain This Line", "What the instruction does, with its real before -> after values",
                            lambda: show_panel(win).explain_line(), "Ctrl+Shift+F1")
    win.a_asm_whatif = act("What-If Console", "Try instructions on chosen register values",
                           lambda: (show_panel(win).tabs.setCurrentIndex(3)))
    sub.addSeparator()
    act("Assembly Checks Window", "Show the Assembly Checks window", lambda: show_panel(win))
    providers = getattr(win, "diag_providers", None)
    if providers is None:
        win.diag_providers = providers = []
    providers.append(lambda w: w.asm_checks.diag_rows() if getattr(w, "asm_checks", None) else [])
    try:
        from ..monaco_editor import MonacoEditor
        if _on_editor_ready not in MonacoEditor.ready_hooks:
            MonacoEditor.ready_hooks.append(_on_editor_ready)
    except ImportError:
        pass
