"""File > Import > Program (.exe / .dll)...  (docs/CONTRACTS.md 10.3)

A wizard: pick the file + legal notice -> identification -> options (target language, AI translation)
-> progress log -> import report -> the new project opens.

The backend for the file type (radide/importers/exe/*: dotnet, vb6, pyexe, java, electron, native) returns an
ImportResult; ``build_project`` turns it into a RAD IDE project in the chosen language (forms through the
neutral model, recovered event code through the action renderer, AI where the user allowed it) and writes
IMPORT_REPORT.md.
"""
from __future__ import annotations

import html
import json
import re
import shutil
import tempfile
import traceback
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QHeaderView, QLabel,
                             QLineEdit, QPlainTextEdit, QProgressBar, QPushButton, QTableWidget,
                             QTableWidgetItem, QTextBrowser, QVBoxLayout, QWizard, QWizardPage)

from .. import theme
from ..importers.exe import base as exe_base

LEGAL_NOTICE = ("Import only programs that you wrote, that you own, or that you are allowed to analyse "
                "(for example to recover your own lost source code or for interoperability). Decompiling "
                "software may be restricted by its licence or by law in your country. Recovered code is "
                "a starting point: check it before you use it.")
PREFERRED_LANGS = ("python-tk", "python-qt", "vb-basic")
BACKEND_TEXT = {
    "dotnet": "ILSpy (ilspycmd) -> C# source; WinForms InitializeComponent -> forms; C# -> Python by rules / AI",
    "vb6": "VB6 form structures -> .frm -> the VB6 importer; code: event names + strings (+ AI)",
    "pyexe": "pyinstxtractor -> .pyc -> decompiler -> the Python importer",
    "java": "jar -> CFR / Vineflower decompiler -> Java source (+ AI to Python)",
    "electron": "app.asar -> the JavaScript project",
    "native": "PE resources (dialogs, menus, strings, icons) + capstone disassembly; Ghidra when installed; "
              "Win32 calls -> handlers by rules (+ AI)",
}


# ============================================================================ project builder
def _ident(name: str, fallback: str) -> str:
    s = re.sub(r"\W", "_", str(name or "")).strip("_")
    if not s:
        return fallback
    return s if not s[0].isdigit() else f"{fallback}_{s}"


def _handler_target(form, key: str, plugin):
    """'btnOK.Click' / '.Load' / 'mnuFileExit.Click' -> (handler name, event) or None."""
    ctrl_name, _, event = key.rpartition(".")
    if not ctrl_name:
        return plugin.handler_for(form, None, event), event
    ctrl = form.find(ctrl_name)
    if ctrl is not None:
        return plugin.handler_for(form, ctrl, event), event
    menu = next((c for c in form.controls if c.type in ("MenuStrip", "ToolStrip")), None)
    if menu is not None:
        from ..controls import menu_names
        if ctrl_name in menu_names(menu.props.get("Items", [])):
            return plugin.handler_for(form, menu, ctrl_name), event
    return None


def _insert_body(code: str, line: int, body: list[str]) -> str:
    lines = code.splitlines()
    if not (0 <= line < len(lines)):
        return code
    cur = lines[line]
    indent = cur[:len(cur) - len(cur.lstrip())] if cur.strip() else cur
    if not indent:
        prev = lines[line - 1] if line > 0 else ""
        indent = prev[:len(prev) - len(prev.lstrip())] + "    "
    new = [indent + b if b else "" for b in body]
    if cur.strip() in ("pass", ""):
        lines[line:line + 1] = new
    else:
        lines[line:line] = new
    return "\n".join(lines) + "\n"


def _body_line(code: str, def_line: int) -> int:
    """First body line of an existing handler (its 'pass' / blank line when there is one)."""
    lines = code.splitlines()
    for i in range(def_line + 1, min(def_line + 4, len(lines))):
        if lines[i].strip() in ("pass", "", "{"):
            return i + 1 if lines[i].strip() == "{" else i
    return def_line + 1


def build_project(result, info, dest: Path, language: str = "python-tk", source: Path | None = None,
                  progress=None) -> tuple:
    """Write a RAD IDE project from an ImportResult.  Returns (Project | None, report markdown)."""
    from ..languages import get_plugin
    from ..controls import event_args
    from ..model import Form, Project
    progress = progress or (lambda _s: None)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    plugin = get_plugin(language)
    comment = (plugin.line_comments[0] if getattr(plugin, "line_comments", None) else "#")
    orig = dest / "_original"
    orig.mkdir(exist_ok=True)
    if source is not None and Path(source).is_file():
        try:
            if Path(source).stat().st_size <= 200 * 1024 * 1024:
                shutil.copy2(source, orig / Path(source).name)
        except OSError as e:
            result.add("warn", f"could not copy the original file: {e}")
    if result.source_dir and Path(result.source_dir).is_dir():
        src_dir = Path(result.source_dir)
        try:
            if dest.resolve() not in src_dir.resolve().parents and src_dir.resolve() != dest.resolve():
                shutil.copytree(src_dir, orig / "source", dirs_exist_ok=True)
        except OSError as e:
            result.add("warn", f"could not copy the recovered sources: {e}")
    name = _ident(Path(source).stem if source else (info.path.stem if info and info.path else "Imported"),
                  "Imported")
    project = Project(dest, name, language)
    # ---- resources: icons / strings
    icons = result.resources.get("icons") or []
    for icon_name, data in icons:
        try:
            (dest / f"{icon_name}.ico").write_bytes(data)
            _ico_to_png(dest / f"{icon_name}.ico", dest / f"{icon_name}.png")
        except OSError:
            pass
    strings = result.resources.get("strings") or {}
    is_python = language.startswith("python")
    # ---- forms
    progress("Writing forms and event handlers ...")
    used, forms_written = set(), []
    startup = result.resources.get("startup_form")
    for fname, fd in result.forms:
        try:
            form = Form.from_dict(fd if isinstance(fd, dict) else json.loads(fd))
        except Exception as e:  # noqa: BLE001
            result.add("warn", f"form {fname}: cannot be loaded ({e})")
            continue
        new_name = _ident(fname, "Form")
        while new_name.lower() in used:
            new_name += "_"
        used.add(new_name.lower())
        if new_name != fname and startup == fname:
            startup = new_name
        form.props["Name"] = new_name
        for c in form.controls:      # pictures that point to icons that were not written
            if c.type == "PictureBox" and c.props.get("Image") and not (dest / c.props["Image"]).exists():
                c.props["Image"] = ""
        is_startup = (startup == new_name) if startup else not project.forms
        code = plugin.new_code(form, is_startup)
        handlers = result.handlers.get(fname) or {}
        n_h = 0
        for key, actions in handlers.items():
            tgt = _handler_target(form, key, plugin)
            if tgt is None:
                result.add("warn", f"{new_name}: no control for handler {key}")
                continue
            hname, event = tgt
            body = exe_base.render_actions(actions, language, form.to_dict(), comment)
            if not body:
                continue
            line = plugin.find_handler(code, hname)
            try:
                if line >= 0:
                    code = _insert_body(code, _body_line(code, line), body)
                else:
                    code, bl = plugin.add_handler(code, hname, form, event_args(event))
                    code = _insert_body(code, bl, body)
                n_h += 1
            except Exception as e:  # noqa: BLE001
                result.add("warn", f"{new_name}.{hname}: could not insert the handler ({e})")
        # complete user code from the backend (handlers + fields + helper methods) when it targets this language
        full = (result.resources.get("form_code") or {}).get(fname)
        if full and new_name == fname and result.resources.get("form_code_language") == language:
            code = full
            n_h = max(n_h, len(handlers))
        form.save(project.form_path(new_name))
        (dest / plugin.code_file(new_name)).write_text(code, encoding="utf-8")
        try:
            (dest / plugin.designer_file(new_name)).write_text(plugin.generate_designer(form, code), encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            result.add("warn", f"{new_name}: designer code not generated ({e}) - open the form and save it")
        project.forms.append(new_name)
        forms_written.append((new_name, len(form.controls), n_h))
        if is_startup and not project.startup:
            project.startup = new_name
    if project.forms and not project.startup:
        project.startup = project.forms[0]
    # other forms reference each other (plugins that need it)
    if project.startup and len(project.forms) > 1:
        try:
            sf = dest / plugin.code_file(project.startup)
            text = sf.read_text(encoding="utf-8")
            for f in project.forms:
                if f != project.startup:
                    text = plugin.on_form_added(text, f)
            sf.write_text(text, encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    # ---- modules
    progress("Writing recovered code modules ...")
    rec = orig / "recovered"
    for mname, code, mlang in result.modules:
        mname = Path(str(mname)).name
        if not mname:
            continue
        ext = Path(mname).suffix.lower()
        same = (mlang in ("python", "py") and is_python and ext in ("", ".py")) or mlang == language or \
            (ext and ext == plugin.code_ext and mlang not in ("text", "c", "csharp", "java", "javascript"))
        if same and ext in ("", plugin.code_ext):
            fn = mname if ext else mname + plugin.code_ext
            stem = _ident(Path(fn).stem, "Module")
            fn = stem + plugin.code_ext
            (dest / fn).write_text(code, encoding="utf-8")
            if fn not in project.modules:
                project.modules.append(fn)
        else:
            rec.mkdir(exist_ok=True)
            (rec / mname).write_text(code, encoding="utf-8", errors="replace")
    if strings:
        if is_python:
            body = "\n".join(f"    {k}: {v!r}," for k, v in sorted(strings.items()))
            (dest / "strings.py").write_text('"""String table of the original program (STRINGTABLE resource)."""\n\n'
                                             f"STRINGS = {{\n{body}\n}}\n", encoding="utf-8")
            project.modules.append("strings.py")
        else:
            rec.mkdir(exist_ok=True)
            (rec / "strings.txt").write_text("\n".join(f"{k}\t{v}" for k, v in sorted(strings.items())),
                                             encoding="utf-8")
    project.save()
    report = report_markdown(result, info, project, forms_written, language, source)
    (dest / "IMPORT_REPORT.md").write_text(report, encoding="utf-8")
    return (project if project.forms or project.modules else None), report


def _ico_to_png(ico: Path, png: Path) -> None:
    try:
        from PyQt6.QtGui import QImage
        img = QImage(str(ico))
        if not img.isNull():
            img.save(str(png), "PNG")
    except Exception:  # noqa: BLE001
        pass


def report_markdown(result, info, project, forms_written, language, source) -> str:
    L = [f"# Import report - {Path(source).name if source else 'program'}", ""]
    if info is not None:
        L += ["## Identification", "", "| | |", "|---|---|"]
        L += [f"| {k} | {str(v).replace('|', '/')} |" for k, v in info.summary()]
        L.append("")
    L += ["## Result", "", f"- Target language: **{language}**"]
    if project is not None:
        L.append(f"- Project folder: `{project.folder}`")
        L.append(f"- Startup form: {project.startup or '(none)'}")
    for name, n, h in forms_written:
        L.append(f"- Form **{name}**: {n} control(s), {h} event handler(s) with recovered code")
    L.append("")
    groups = [("exact", "Recovered exactly"), ("rules", "Translated by rules"), ("ai", "Translated by AI"),
              ("missing", "Not recovered (missing)"), ("warn", "Warnings"), ("error", "Errors"), ("info", "Notes")]
    for level, title in groups:
        items = [t for lv, t in result.report if lv == level]
        if items:
            L += [f"## {title}", ""] + [f"- {t}" for t in items] + [""]
    ht = result.resources.get("handler_text")
    if ht:
        L += ["## Recovered event code (neutral form)", ""] + [f"- `{t}`" for t in ht[:200]] + [""]
    L += ["## Files", "", "- `_original/` - a copy of the imported file and anything recovered that is not "
          "project code (decompiled sources, reports, strings)",
          "- `IMPORT_REPORT.md` - this report", ""]
    L += ["---", "", LEGAL_NOTICE, ""]
    return "\n".join(L)


def markdown_to_html(md: str) -> str:
    """Tiny renderer for the report page (headings, lists, tables, code)."""
    out, in_list, in_table = [], False, False
    for raw in md.splitlines():
        line = html.escape(raw)
        line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
        line = re.sub(r"`(.+?)`", r"<code>\1</code>", line)
        if raw.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue
            if not in_table:
                out.append("<table cellspacing='0' cellpadding='3'>")
                in_table = True
            out.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
            continue
        if in_table:
            out.append("</table>")
            in_table = False
        if raw.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{line[2:]}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        if raw.startswith("# "):
            out.append(f"<h2>{line[2:]}</h2>")
        elif raw.startswith("## "):
            out.append(f"<h3>{line[3:]}</h3>")
        elif raw.strip() == "---":
            out.append("<hr>")
        elif raw.strip():
            out.append(f"<p>{line}</p>")
    if in_list:
        out.append("</ul>")
    if in_table:
        out.append("</table>")
    t = theme.current()
    style = (f"<style>body{{color:{t['text']};}} h2,h3{{color:{t['heading']};}} code{{color:{t['link']};}}"
             f" td{{border-bottom:1px solid {t['border']};}}</style>")
    return style + "\n".join(out)


def import_program(path: Path, dest: Path, language: str = "python-tk", ai_translate: bool = False,
                   progress=None, workdir: Path | None = None) -> tuple:
    """Identify + run the backend + build the project (used by the wizard worker and by scripts).
    Returns (Project | None, report markdown, ImportResult, BinaryInfo)."""
    progress = progress or (lambda _s: None)
    path = Path(path)
    progress(f"Identifying {path.name} ...")
    info = exe_base.identify(path)
    progress(f"  {info.label}")
    backend = exe_base.pick_backend(info)
    if backend is None:
        result = exe_base.ImportResult()
        result.add("error", f"No importer for this kind of file ({info.label}).")
        return None, report_markdown(result, info, None, [], language, path), result, info
    bname = backend.__name__.rsplit(".", 1)[-1]
    progress(f"Importer: {bname}")
    work = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="radexe_"))
    try:
        result = backend.run(path, info, work, progress, ai_translate)
    except Exception as e:  # noqa: BLE001 - shown in the report
        result = exe_base.ImportResult()
        result.add("error", f"{bname} importer failed: {e}")
        progress(traceback.format_exc())
    if bname != "native" and not result.forms and info.details.get("format", "").startswith("PE"):
        # nothing from the specialised importer: at least the resources and the code report
        try:
            from ..importers.exe import native
            progress("Falling back to the native importer (resources + disassembly) ...")
            result.merge(native.run(path, info, work, progress, ai_translate))
        except Exception as e:  # noqa: BLE001
            result.add("warn", f"native fallback failed: {e}")
    project, report = build_project(result, info, dest, language, path, progress)
    progress("Done." if project is not None else "Finished without a project (see the report).")
    return project, report, result, info


# ============================================================================ wizard
class _Worker(QThread):
    log = pyqtSignal(str)
    done = pyqtSignal(object)

    def __init__(self, path, dest, language, ai):
        super().__init__()
        self.args = (path, dest, language, ai)

    def run(self):
        path, dest, language, ai = self.args
        try:
            project, report, _result, _info = import_program(path, dest, language, ai, self.log.emit)
            self.done.emit((project, report, None))
        except Exception:  # noqa: BLE001
            self.done.emit((None, "", traceback.format_exc()))


class FilePage(QWizardPage):
    def __init__(self, wiz):
        super().__init__()
        self.setTitle("Import a program")
        self.setSubTitle("Choose a Windows program (.exe / .dll) - or a .jar / app.asar - to turn into a RAD IDE "
                         "project with forms and code.")
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        self.path = QLineEdit()
        self.path.setPlaceholderText("C:\\path\\to\\program.exe")
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse)
        row.addWidget(self.path, 1)
        row.addWidget(browse)
        lbl = QLabel("&Program file:")
        lbl.setBuddy(self.path)
        lay.addWidget(lbl)
        lay.addLayout(row)
        lay.addSpacing(12)
        notice = QLabel(LEGAL_NOTICE)
        notice.setWordWrap(True)
        theme.role(notice, "info")
        lay.addWidget(notice)
        self.agree = QCheckBox("I wrote this program, own it, or am allowed to analyse it")
        lay.addWidget(self.agree)
        lay.addStretch(1)
        self.registerField("exe_path*", self.path)
        self.registerField("exe_agree*", self.agree)
        self.path.textChanged.connect(self.completeChanged)
        self.agree.toggled.connect(self.completeChanged)

    def _browse(self):
        f, _ = QFileDialog.getOpenFileName(self, "Program to import", self.path.text(),
                                           "Programs (*.exe *.dll *.jar *.asar);;All files (*.*)")
        if f:
            self.path.setText(f)

    def isComplete(self) -> bool:
        return self.agree.isChecked() and Path(self.path.text().strip().strip('"')).is_file()


class IdentifyPage(QWizardPage):
    def __init__(self, wiz):
        super().__init__()
        self.wiz = wiz
        self.setTitle("What kind of program is it?")
        self.setSubTitle("The file was examined without running it.")
        lay = QVBoxLayout(self)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Property", "Value"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        lay.addWidget(self.table, 1)
        self.how = QLabel()
        self.how.setWordWrap(True)
        theme.role(self.how, "note")
        lay.addWidget(self.how)

    def initializePage(self):
        path = Path(self.field("exe_path").strip().strip('"'))
        try:
            info = exe_base.identify(path)
        except Exception as e:  # noqa: BLE001
            info = exe_base.BinaryInfo("unknown", {"error": str(e)}, path)
        self.wiz.info = info
        rows = info.summary()
        if info.details.get("error"):
            rows.append(("Problem", info.details["error"]))
        self.table.setRowCount(len(rows))
        for i, (k, v) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(k))
            self.table.setItem(i, 1, QTableWidgetItem(v))
        backend = exe_base.pick_backend(info)
        self.wiz.backend = backend
        if backend is None:
            self.how.setText("No importer can handle this file.")
        else:
            bname = backend.__name__.rsplit(".", 1)[-1]
            extra = ""
            describe = getattr(backend, "describe", None)
            if callable(describe):
                try:
                    extra = str(describe(info) or "")
                except Exception:  # noqa: BLE001
                    extra = ""
            self.how.setText(f"Importer: <b>{bname}</b> - {html.escape(extra or BACKEND_TEXT.get(bname, ''))}")
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return getattr(self.wiz, "backend", None) is not None


class OptionsPage(QWizardPage):
    def __init__(self, wiz):
        super().__init__()
        self.wiz = wiz
        self.setTitle("Options")
        self.setSubTitle("Where to create the project, in which language, and whether AI may translate code.")
        self.setCommitPage(True)
        self.setButtonText(QWizard.WizardButton.CommitButton, "&Import")
        form = QFormLayout(self)
        self.lang = QComboBox()
        from ..languages import all_plugins
        plugins = sorted(all_plugins(), key=lambda p: (p.id not in PREFERRED_LANGS,
                                                       PREFERRED_LANGS.index(p.id) if p.id in PREFERRED_LANGS else 0,
                                                       p.display_name))
        for p in plugins:
            self.lang.addItem(p.display_name, p.id)
        form.addRow("Target &language:", self.lang)
        row = QHBoxLayout()
        self.folder = QLineEdit()
        b = QPushButton("Browse...")
        b.clicked.connect(self._browse)
        row.addWidget(self.folder, 1)
        row.addWidget(b)
        form.addRow("Project folder:", row)
        self.ai = QCheckBox("Translate machine code / decompiled code to Python with AI")
        form.addRow("", self.ai)
        self.ai_status = QLabel()
        self.ai_status.setWordWrap(True)
        theme.role(self.ai_status, "muted")
        form.addRow("", self.ai_status)
        self.tools = QLabel()
        self.tools.setWordWrap(True)
        theme.role(self.tools, "muted")
        form.addRow("Tools:", self.tools)
        self.warn = QLabel()
        theme.role(self.warn, "error")
        form.addRow("", self.warn)
        self.folder.textChanged.connect(self._check)
        self.registerField("exe_ai", self.ai)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Parent folder for the new project",
                                             str(Path(self.folder.text()).parent))
        if d:
            src = Path(self.field("exe_path").strip().strip('"'))
            self.folder.setText(str(Path(d) / f"{src.stem}_RAD"))

    def initializePage(self):
        src = Path(self.field("exe_path").strip().strip('"'))
        target = src.parent / f"{src.stem}_RAD"
        i = 2
        while target.exists() and any(target.iterdir()):
            target, i = src.parent / f"{src.stem}_RAD{i}", i + 1
        self.folder.setText(str(target))
        i = self.lang.findData("python-tk")
        if self.wiz.info is not None and self.wiz.info.kind == "vb6":
            i = self.lang.findData("vb-basic")
        self.lang.setCurrentIndex(max(0, i))
        ok, label = ai_status()
        self.ai.setEnabled(ok)
        self.ai.setChecked(False)
        self.ai_status.setText(label)
        from ..importers.exe.native import find_ghidra
        g = find_ghidra()
        self.tools.setText(("Ghidra: " + (g if g else "not installed (optional - full pseudo-C decompilation; "
                                          "put it in %LOCALAPPDATA%\\RADIDE\\tools or set GHIDRA_HOME)")))
        self._check()

    def _check(self):
        t = Path(self.folder.text().strip()) if self.folder.text().strip() else None
        msg = ""
        if t is None:
            msg = "Choose a folder."
        elif t.exists() and any(t.iterdir()):
            msg = "This folder exists and is not empty."
        self.warn.setText(msg)
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        return not self.warn.text()


class ProgressPage(QWizardPage):
    def __init__(self, wiz):
        super().__init__()
        self.wiz = wiz
        self.setTitle("Importing")
        self.setSubTitle("The program is examined and a project is written. Large programs can take a while.")
        lay = QVBoxLayout(self)
        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        lay.addWidget(self.bar)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        lay.addWidget(self.log, 1)
        self.finished = False
        self.worker = None

    def initializePage(self):
        opts = self.wiz.options
        path = Path(self.field("exe_path").strip().strip('"'))
        dest = Path(opts.folder.text().strip())
        language = opts.lang.currentData()
        ai = bool(self.field("exe_ai"))
        self.finished = False
        self.log.clear()
        self.bar.setRange(0, 0)
        self.worker = _Worker(path, dest, language, ai)
        self.worker.log.connect(self.log.appendPlainText)
        self.worker.done.connect(self._done)
        self.worker.start()

    def _done(self, payload):
        project, report, err = payload
        self.wiz.project, self.wiz.report = project, report
        if err:
            self.log.appendPlainText(err)
            self.wiz.report = (report or "") + "\n\n## Error\n\n" + "\n".join(f"- {ln}" for ln in err.splitlines())
        self.bar.setRange(0, 1)
        self.bar.setValue(1)
        self.finished = True
        if self.worker is not None:
            self.worker.wait(2000)
        self.completeChanged.emit()
        if self.wiz.currentPage() is self:
            self.wiz.next()

    def isComplete(self) -> bool:
        return self.finished


class ResultPage(QWizardPage):
    def __init__(self, wiz):
        super().__init__()
        self.wiz = wiz
        self.setTitle("Import report")
        lay = QVBoxLayout(self)
        self.view = QTextBrowser()
        self.view.setOpenExternalLinks(True)
        lay.addWidget(self.view, 1)
        self.open = QCheckBox("Open the project now")
        self.open.setChecked(True)
        lay.addWidget(self.open)

    def initializePage(self):
        p = self.wiz.project
        self.setSubTitle(f"Project created in {p.folder}" if p is not None else
                         "No project could be created - see the report.")
        self.open.setEnabled(p is not None)
        self.open.setChecked(p is not None)
        self.view.setHtml(markdown_to_html(self.wiz.report or ""))


class ExeImportWizard(QWizard):
    def __init__(self, parent=None, path: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Import Program (.exe / .dll)")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.NoBackButtonOnLastPage, True)
        self.resize(780, 560)
        self.info = None
        self.backend = None
        self.project = None
        self.report = ""
        self.file_page = FilePage(self)
        self.identify = IdentifyPage(self)
        self.options = OptionsPage(self)
        self.progress = ProgressPage(self)
        self.result_page = ResultPage(self)
        for p in (self.file_page, self.identify, self.options, self.progress, self.result_page):
            self.addPage(p)
        if path:
            self.file_page.path.setText(path)

    def reject(self):
        w = self.progress.worker
        if w is not None and w.isRunning():
            return             # cannot stop a running import half-way; wait for it
        super().reject()


def ai_status() -> tuple[bool, str]:
    try:
        from .. import ai
        p, model = ai.default("edit")
        ok, why = p.available()
        if ok:
            return True, f"Uses your default AI provider: {p.name}{' / ' + model if model else ''} " \
                         "(Tools > Options > AI). Without AI, Win32 calls are translated by rules."
        return False, f"AI is not available ({p.name}: {why}). Win32 calls are still translated by rules."
    except Exception as e:  # noqa: BLE001
        return False, f"AI is not available ({e}). Win32 calls are still translated by rules."


def run_wizard(win, path: str = ""):
    if hasattr(win, "_confirm_close_project") and getattr(win, "project", None) is not None:
        if not win._confirm_close_project():
            return None
    wiz = ExeImportWizard(win, path)
    if wiz.exec() and wiz.project is not None:
        try:
            win.log(f"Imported {wiz.field('exe_path')} -> {wiz.project.folder}")
        except Exception:  # noqa: BLE001
            pass
        if wiz.result_page.open.isChecked():
            win.open_project(wiz.project.folder, ask=False)
    return wiz


def install(win) -> None:
    menu = getattr(win, "file_menu", None)
    if menu is None:
        menu = next((a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == "File"), None)
    if menu is None:
        return
    imp = next((a.menu() for a in menu.actions() if a.menu() is not None and a.text().replace("&", "") == "Import"),
               None)
    act = QAction("&Program (.exe / .dll)...", win)
    act.setStatusTip("Turn a compiled program into a project with forms and code (programs you may analyse)")
    act.triggered.connect(lambda: run_wizard(win))
    if imp is not None:
        imp.addSeparator()
        imp.addAction(act)
    else:
        menu.addAction(act)
    win.a_import_exe = act
