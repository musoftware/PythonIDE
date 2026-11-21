"""Visual Studio 2022's New Project dialog for .NET (Qt; the back end is catalog.py / create.py).

Three pages, like VS:

1. **Create a new project** - "Recent project templates" on the left; on the right "Search for templates",
   the "All languages" / "All platforms" / "All project types" filters and the template list (installed
   ``dotnet new`` templates incl. workload ones + RAD IDE's own: Shared Project, .NET Framework old-style ...).
2. **Configure your new project** - Project name, Location, Solution name, "Place solution and project in
   the same directory", "Project will be created in ..." (adding to an open solution hides the solution fields).
3. **Additional information** - Framework and the template's own options (from its parameters: checkboxes
   for bools, combos for choices, text boxes), then Create.

``show_wizard(win, add_to=None, preselect="", exec_=True)``: *add_to* is the open VsSolution to add the project
to (None = a new solution, opened in the IDE when created).
"""
from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel,
                             QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QStackedWidget,
                             QToolButton, QVBoxLayout, QWidget)

from . import catalog as C
from . import create as K

ROLE = Qt.ItemDataRole.UserRole
OFFSCREEN = os.environ.get("QT_QPA_PLATFORM", "") == "offscreen"
RECENT_KEY = "dotnet/recent_templates"
LOCATION_KEY = "dotnet/new_project_location"
LANG_COLORS = {"C#": "#68217A", "VB": "#00539C", "F#": "#378BBA", "": "#5C5C5C"}


def _log(win, text: str) -> None:
    try:
        win.log(text)
    except Exception:  # noqa: BLE001
        print(text)


_ICONS: dict = {}


def template_icon(t: C.TemplateInfo) -> QIcon:
    """A small badge: language colour + a glyph for the project type."""
    key = (t.language, t.short_name, t.source)
    if key in _ICONS:
        return _ICONS[key]
    pm = QPixmap(32, 32)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(LANG_COLORS.get(t.language, "#5C5C5C")))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(2, 2, 28, 28, 5, 5)
    p.setPen(QColor("white"))
    f = QFont()
    f.setBold(True)
    f.setPixelSize(11)
    p.setFont(f)
    glyph = {"Console": ">_", "Library": "{ }", "Desktop": "▣", "Web": "⊕", "Test": "✓",
             "Mobile": "▯", "Service": "⚙", "Shared": "⧉", "Other": "☐"}
    types = t.project_types
    txt = glyph.get(types[0], t.language or "sln") if types else (t.language or "sln")
    p.drawText(pm.rect().adjusted(0, -6, 0, 0), Qt.AlignmentFlag.AlignCenter, txt)
    f.setPixelSize(8)
    p.setFont(f)
    p.drawText(pm.rect().adjusted(0, 14, 0, 0), Qt.AlignmentFlag.AlignCenter, t.language or "")
    p.end()
    icon = QIcon(pm)
    _ICONS[key] = icon
    return icon


def _settings() -> QSettings:
    return QSettings()


def default_location() -> str:
    v = _settings().value(LOCATION_KEY, "")
    if v and Path(str(v)).is_dir():
        return str(v)
    return str(Path(os.environ.get("USERPROFILE") or Path.home()) / "source" / "repos")


def recent_keys() -> list[str]:
    v = _settings().value(RECENT_KEY, [])
    if isinstance(v, str):
        v = [v] if v else []
    return [str(x) for x in (v or [])]


def remember(t: C.TemplateInfo, location: str) -> None:
    keys = [t.key] + [k for k in recent_keys() if k != t.key]
    s = _settings()
    s.setValue(RECENT_KEY, keys[:10])
    s.setValue(LOCATION_KEY, location)


def _tag_html(t: C.TemplateInfo) -> str:
    return "  ".join(f"<span style='background:#e8e8e8;color:#333;padding:1px 4px'>&nbsp;{x}&nbsp;</span>"
                     for x in t.tags())


class NewProjectWizard(QDialog):
    def __init__(self, win, add_to=None, preselect: str = "", templates: list | None = None):
        super().__init__(win)
        self.win, self.add_to = win, add_to
        self.setWindowTitle("Add a new project" if add_to is not None else "Create a new project")
        self.setObjectName("dotnetNewProjectWizard")
        self.resize(1000, 640)
        self.templates = templates if templates is not None else C.all_templates()
        self.template: C.TemplateInfo | None = None
        self.result_info: K.NewProjectResult | None = None
        self.param_widgets: dict = {}
        lay = QVBoxLayout(self)
        self.stack = QStackedWidget()
        lay.addWidget(self.stack, 1)
        self._page_templates()
        self._page_configure()
        self._page_additional()
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        lay.addWidget(line)
        btns = QHBoxLayout()
        btns.addStretch(1)
        self.back_btn = QPushButton("Back")
        self.next_btn = QPushButton("Next")
        self.next_btn.setDefault(True)
        btns.addWidget(self.back_btn)
        btns.addWidget(self.next_btn)
        lay.addLayout(btns)
        self.back_btn.clicked.connect(self.back)
        self.next_btn.clicked.connect(self.next)
        self._filter()
        if preselect:
            self.select(preselect)
        self._update_buttons()

    # ------------------------------------------------------------------ page 1
    def _page_templates(self) -> None:
        page = QWidget()
        h = QHBoxLayout(page)
        left = QVBoxLayout()
        title = QLabel("Create a new project")
        f = title.font()
        f.setPointSize(f.pointSize() + 8)
        title.setFont(f)
        left.addWidget(title)
        left.addSpacing(8)
        rl = QLabel("Recent project templates")
        rl.setStyleSheet("font-weight: bold")
        left.addWidget(rl)
        self.recent = QListWidget()
        self.recent.setObjectName("recentTemplates")
        self.recent.setMaximumWidth(330)
        left.addWidget(self.recent, 1)
        h.addLayout(left, 1)
        right = QVBoxLayout()
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setObjectName("templateSearch")
        self.search.setPlaceholderText("Search for templates (Alt+S)")
        self.search.setClearButtonEnabled(True)
        top.addWidget(self.search, 1)
        clear = QToolButton()
        clear.setText("Clear all")
        clear.setAutoRaise(True)
        top.addWidget(clear)
        right.addLayout(top)
        combos = QHBoxLayout()
        langs, plats, types = C.filter_values(self.templates)
        from ...i18n import tr as _tr                    # combo items are not seen by the widget translator
        self.lang_combo = QComboBox()
        self.lang_combo.addItem(_tr("All languages"), "")
        for x in langs:
            self.lang_combo.addItem(x, x)
        self.plat_combo = QComboBox()
        self.plat_combo.addItem(_tr("All platforms"), "")
        for x in plats:
            self.plat_combo.addItem(x, x)
        self.type_combo = QComboBox()
        self.type_combo.addItem(_tr("All project types"), "")
        for x in types:
            self.type_combo.addItem(x, x)
        for c in (self.lang_combo, self.plat_combo, self.type_combo):
            combos.addWidget(c, 1)
            c.currentIndexChanged.connect(lambda *_: self._filter())
        right.addLayout(combos)
        self.list = QListWidget()
        self.list.setObjectName("templateList")
        self.list.setWordWrap(True)
        self.list.setIconSize(self.list.iconSize() * 2 if self.list.iconSize().width() < 32 else self.list.iconSize())
        self.list.setSpacing(2)
        right.addWidget(self.list, 1)
        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: gray")
        right.addWidget(self.count_label)
        h.addLayout(right, 2)
        self.search.textChanged.connect(lambda *_: self._filter())
        clear.clicked.connect(self.clear_filters)
        self.list.currentItemChanged.connect(lambda *_: self._update_buttons())
        self.list.itemDoubleClicked.connect(lambda *_: self.next())
        self.recent.itemClicked.connect(lambda it: self.select(it.data(ROLE)))
        self.recent.itemDoubleClicked.connect(lambda it: (self.select(it.data(ROLE)), self.next()))
        by_key = {t.key: t for t in self.templates}
        for k in recent_keys():
            t = by_key.get(k)
            if t is None:
                continue
            it = QListWidgetItem(template_icon(t), f"{t.name}    {t.language}")
            it.setData(ROLE, t.key)
            self.recent.addItem(it)
        if self.recent.count() == 0:
            it = QListWidgetItem("A list of your recently accessed templates will be displayed here.")
            it.setFlags(Qt.ItemFlag.NoItemFlags)
            self.recent.addItem(it)
        self.stack.addWidget(page)

    def clear_filters(self) -> None:
        for c in (self.lang_combo, self.plat_combo, self.type_combo):
            c.setCurrentIndex(0)
        self.search.clear()

    def _filter(self) -> None:
        cur = self.list.currentItem().data(ROLE).key if self.list.currentItem() else None
        shown = C.filter_templates(self.templates, self.search.text(), self.lang_combo.currentData() or "",
                                   self.plat_combo.currentData() or "", self.type_combo.currentData() or "")
        self.list.blockSignals(True)
        self.list.clear()
        for t in shown:
            it = QListWidgetItem(template_icon(t), f"{t.name}\n{t.description}\n" + "   ".join(t.tags()))
            it.setData(ROLE, t)
            it.setToolTip(f"{t.name} ({t.language or 'solution'})\n{t.description}\n"
                          + (f"dotnet new {t.short_name}" if t.source == "cli" else "RAD IDE template"))
            self.list.addItem(it)
            if t.key == cur:
                self.list.setCurrentItem(it)
        self.list.blockSignals(False)
        if self.list.currentItem() is None and self.list.count():
            self.list.setCurrentRow(0)
        self.count_label.setText(f"{len(shown)} templates" if shown else
                                 "No templates match your search. Clear the filters or search again.")
        self._update_buttons()

    def select(self, key: str, language: str = "C#") -> bool:
        t = C.find(self.templates, key, language)
        if t is None:
            return False
        for i in range(self.list.count()):
            if self.list.item(i).data(ROLE).key == t.key:
                self.list.setCurrentRow(i)
                return True
        self.clear_filters()
        for i in range(self.list.count()):
            if self.list.item(i).data(ROLE).key == t.key:
                self.list.setCurrentRow(i)
                return True
        return False

    def visible_templates(self) -> list[C.TemplateInfo]:
        return [self.list.item(i).data(ROLE) for i in range(self.list.count())]

    # ------------------------------------------------------------------ page 2
    def _header(self, lay, title: str) -> QLabel:
        t = QLabel(title)
        f = t.font()
        f.setPointSize(f.pointSize() + 8)
        t.setFont(f)
        lay.addWidget(t)
        sub = QLabel("")
        sub.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(sub)
        lay.addSpacing(10)
        return sub

    def _page_configure(self) -> None:
        page = QWidget()
        v = QVBoxLayout(page)
        self.cfg_sub = self._header(v, "Configure your new project")
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        self.name_edit = QLineEdit()
        self.name_edit.setObjectName("projectName")
        form.addRow("Project name", self.name_edit)
        locrow = QHBoxLayout()
        self.loc_edit = QLineEdit(default_location())
        self.loc_edit.setObjectName("projectLocation")
        browse = QToolButton()
        browse.setText("...")
        locrow.addWidget(self.loc_edit, 1)
        locrow.addWidget(browse)
        form.addRow("Location", locrow)
        self.sln_edit = QLineEdit()
        self.sln_edit.setObjectName("solutionName")
        self.sln_label = QLabel("Solution name")
        form.addRow(self.sln_label, self.sln_edit)
        self.same_dir = QCheckBox("Place solution and project in the same directory")
        form.addRow(self.same_dir)
        v.addLayout(form)
        self.where = QLabel("")
        self.where.setStyleSheet("color: gray")
        self.where.setWordWrap(True)
        v.addWidget(self.where)
        self.error = QLabel("")
        self.error.setStyleSheet("color: #C50F1F")
        v.addWidget(self.error)
        v.addStretch(1)
        self._sln_follows = True
        self.name_edit.textEdited.connect(self._name_changed)
        self.sln_edit.textEdited.connect(lambda *_: setattr(self, "_sln_follows", False))
        for w in (self.name_edit, self.loc_edit, self.sln_edit):
            w.textChanged.connect(lambda *_: self._update_where())
        self.same_dir.toggled.connect(lambda *_: self._update_where())
        browse.clicked.connect(self._browse)
        if self.add_to is not None:
            self.loc_edit.setText(str(self.add_to.folder))
            self.loc_edit.setEnabled(False)
            browse.setEnabled(False)
            for w in (self.sln_label, self.sln_edit, self.same_dir):
                w.hide()
        self.stack.addWidget(page)

    def _name_changed(self, text: str) -> None:
        if self._sln_follows:
            self.sln_edit.setText(text)
        self._update_where()

    def _browse(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Project Location", self.loc_edit.text())
        if d:
            self.loc_edit.setText(d)

    def request(self) -> K.NewProjectRequest:
        opts = {}
        for name, w in self.param_widgets.items():
            if isinstance(w, QCheckBox):
                opts[name] = w.isChecked()
            elif isinstance(w, QComboBox):
                opts[name] = w.currentData()
            else:
                opts[name] = w.text()
        fw = str(opts.pop("Framework", "") or "")
        return K.NewProjectRequest(self.template, self.name_edit.text().strip(), Path(self.loc_edit.text().strip()),
                                   self.sln_edit.text().strip(), self.same_dir.isChecked(), fw, opts,
                                   Path(self.add_to.file) if self.add_to is not None else None)

    def _update_where(self) -> None:
        if self.template is None:
            return
        self.sln_label.setEnabled(not self.same_dir.isChecked())
        self.sln_edit.setEnabled(not self.same_dir.isChecked())
        req = self.request()
        is_sln = self.template.kind == "solution"
        why = K.validate_name(req.name)
        if not why and req.solution is None and not req.same_dir and not is_sln:
            why = K.validate_name(req.solution_name).replace("Project", "Solution")
        if not why and not str(req.location):
            why = "Enter a location"
        pdir, sf = K.paths_for(req)
        if not why and not is_sln and pdir.exists() and any(pdir.glob(f"{req.name}.*proj")):
            why = f"The project '{pdir / req.name}' already exists."
        if not why and sf is not None and req.solution is None and sf.exists():
            why = f"The solution '{sf}' already exists."
        self.error.setText(why)
        if is_sln:
            self.where.setText(f'Solution will be created in "{pdir}\\"')
        else:
            self.where.setText(f'Project will be created in "{pdir}\\"')
        self._update_buttons()

    # ------------------------------------------------------------------ page 3
    def _page_additional(self) -> None:
        page = QWidget()
        v = QVBoxLayout(page)
        self.add_sub = self._header(v, "Additional information")
        self.params_host = QWidget()
        self.params_form = QFormLayout(self.params_host)
        self.params_form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        v.addWidget(self.params_host)
        v.addStretch(1)
        self.stack.addWidget(page)

    def _build_params(self) -> None:
        while self.params_form.rowCount():
            self.params_form.removeRow(0)
        self.param_widgets = {}
        t = self.template
        for p in (t.params if t else []):
            if p.kind == "bool":
                w = QCheckBox(p.label)
                w.setChecked(p.default.lower() == "true")
                w.setToolTip(p.description)
                self.params_form.addRow(w)
            elif p.kind == "choice" and p.choices:
                w = QComboBox()
                for val, disp in p.choices:
                    shown = disp if p.name.lower() != "framework" or val in disp else f"{disp} ({val})"
                    if p.name.lower() == "framework" and val.startswith("net") and "Support" not in shown:
                        if val in ("net8.0", "net10.0"):
                            shown += " (Long Term Support)"
                        elif val in ("net9.0",):
                            shown += " (Standard Term Support)"
                    w.addItem(shown, val)
                i = w.findData(p.default)
                w.setCurrentIndex(max(0, i))
                w.setToolTip(p.description)
                self.params_form.addRow(p.label, w)
            elif p.kind in ("text", "string", "integer"):
                w = QLineEdit(p.default)
                w.setToolTip(p.description)
                self.params_form.addRow(p.label, w)
            else:
                continue
            w.setObjectName(f"param_{p.name}")
            self.param_widgets[p.name] = w

    def set_option(self, name: str, value) -> bool:
        w = self.param_widgets.get(name)
        if w is None:
            return False
        if isinstance(w, QCheckBox):
            w.setChecked(bool(value))
        elif isinstance(w, QComboBox):
            i = w.findData(value)
            if i < 0:
                return False
            w.setCurrentIndex(i)
        else:
            w.setText(str(value))
        return True

    # ------------------------------------------------------------------ navigation
    def _has_params(self) -> bool:
        return bool(self.template and any(p.kind in ("bool", "choice", "text", "string", "integer")
                                          for p in self.template.params))

    def _update_buttons(self) -> None:
        if not hasattr(self, "next_btn"):
            return
        page = self.stack.currentIndex()
        self.back_btn.setEnabled(page > 0)
        if page == 0:
            self.next_btn.setText("Next")
            self.next_btn.setEnabled(self.list.currentItem() is not None)
        elif page == 1:
            self.next_btn.setText("Next" if self._has_params() else "Create")
            self.next_btn.setEnabled(not self.error.text())
        else:
            self.next_btn.setText("Create")
            self.next_btn.setEnabled(True)

    def back(self) -> None:
        if self.stack.currentIndex() > 0:
            self.stack.setCurrentIndex(self.stack.currentIndex() - 1)
        self._update_buttons()

    def next(self) -> None:
        page = self.stack.currentIndex()
        if page == 0:
            it = self.list.currentItem()
            if it is None:
                return
            t = it.data(ROLE)
            changed = t is not self.template
            self.template = t
            sub = f"<b>{t.name}</b>&nbsp;&nbsp;&nbsp;{_tag_html(t)}"
            self.cfg_sub.setText(sub)
            self.add_sub.setText(sub)
            if changed:
                self._build_params()
                base = "Solution" if t.kind == "solution" else (
                    "SharedProject" if t.project_types[:1] == ["Shared"] else
                    "ClassLibrary" if "Library" in t.project_types else
                    "TestProject" if "Test" in t.project_types else
                    "WinFormsApp" if "WinForms" in t.classifications else
                    "WpfApp" if "WPF" in t.classifications else
                    "WebApplication" if "Web" in t.project_types else
                    "WindowsService" if "Windows Service" in t.classifications else
                    "ConsoleApp" if "Console" in t.project_types else "Project")
                self.name_edit.setText(self._free_name(base))
                if self._sln_follows:
                    self.sln_edit.setText(self.name_edit.text())
            is_sln = t.kind == "solution"
            self.sln_label.setVisible(not is_sln and self.add_to is None)
            self.sln_edit.setVisible(not is_sln and self.add_to is None)
            self.same_dir.setVisible(not is_sln and self.add_to is None)
            self.stack.setCurrentIndex(1)
            self._update_where()
            self.name_edit.setFocus()
            self.name_edit.selectAll()
        elif page == 1:
            self._update_where()
            if self.error.text():
                return
            if self._has_params():
                self.stack.setCurrentIndex(2)
            else:
                self.create()
        else:
            self.create()
        self._update_buttons()

    def _free_name(self, base: str) -> str:
        loc = Path(self.add_to.folder) if self.add_to is not None else Path(self.loc_edit.text() or ".")
        i = 1
        while (loc / f"{base}{i}").exists():
            i += 1
        return f"{base}{i}"

    def create(self) -> K.NewProjectResult | None:
        if self.template is None:
            return None
        req = self.request()
        self.setCursor(Qt.CursorShape.WaitCursor)
        try:
            res = K.create(req, log=lambda t: _log(self.win, t))
        except (OSError, ValueError) as e:
            self.unsetCursor()
            self.error.setText(str(e).splitlines()[0])
            _log(self.win, f"*** {self.windowTitle()}: {e}")
            if not OFFSCREEN:
                QMessageBox.warning(self, self.windowTitle(), str(e)[-1500:])
            return None
        self.unsetCursor()
        self.result_info = res
        remember(self.template, str(req.location))
        self.accept()
        open_result(self.win, res, self.add_to)
        return res


def open_result(win, res: K.NewProjectResult, add_to=None) -> None:
    """Show what was created in the IDE: the new solution, or the new project in the open one."""
    if win is None or not hasattr(win, "solution"):
        return
    try:
        if add_to is not None and res.project_file is not None:
            from ...foreign.msbuild import MSBuildProject
            from ...foreign.vs_solution import VsProject, _add, load_solution_model
            add_to.model = load_solution_model(add_to.file)       # create() edited the .sln on disk
            if res.project_file.suffix.lower() == ".shproj":
                from ..shared import ui as SUI
                SUI.refresh(win)
                return
            n = os.path.normcase(str(Path(res.project_file).resolve()))
            entry = next((e for e in add_to.model.projects()
                          if os.path.normcase(str((add_to.model.folder / e.path).resolve())) == n), None)
            vp = VsProject(MSBuildProject.load(res.project_file), add_to, entry.name if entry else "")
            if entry is not None:
                vp.sln_entry = entry
            _add(add_to, vp)
            win._state_for(vp)
            from ..shared import ui as SUI
            SUI.refresh(win)
            win.activate_project(vp)
            from ...foreign import vs_ui
            vs_ui._open_first(win, vp)
            return
        if res.solution_file is not None:
            from ...foreign import vs_ui
            vs_ui.open_in_window(win, res.solution_file) if res.project_file is not None else \
                _open_blank(win, res.solution_file)
    except Exception as e:  # noqa: BLE001
        _log(win, f"*** cannot open {res.solution_file or res.project_file}: {e}")


def _open_blank(win, sln: Path) -> None:
    _log(win, f"Created blank solution {sln} - add projects with right-click > Add > New Project after opening "
              "one, or File > Open.")


def show_wizard(win, add_to=None, preselect: str = "", exec_: bool = True):
    dlg = NewProjectWizard(win, add_to, preselect)
    if not exec_:
        return dlg
    dlg.exec()
    return dlg.result_info


__all__ = ["NewProjectWizard", "show_wizard", "open_result", "template_icon", "recent_keys", "default_location"]
