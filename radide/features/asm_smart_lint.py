"""Smart assembly checks in the editor (the IDE side of radide/asm_lint): an assembly editor that explains your
mistakes while you type, in Arabic and English.

* Every Monaco editor of an assembly file (NASM / MASM / FASM / GNU as / emu8086) is analysed ~0.4 s after the
  last key press: squiggles (marker owner ``radAsmLint``) and a gutter icon per line (red / yellow / blue).
* Hovering a squiggle shows the full explanation: the message, **why** it is a problem, **how to fix it**, the
  quick fixes and a "Learn more" link (the IDE language decides Arabic or English; Arabic keeps the English
  message too, for web searches).
* Ctrl+. (the light bulb) lists the quick fixes of the issue under the caret (Monaco code actions) plus
  "Explain in the Problems panel".
* View > Problems Explained: a dock listing the issues of the current file with their explanation, a Fix button,
  Learn more (the instruction's reference from radide/asm_intel), the matching lesson of the Arabic assembly
  course, the assembler's own messages translated into friendly text, and Configure Rules (per project, saved
  in project.radproj "asm_lint").
* Error List: the issues of the project's assembly files join it (``win.diag_providers``); a row that repeats an
  assembler message on the same line is dropped, and assembler messages get a friendly explanation (tool tip;
  in Arabic the friendly text comes first).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QDockWidget, QHBoxLayout, QHeaderView, QLabel,
                             QListWidget, QListWidgetItem, QPushButton, QSplitter, QTableWidget, QTableWidgetItem,
                             QTextBrowser, QVBoxLayout, QWidget)

DEBOUNCE_MS = 400
LINT_ROLE = Qt.ItemDataRole.UserRole + 31
SEV_COLORS = {"error": "#e51400", "warning": "#bf8803", "info": "#1a85ff"}

JS_LINT = r"""(function () {
  if (window.__radAsmLint) return;
  const obj = window.radChannel && window.radChannel.objects.radAsmLint;
  const editor = window.radEditor;
  if (!obj || !editor) return;
  window.__radAsmLint = true;
  const model = editor.getModel();
  const lang = model.getLanguageId();
  let issues = [];
  let decos = [];
  const css = document.createElement('style');
  css.textContent =
    '.rad-lint-error,.rad-lint-warning,.rad-lint-info{border-radius:50%;margin:5px 0 0 4px;width:9px !important;' +
    'height:9px !important;}' +
    '.rad-lint-error{background:#e51400;box-shadow:0 0 0 1px #fff inset;}' +
    '.rad-lint-warning{background:#ddb100;}.rad-lint-info{background:#1a85ff;}';
  document.head.appendChild(css);
  const rank = s => s === 'error' ? 3 : s === 'warning' ? 2 : 1;
  const sev = s => s === 'error' ? monaco.MarkerSeverity.Error :
                   s === 'warning' ? monaco.MarkerSeverity.Warning : monaco.MarkerSeverity.Info;
  function apply(list) {
    issues = list || [];
    window.radAsmLintIssues = issues;
    monaco.editor.setModelMarkers(model, 'radAsmLint', issues.map(d => ({
      startLineNumber: d.line + 1, startColumn: d.col + 1, endLineNumber: d.endLine + 1, endColumn: d.endCol + 1,
      message: d.message, severity: sev(d.severity), code: d.rule, source: 'asm' })));
    const byLine = {};
    issues.forEach(d => { const o = byLine[d.line]; if (!o || rank(d.severity) > rank(o.severity)) byLine[d.line] = d; });
    decos = editor.deltaDecorations(decos, Object.keys(byLine).map(k => {
      const d = byLine[k];
      return { range: new monaco.Range(d.line + 1, 1, d.line + 1, 1),
               options: { glyphMarginClassName: 'rad-lint-' + d.severity,
                          glyphMarginHoverMessage: { value: d.markdown } } };
    }));
    window.radAsmLintStamp = (window.radAsmLintStamp || 0) + 1;
  }
  let timer = null;
  function run() {
    obj.lint(r => { let list = []; try { list = JSON.parse(r || '[]'); } catch (e) {} apply(list); });
  }
  window.radAsmLintRun = run;
  window.radAsmLintApply = apply;
  model.onDidChangeContent(() => { clearTimeout(timer); timer = setTimeout(run, %(debounce)d); });
  const covers = (d, pos) => {
    const l = pos.lineNumber - 1, c = pos.column - 1;
    if (l < d.line || l > d.endLine) return false;
    if (l === d.line && c < d.col) return false;
    if (l === d.endLine && c > d.endCol) return false;
    return true;
  };
  window.radAsmLintHover = (line, col) => issues.filter(d => covers(d, { lineNumber: line + 1, column: col + 1 }))
    .map(d => d.markdown);
  monaco.languages.registerHoverProvider(lang, {
    provideHover: (m, pos) => {
      if (m !== model) return null;
      const hits = issues.filter(d => covers(d, pos));
      if (!hits.length) return null;
      const d = hits[0];
      return { range: new monaco.Range(d.line + 1, d.col + 1, d.endLine + 1, d.endCol + 1),
               contents: hits.map(h => ({ value: h.markdown })) };
    } });
  const explainCmd = editor.addCommand(0, (ctx, idx) => obj.explain(idx));
  function actionsFor(m, range, markers) {
    const out = [];
    issues.forEach((d, idx) => {
      if (d.line + 1 > range.endLineNumber || d.endLine + 1 < range.startLineNumber) return;
      const mk = (markers || []).filter(x => x.code === d.rule && x.startLineNumber === d.line + 1);
      (d.fixes || []).forEach((f, k) => out.push({
        title: f.title, kind: 'quickfix', diagnostics: mk, isPreferred: k === 0,
        edit: { edits: f.edits.map(e => ({ resource: m.uri, versionId: undefined, textEdit: {
          range: new monaco.Range(e.range[0] + 1, e.range[1] + 1, e.range[2] + 1, e.range[3] + 1), text: e.text } })) }
      }));
      out.push({ title: d.explainTitle, kind: 'quickfix', diagnostics: mk,
                 command: { id: explainCmd, title: d.explainTitle, arguments: [idx] } });
    });
    return out;
  }
  window.radAsmLintActions = (line) => actionsFor(model, new monaco.Range(line + 1, 1, line + 1, 1), [])
    .map(a => a.title);
  window.radAsmLintApplyFix = (line, k) => {
    const acts = actionsFor(model, new monaco.Range(line + 1, 1, line + 1, 1), []).filter(a => a.edit);
    const a = acts[k || 0];
    if (!a) return false;
    editor.executeEdits('radAsmLint', a.edit.edits.map(e => ({ range: e.textEdit.range, text: e.textEdit.text,
                                                               forceMoveMarkers: true })));
    return true;
  };
  monaco.languages.registerCodeActionProvider(lang, {
    provideCodeActions: (m, range, context) => {
      if (m !== model) return { actions: [], dispose() {} };
      return { actions: actionsFor(m, range, context.markers), dispose() {} };
    } }, { providedCodeActionKinds: ['quickfix'] });
  run();
})();""".replace("%(debounce)d", str(DEBOUNCE_MS))


def _tr(text: str) -> str:
    try:
        from .. import i18n
        return i18n.tr(text)
    except Exception:  # noqa: BLE001
        return text


def ui_lang() -> str:
    try:
        from .. import i18n
        return "ar" if i18n.language() == "ar" else "en"
    except Exception:  # noqa: BLE001
        return "en"


def _plugin_id(plugin) -> str:
    base = getattr(plugin, "base_plugin", None)
    return str(getattr(base or plugin, "id", "") or "").lower()


def is_lint_editor(ed) -> bool:
    plugin = getattr(ed, "plugin", None)
    if plugin is None or not getattr(plugin, "asm_intel", False):
        return False
    pid = _plugin_id(plugin)
    if any(x in pid for x in ("retro", "agc", "6502", "z80", "gameboy", "nes", "c64", "atari")):
        return False
    return os.environ.get("RADIDE_ASM_LINT", "1") != "0"


def lint_editor(ed):
    """The issues of an editor's current text (radide.asm_lint.lint)."""
    from ..asm_lint import lint
    plugin = getattr(ed, "plugin", None)
    text = ed.text() if hasattr(ed, "text") else ed.toPlainText()
    return lint(text, getattr(ed, "path", None), dialect=None, plugin=plugin)


# ============================================================================ the channel object
class AsmLintBridge(QObject):
    """Published to each Monaco page as ``radAsmLint`` (used only by assembly editors)."""
    issuesChanged = pyqtSignal(object)

    def __init__(self, editor):
        super().__init__(editor)
        self.ed = editor
        self.issues: list = []

    @pyqtSlot(result=str)
    def lint(self) -> str:
        if not is_lint_editor(self.ed):
            return "[]"
        try:
            self.issues = lint_editor(self.ed)
        except Exception as e:  # noqa: BLE001 - the analyzer must never break typing
            print(f"[asm-lint] {e}")
            self.issues = []
        lang = ui_lang()
        out = []
        for it in self.issues:
            d = it.to_dict(lang)
            d["explainTitle"] = ("اشرح المشكلة " + it.rule) if lang == "ar" else f"Explain {it.rule}"
            out.append(d)
        try:
            self.issuesChanged.emit(self.issues)
            win = self.ed.window()
            panel = getattr(win, "_asm_lint_panel", None)
            if panel is not None:
                panel.editor_updated(self.ed, self.issues)
        except Exception:  # noqa: BLE001
            pass
        return json.dumps(out, ensure_ascii=False)

    @pyqtSlot(int)
    def explain(self, idx: int) -> None:
        try:
            win = self.ed.window()
            panel = ensure_panel(win)
            panel.show_editor(self.ed, self.issues, idx)
        except Exception as e:  # noqa: BLE001
            print(f"[asm-lint] explain: {e}")


def on_editor_ready(ed) -> None:
    if not is_lint_editor(ed):
        return
    try:
        ed._js(JS_LINT)
    except Exception as e:  # noqa: BLE001 - never break the editor
        print(f"[asm-lint] editor hook: {e}")


def apply_fix(ed, fix) -> None:
    """Apply a quick fix through the editor API (Problems panel 'Fix' button)."""
    edits = sorted(fix.edits, key=lambda e: (e["range"][0], e["range"][1]), reverse=True)
    if hasattr(ed, "beginUndoAction"):
        ed.beginUndoAction()
    try:
        for e in edits:
            l1, c1, l2, c2 = e["range"]
            if hasattr(ed, "_replace_range"):
                ed._replace_range(l1, c1, l2, c2, e["text"])
            else:                                    # the plain (QScintilla-like) editor
                ed.setSelection(l1, c1, l2, c2)
                ed.replaceSelectedText(e["text"])
    finally:
        if hasattr(ed, "endUndoAction"):
            ed.endUndoAction()
    # MonacoEditor._replace_range is muted in the page (no change event comes back): tell the listeners that
    # follow the user's edits (the CPU view's jump arrows / register references, the outline ...) like typing does
    sig = getattr(ed, "textEdited", None)
    if sig is not None:
        try:
            sig.emit()
        except (RuntimeError, TypeError):
            pass


# ============================================================================ Problems Explained panel
class RulesDialog(QDialog):
    """Enable / disable the rules and change their severity for this project (project.radproj "asm_lint")."""

    def __init__(self, path, parent=None):
        super().__init__(parent)
        from ..asm_lint import config
        from ..asm_lint.rules import RULES
        self.path = path
        self.setWindowTitle(_tr("Assembly Rules"))
        self.resize(820, 560)
        lay = QVBoxLayout(self)
        lang = ui_lang()
        cfg = config.project_config(path)
        levels = config.rule_levels(cfg)
        self.table = QTableWidget(len(RULES), 4)
        self.table.setHorizontalHeaderLabels([_tr("Rule"), _tr("Category"), _tr("Message"), _tr("Severity")])
        self.combos = {}
        for row, r in enumerate(RULES.values()):
            self.table.setItem(row, 0, QTableWidgetItem(r.id))
            self.table.setItem(row, 1, QTableWidgetItem(r.category))
            msg = (r.msg_ar if lang == "ar" else r.msg_en).split("{")[0].strip(" :'") or r.name
            self.table.setItem(row, 2, QTableWidgetItem(f"{r.name} - {msg}"))
            cb = QComboBox()
            for key, en in (("", f"Default ({r.severity})"), ("error", "Error"), ("warning", "Warning"),
                            ("info", "Hint"), ("off", "Off")):
                cb.addItem(_tr(en), key)
            cur = levels.get(r.id, "")
            cb.setCurrentIndex(max(0, cb.findData(cur)))
            self.table.setCellWidget(row, 3, cb)
            self.combos[r.id] = cb
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.table)
        note = QLabel(_tr("Suppress one line with a comment:") + "  ; asmlint-disable-line ASM101")
        lay.addWidget(note)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.save)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def values(self) -> dict:
        return {rid: cb.currentData() for rid, cb in self.combos.items() if cb.currentData()}

    def save(self) -> None:
        from ..asm_lint import config
        cfg = config.project_config(self.path)
        cfg["rules"] = self.values()
        cfg.setdefault("enabled", True)
        config.save_project_config(self.path, cfg)
        try:
            from .. import asm_lint
            asm_lint._LAST.clear()
        except Exception:  # noqa: BLE001
            pass
        self.accept()


class ProblemsPanel(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.ed = None
        self.issues: list = []
        self.asm_rows: list = []             # (message, line, explanation)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        self.title = QLabel()
        lay.addWidget(self.title)
        split = QSplitter(Qt.Orientation.Vertical)
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._show_row)
        self.list.itemDoubleClicked.connect(lambda _it: self.goto())
        split.addWidget(self.list)
        self.text = QTextBrowser()
        self.text.setOpenExternalLinks(False)
        self.text.anchorClicked.connect(self._link)
        split.addWidget(self.text)
        split.setSizes([180, 320])
        lay.addWidget(split, 1)
        row = QHBoxLayout()
        self.b_fix = QPushButton(_tr("Fix"))
        self.b_fix.clicked.connect(self.fix)
        self.b_goto = QPushButton(_tr("Go to Line"))
        self.b_goto.clicked.connect(self.goto)
        self.b_learn = QPushButton(_tr("Learn more"))
        self.b_learn.clicked.connect(self.learn)
        self.b_lesson = QPushButton(_tr("Open Lesson"))
        self.b_lesson.clicked.connect(self.lesson)
        self.b_rules = QPushButton(_tr("Configure Rules..."))
        self.b_rules.clicked.connect(self.rules)
        for b in (self.b_fix, self.b_goto, self.b_learn, self.b_lesson, self.b_rules):
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        self._refresh_buttons()

    # ------------------------------------------------------------ data
    def editor_updated(self, ed, issues) -> None:
        cur = _current_editor(self.win)
        if cur is ed or self.ed is None or self.ed is ed:
            self.show_editor(ed, issues, keep=True)

    def show_editor(self, ed, issues, idx: int = -1, keep: bool = False) -> None:
        old_rule = None
        if keep and 0 <= self.list.currentRow() < len(self.issues):
            o = self.issues[self.list.currentRow()]
            old_rule = (o.rule, o.line)
        self.ed = ed
        self.issues = list(issues or [])
        self.asm_rows = assembler_rows(self.win, getattr(ed, "path", None))
        lang = ui_lang()
        name = Path(str(getattr(ed, "path", "") or "")).name
        n_e = sum(i.severity == "error" for i in self.issues)
        n_w = sum(i.severity == "warning" for i in self.issues)
        n_i = len(self.issues) - n_e - n_w
        if lang == "ar":
            self.title.setText(f"{name}: {n_e} خطأ، {n_w} تحذير، {n_i} تلميح")
        else:
            self.title.setText(f"{name}: {n_e} error(s), {n_w} warning(s), {n_i} hint(s)")
        self.list.blockSignals(True)
        self.list.clear()
        for it in self.issues:
            item = QListWidgetItem(f"{it.line + 1}: {it.rule}  {it.message(lang)}")
            item.setForeground(QColor(SEV_COLORS.get(it.severity, "#888")))
            item.setToolTip(it.message("en"))
            self.list.addItem(item)
        for msg, line, exp in self.asm_rows:
            text = f"{line}: " + (exp.message(lang) if exp else msg)
            item = QListWidgetItem(("[المجمّع] " if lang == "ar" else "[assembler] ") + text)
            item.setForeground(QColor(SEV_COLORS["error"]))
            item.setToolTip(msg)
            self.list.addItem(item)
        self.list.blockSignals(False)
        sel = idx
        if sel < 0 and old_rule is not None:
            sel = next((k for k, i in enumerate(self.issues) if (i.rule, i.line) == old_rule), -1)
        if sel < 0 and self.list.count():
            sel = 0
        if sel >= 0:
            self.list.setCurrentRow(sel)
            self._show_row(sel)
        else:
            self.text.setMarkdown("لا توجد مشكلات في هذا الملف." if lang == "ar" else "No problems in this file.")
        self._refresh_buttons()
        if idx >= 0:
            dock = getattr(self.win, "_asm_lint_dock", None)
            if dock is not None:
                dock.show()
                dock.raise_()

    def current(self):
        r = self.list.currentRow()
        return self.issues[r] if 0 <= r < len(self.issues) else None

    def _show_row(self, r: int) -> None:
        lang = ui_lang()
        if 0 <= r < len(self.issues):
            it = self.issues[r]
            md = it.markdown(lang)
            if it.mnem:
                md += "\n\n---\n" + instruction_doc(it.mnem, lang)
            self.text.setMarkdown(md)
            self.text.setLayoutDirection(Qt.LayoutDirection.RightToLeft if lang == "ar" else
                                         Qt.LayoutDirection.LeftToRight)
        elif 0 <= r - len(self.issues) < len(self.asm_rows):
            msg, line, exp = self.asm_rows[r - len(self.issues)]
            self.text.setMarkdown(exp.markdown(msg, lang) if exp else f"**{msg}**")
        self._refresh_buttons()

    def _refresh_buttons(self) -> None:
        it = self.current()
        self.b_fix.setEnabled(bool(it and it.fixes))
        self.b_goto.setEnabled(self.list.currentRow() >= 0)
        self.b_learn.setEnabled(bool(it))
        self.b_lesson.setEnabled(bool(it and it.lesson()))
        self.b_rules.setEnabled(self.ed is not None)
        if it and it.fixes:
            self.b_fix.setToolTip(it.fixes[0].title(ui_lang()))

    # ------------------------------------------------------------ actions
    def _line_of_current(self) -> int:
        r = self.list.currentRow()
        if 0 <= r < len(self.issues):
            return self.issues[r].line
        if 0 <= r - len(self.issues) < len(self.asm_rows):
            return max(0, self.asm_rows[r - len(self.issues)][1] - 1)
        return -1

    def goto(self) -> None:
        line = self._line_of_current()
        if self.ed is not None and line >= 0:
            try:
                self.ed.goto_line(line)
                self.ed.setFocus()
            except Exception:  # noqa: BLE001
                pass

    def fix(self) -> None:
        it = self.current()
        if it is None or not it.fixes or self.ed is None:
            return
        apply_fix(self.ed, it.fixes[0])
        QTimer.singleShot(50, self.relint)

    def relint(self) -> None:
        if self.ed is None:
            return
        try:
            self.show_editor(self.ed, lint_editor(self.ed), keep=True)
            self.ed._js("if (window.radAsmLintRun) radAsmLintRun();")
        except Exception:  # noqa: BLE001
            pass

    def learn(self) -> None:
        it = self.current()
        if it is None:
            return
        lang = ui_lang()
        md = instruction_doc(it.mnem, lang) if it.mnem else ""
        url = it.learn_url()
        md += ("\n\n" if md else "") + (f"[المرجع]({url})" if lang == "ar" else f"[Reference]({url})")
        self.text.setMarkdown(md)

    def lesson(self) -> None:
        it = self.current()
        if it is None or not it.lesson():
            return
        try:
            from .tutorials import show_tutorials
            show_tutorials(self.win, "assembly", it.lesson())
        except Exception as e:  # noqa: BLE001
            print(f"[asm-lint] lesson: {e}")

    def rules(self) -> None:
        path = getattr(self.ed, "path", None)
        if path is None:
            return
        from ..asm_lint.config import project_file
        if project_file(path) is None:
            self.text.setMarkdown("Rules are saved per project: open the file inside a RAD IDE project." if
                                  ui_lang() != "ar" else "تُحفظ القواعد لكل مشروع: افتح الملف داخل مشروع RAD IDE.")
            return
        dlg = RulesDialog(path, self)
        if dlg.exec():
            self.relint()

    def _link(self, url) -> None:
        if os.environ.get("RADIDE_NO_BROWSER"):
            return
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(url)


def instruction_doc(mnem: str, lang: str = "en") -> str:
    """The instruction's reference text from radide/asm_intel (Learn more)."""
    try:
        from ..asm_intel import isa
        from ..asm_intel.engine import _ins_doc
        ins = isa.instruction(mnem) or isa.instruction(mnem, att=True)
        if ins is None:
            return ""
        return _ins_doc(ins)
    except Exception:  # noqa: BLE001
        return ""


def assembler_rows(win, path) -> list:
    """(message, line, explanation) of the Error List rows of the assembler for *path*."""
    out = []
    el = getattr(win, "error_list", None)
    if el is None or not path:
        return out
    from ..asm_lint.asm_errors import explain
    name = Path(str(path)).name.lower()
    for i in range(el.topLevelItemCount()):
        it = el.topLevelItem(i)
        if it.data(1, LINT_ROLE) == "lint" or Path(it.text(2)).name.lower() != name:
            continue
        msg = it.data(1, LINT_ROLE + 1) or it.text(1)
        try:
            line = int(it.text(3) or 0)
        except ValueError:
            line = 0
        out.append((msg, line, explain(msg)))
    return out


def _current_editor(win):
    try:
        cv = win._current_code() if hasattr(win, "_current_code") else None
        if cv is not None:
            return cv.editor
    except Exception:  # noqa: BLE001
        pass
    try:
        from PyQt6.QtWidgets import QApplication
        w = QApplication.focusWidget()
        while w is not None:
            if hasattr(w, "plugin") and hasattr(w, "path"):
                return w
            w = w.parentWidget()
    except Exception:  # noqa: BLE001
        pass
    return None


def ensure_panel(win) -> ProblemsPanel:
    panel = getattr(win, "_asm_lint_panel", None)
    if panel is not None:
        return panel
    panel = ProblemsPanel(win)
    dock = QDockWidget(_tr("Problems Explained"), win)
    dock.setObjectName("dock_asm_problems")
    dock.setWidget(panel)
    win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
    win._asm_lint_panel = panel
    win._asm_lint_dock = dock
    return panel


def show_panel(win) -> ProblemsPanel:
    panel = ensure_panel(win)
    ed = _current_editor(win)
    if ed is not None and is_lint_editor(ed):
        try:
            panel.show_editor(ed, lint_editor(ed))
        except Exception as e:  # noqa: BLE001
            print(f"[asm-lint] panel: {e}")
    win._asm_lint_dock.show()
    win._asm_lint_dock.raise_()
    return panel


# ============================================================================ Error List
def _asm_files(win) -> dict:
    """relative name -> (path, text) of the project's assembly files (open editors' text wins)."""
    project = getattr(win, "project", None)
    if project is None:
        return {}
    folder = Path(project.folder)
    from ..asm_intel.index import project_files
    open_texts = {}
    try:
        from ..tools import _open_editors
        for key, ed in _open_editors(win).items():
            if is_lint_editor(ed):
                open_texts[key] = ed
    except Exception:  # noqa: BLE001
        pass
    out = {}
    files = project_files(folder / "x.asm")[:60]
    for f in files:
        if f.suffix.lower() == ".inc" or f.name.startswith("_rad"):
            continue
        key = os.path.normcase(str(f.resolve()))
        ed = open_texts.get(key)
        try:
            text = ed.text() if ed is not None else (f.read_text(encoding="utf-8", errors="replace")
                                                      if f.stat().st_size < 400_000 else "")
        except OSError:
            continue
        if not text:
            continue
        try:
            rel = f.resolve().relative_to(folder.resolve()).as_posix()
        except ValueError:
            rel = f.name
        out[rel] = (f, text, ed)
    return out


def diag_provider(win) -> list:
    """tools.run_checks hook: the analyzer's errors and warnings of the project's assembly files."""
    if os.environ.get("RADIDE_ASM_LINT", "1") == "0":
        return []
    project = getattr(win, "project", None)
    if project is None:
        return []
    from ..asm_lint import lint
    from ..tools import Diag
    lang = ui_lang()
    out = []
    for rel, (f, text, ed) in _asm_files(win).items():
        try:
            plugin = getattr(ed, "plugin", None) if ed is not None else None
            issues = lint(text, f, dialect=None, plugin=plugin)
        except Exception:  # noqa: BLE001
            continue
        for it in issues:
            if it.severity == "info":
                continue
            out.append(Diag("Error" if it.severity == "error" else "Warning", it.title(lang), rel, it.line + 1))
    return out


class ErrorListMerger(QObject):
    """Drops analyzer rows that repeat an assembler message on the same line and explains assembler messages."""

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.busy = False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(0)
        self.timer.timeout.connect(self.process)
        el = getattr(win, "error_list", None)
        if el is not None:
            el.model().rowsInserted.connect(lambda *_a: self.timer.start())

    def process(self) -> None:
        el = getattr(self.win, "error_list", None)
        if el is None or self.busy:
            return
        self.busy = True
        try:
            from ..asm_lint.asm_errors import explain
            import re
            lang = ui_lang()
            asm_lines = set()
            rows = [el.topLevelItem(i) for i in range(el.topLevelItemCount())]
            for it in rows:
                msg = it.data(1, LINT_ROLE + 1) or it.text(1)
                if re.match(r"ASM\d{3}: ", it.text(1)):
                    it.setData(1, LINT_ROLE, "lint")
                    continue
                if it.text(0) not in ("Error", "Warning") or not it.text(2).lower().endswith(
                        (".asm", ".s", ".inc", ".nasm", ".fasm", ".masm", ".mac")):
                    continue
                asm_lines.add((Path(it.text(2)).name.lower(), it.text(3)))
                if it.data(1, LINT_ROLE + 1):
                    continue
                exp = explain(msg)
                it.setData(1, LINT_ROLE + 1, msg)
                if exp is not None:
                    it.setToolTip(1, exp.markdown(msg, lang).replace("**", "").replace("*", ""))
                    if lang == "ar":
                        it.setText(1, f"{exp.ar} — {msg}")
            for i in reversed(range(el.topLevelItemCount())):
                it = el.topLevelItem(i)
                if it.data(1, LINT_ROLE) == "lint" and (Path(it.text(2)).name.lower(), it.text(3)) in asm_lines \
                        and it.text(0) == "Error":
                    el.takeTopLevelItem(i)
        except Exception as e:  # noqa: BLE001 - never break the Error List
            print(f"[asm-lint] error list: {e}")
        finally:
            self.busy = False


# ============================================================================ install
def install(win) -> None:
    try:
        from ..monaco_editor import MonacoEditor
    except ImportError:                      # no QtWebEngine: the built-in editor has no Monaco hooks
        MonacoEditor = None
    if MonacoEditor is not None:
        MonacoEditor.channel_objects["radAsmLint"] = AsmLintBridge
        if on_editor_ready not in MonacoEditor.ready_hooks:
            MonacoEditor.ready_hooks.append(on_editor_ready)
    providers = getattr(win, "diag_providers", None)
    if providers is None:
        win.diag_providers = providers = []
    if diag_provider not in providers:
        providers.append(diag_provider)
    try:
        win._asm_lint_merger = ErrorListMerger(win)
    except Exception:  # noqa: BLE001
        pass
    win.show_asm_problems = lambda: show_panel(win)
    try:
        view = next((a.menu() for a in win.menuBar().actions()
                     if a.menu() is not None and a.text().replace("&", "") == "View"), None)
        if view is not None:
            act = view.addAction("Problems Explained")
            act.setStatusTip("The assembly analyzer's findings of the current file, explained (Arabic / English)")
            act.triggered.connect(lambda: show_panel(win))
            win.a_asm_problems = act
    except Exception:  # noqa: BLE001
        pass
