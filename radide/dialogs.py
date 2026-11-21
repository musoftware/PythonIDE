"""New Project dialog (VS 2005 style)."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                             QPushButton, QStyle, QVBoxLayout)

from .languages import all_plugins
from .properties import valid_identifier


def default_location() -> Path:
    return Path.home() / "Documents" / "RAD IDE Projects"


LANGUAGE_GROUPS = [
    ("Visual Basic", ["vb-basic"]),
    ("Python", ["python-tk", "python-qt"]),
    ("Ring", ["ring-qt", "ring-app"]),
    (".NET", ["csharp-bridge", "powershell-bridge"]),
    ("Java", ["java-bridge"]),
    ("Web", ["php-web", "static-web", "node-web",            # web site projects (CONTRACTS 8.1)
             "python-django", "python-flask", "python-fastapi",    # Python web frameworks (web_site/frameworks)
             "aspnet-web", "spring-web", "rails-web", "nestjs-web"]),  # backend frameworks (web_site/frameworks)
    ("Web & Script", ["javascript", "typescript", "php"]),
    ("Native", ["c-bridge", "cpp-bridge", "rust-bridge", "rust-cargo", "fortran-bridge", "go-bridge"]),
    ("Assembly", ["asm-nasm", "asm-fasm", "asm-masm", "asm-gas", "emu8086"]),     # docs/ASSEMBLY.md
    ("Scripting", ["lua-bridge", "ruby-bridge", "perl-bridge", "dart-bridge"]),
    ("Mobile", ["flutter", "kivy", "expo"]),                   # mobile apps (CONTRACTS 10.1)
    ("Games", ["pygame", "godot", "html5-game", "python-arcade", "ring-game",   # game projects (CONTRACTS 10.2)
               "python-ursina", "godot3d"]),                                     # 3D games (round 7, games3d/)
]
BADGE = {"vb-basic": ("VB", "#5C2D91"), "python-tk": ("Py", "#3572A5"), "python-qt": ("Qt", "#41CD52"),
         "ring-qt": ("Rg", "#2C3E50"), "ring-app": ("Rg", "#34495E"), "csharp-bridge": ("C#", "#178600"), "powershell-bridge": ("PS", "#012456"),
         "java-bridge": ("J", "#B07219"), "javascript": ("JS", "#C9A400"), "typescript": ("TS", "#3178C6"),
         "php": ("PHP", "#4F5D95"), "c-bridge": ("C", "#555555"), "cpp-bridge": ("C++", "#F34B7D"),
         "rust-bridge": ("Rs", "#B7410E"), "rust-cargo": ("Rs", "#DEA584"), "fortran-bridge": ("F", "#4D41B1"), "go-bridge": ("Go", "#00ADD8"),
         "asm-nasm": ("ASM", "#6E4C13"), "asm-fasm": ("FA", "#8B5A2B"), "asm-masm": ("ML", "#5C3D99"),
         "asm-gas": ("as", "#4E5A65"), "emu8086": ("86", "#9A4D00"),
         "lua-bridge": ("Lua", "#000080"), "ruby-bridge": ("Rb", "#CC342D"), "perl-bridge": ("Pl", "#0298C3"),
         "dart-bridge": ("Dt", "#00B4AB"), "php-web": ("PHP", "#777BB3"), "static-web": ("H5", "#E34F26"),
         "node-web": ("N", "#3C873A"), "pygame": ("Pg", "#2E7D32"), "godot": ("Gd", "#478CBF"),
         "flutter": ("Fl", "#02569B"), "kivy": ("Kv", "#5A7D2E"), "expo": ("RN", "#087EA4"),
         "html5-game": ("H5", "#F16529"), "python-arcade": ("Ar", "#7B3FA0"), "ring-game": ("RG", "#2C3E50"),
         "python-django": ("Dj", "#0C4B33"), "python-flask": ("Fk", "#2B2B2B"), "python-fastapi": ("FA", "#009688"),
         "python-ursina": ("3D", "#5B3F8C"), "godot3d": ("G3", "#2F6A9F"),
         "aspnet-web": ("ASP", "#512BD4"), "spring-web": ("Sp", "#6DB33F"), "rails-web": ("RoR", "#CC0000"),
         "nestjs-web": ("Ns", "#E0234E")}
TEMPLATE_ICONS = {"windows": "SP_ComputerIcon", "dialog": "SP_MessageBoxInformation",
                  "data": "SP_FileDialogDetailedView", "console": "rad:console",
                  "library": "SP_DriveHDIcon"}


def template_icon(style, name: str):
    """A QStyle standard icon name ("SP_...") or one of radide.icons ("rad:<name>")."""
    if name.startswith("rad:"):
        from .icons import icon
        return icon(name[4:], 32)
    return style.standardIcon(getattr(QStyle.StandardPixmap, name, QStyle.StandardPixmap.SP_FileIcon))


def badge_icon(pid: str, size: int = 28):
    from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
    text, colour = BADGE.get(pid, (pid[:2].upper(), "#777777"))
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(colour))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(1, 1, size - 2, size - 2, 6, 6)
    p.setPen(QColor("#ffffff"))
    p.setFont(QFont("Segoe UI", max(6, size // (3 if len(text) <= 2 else 4)), QFont.Weight.Bold))
    p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, text)
    p.end()
    return QIcon(pm)


def language_installed(plugin) -> tuple[bool, str]:
    """(installed?, short note) for the New Project dialog."""
    try:
        if hasattr(plugin, "tool"):
            t = plugin.tool()
            return (bool(t), Path(t).name if t else f"needs {', '.join(plugin.tool_names) or 'its compiler'}")
        exe = plugin.find_interpreter("")
        if exe and getattr(plugin, "id", "") == "vb-basic":
            return True, "built in (no install needed)"
        return (bool(exe), Path(exe).name if exe else "interpreter not found")
    except Exception as e:  # noqa: BLE001
        return (False, str(e))


class NewProjectDialog(QDialog):
    """Visual-Studio-style: language tree | templates | description, plus search."""

    def __init__(self, parent=None):
        super().__init__(parent)
        from PyQt6.QtWidgets import QSplitter, QTreeWidget, QTreeWidgetItem
        self.setWindowTitle("New Project")
        self.resize(940, 680)
        # plugins of projects opened in place from other IDEs (radide/foreign) are not new-project languages
        plugins = {p.id: p for p in all_plugins() if not getattr(p, "foreign_only", False)}
        self._plugins = plugins

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search languages and templates (e.g. python, c#, console)")
        self.search.textChanged.connect(self._filter)

        self.langs = QTreeWidget()
        self.langs.setHeaderHidden(True)
        self.langs.setIconSize(QSize(22, 22))
        grouped = set()
        for group, ids in LANGUAGE_GROUPS:
            g = QTreeWidgetItem([group])
            g.setFlags(Qt.ItemFlag.ItemIsEnabled)
            f = g.font(0)
            f.setBold(True)
            g.setFont(0, f)
            for pid in ids:
                if pid in plugins:
                    self._lang_item(g, plugins[pid])
                    grouped.add(pid)
            if g.childCount():
                self.langs.addTopLevelItem(g)
        rest = [p for pid, p in plugins.items() if pid not in grouped]
        if rest:
            g = QTreeWidgetItem(["Other"])
            for p in rest:
                self._lang_item(g, p)
            self.langs.addTopLevelItem(g)
        self.langs.expandAll()
        self.langs.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.langs.setMinimumWidth(250)

        self.templates = QListWidget()
        self.templates.setViewMode(QListWidget.ViewMode.IconMode)
        self.templates.setIconSize(QSize(40, 40))
        self.templates.setGridSize(QSize(150, 86))
        self.templates.setMovement(QListWidget.Movement.Static)
        self.templates.setWordWrap(True)
        self.templates.setFlow(QListWidget.Flow.LeftToRight)
        self.templates.setWrapping(True)
        self.templates.setResizeMode(QListWidget.ResizeMode.Adjust)
        try:
            from .features.templates import TEMPLATES
        except Exception:  # noqa: BLE001
            TEMPLATES = [("windows", "Windows Application", "An application with an empty form.")]
        self._template_list = TEMPLATES
        for tid, title, desc in TEMPLATES:
            icon = template_icon(self.style(), TEMPLATE_ICONS.get(tid, "SP_FileIcon"))
            it = QListWidgetItem(icon, title)
            it.setData(Qt.ItemDataRole.UserRole, tid)
            it.setToolTip(desc)
            self.templates.addItem(it)

        self.desc = QLabel()
        self.desc.setWordWrap(True)
        self.desc.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.desc.setMinimumWidth(200)
        self.desc.setProperty("radRole", "info")

        split = QSplitter()
        split.addWidget(self.langs)
        split.addWidget(self.templates)
        split.addWidget(self.desc)
        split.setSizes([290, 390, 240])
        split.setChildrenCollapsible(False)

        self.name = QLineEdit("WindowsApplication1")
        self.location = QLineEdit(str(default_location()))
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse)
        loc_row = QHBoxLayout()
        loc_row.addWidget(self.location, 1)
        loc_row.addWidget(browse)
        # Visual Studio: a project always lives in a solution (new one, or the open one)
        from PyQt6.QtWidgets import QCheckBox, QComboBox
        win = parent
        self._current_solution = getattr(win, "sln", None) if win is not None else None
        self.solution_mode = QComboBox()
        self.solution_mode.addItem("Create new solution", "new")
        if self._current_solution is not None:
            self.solution_mode.addItem(f"Add to solution '{self._current_solution.name}'", "add")
        self.solution_name = QLineEdit()
        self._sln_name_auto = True
        self.solution_name.textEdited.connect(lambda _t: setattr(self, "_sln_name_auto", False))
        self.name.textChanged.connect(self._sync_solution_name)
        self.same_dir = QCheckBox("Place solution and project in the same directory")
        self.solution_mode.currentIndexChanged.connect(lambda _i: self._on_solution_mode())
        form = QFormLayout()
        form.addRow("Name:", self.name)
        form.addRow("Location:", loc_row)
        form.addRow("Solution:", self.solution_mode)
        form.addRow("Solution name:", self.solution_name)
        form.addRow("", self.same_dir)
        self._sync_solution_name()
        self._on_solution_mode()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addWidget(self.search)
        lay.addWidget(split, 1)
        lay.addLayout(form)
        hint = QLabel("Tip: a solution holds projects in different languages. Create a Class Library in any "
                      "language, then right-click your project > Add > Reference... and call its functions "
                      "as normal code (e.g. MathLib.Add(2, 3)).")
        hint.setWordWrap(True)
        hint.setProperty("radRole", "muted")
        lay.addWidget(hint)
        lay.addWidget(buttons)

        self.langs.currentItemChanged.connect(lambda *_: self._sync_templates())
        self.langs.currentItemChanged.connect(lambda *_: self._update_desc())
        self.templates.currentItemChanged.connect(lambda *_: self._on_template())
        self.templates.itemDoubleClicked.connect(lambda *_: self._accept())
        # templates feature (radide/features/templates.py) adds a hidden combo we keep in sync
        try:
            from .features.templates import extend_new_project_dialog
            extend_new_project_dialog(self)
            if hasattr(self, "template_combo"):
                self.template_combo.hide()
                info = form.itemAt(1, QFormLayout.ItemRole.FieldRole)
                if info is not None and isinstance(info.widget(), QLabel):
                    info.widget().hide()
                lbl = form.labelForField(self.template_combo)
                if lbl is not None:
                    lbl.hide()
                pre = self.template_combo.currentData()
                for i in range(self.templates.count()):
                    if self.templates.item(i).data(Qt.ItemDataRole.UserRole) == pre:
                        self.templates.setCurrentRow(i)
        except Exception:  # noqa: BLE001 - templates are optional
            pass
        if self.templates.currentRow() < 0:
            self.templates.setCurrentRow(0)
        first = self.langs.topLevelItem(0)
        if first is not None and first.childCount():
            self.langs.setCurrentItem(first.child(0))
        self._update_desc()

    # ------------------------------------------------------------ web site templates (CONTRACTS 8.1)
    def _sync_templates(self):
        """Web site languages (php-web, static-web, node-web) show their own templates."""
        li = self.langs.currentItem()
        pid = li.data(0, Qt.ItemDataRole.UserRole) if li is not None else None
        plugin = self._plugins.get(pid) if pid else None
        web = getattr(plugin, "project_kind", "") == "website"
        # plugins with their own New Project templates (games, CONTRACTS 10.2): project_templates()
        own = not web and callable(getattr(plugin, "project_templates", None))
        mode = pid if (web or own) else ""
        if mode == getattr(self, "_templates_mode", ""):
            return
        was_web = bool(getattr(self, "_templates_mode", ""))
        self._templates_mode = mode
        if web:
            try:
                from .web_site.project import templates_for
                items = [(t.id, t.title, t.description, t.icon) for t in templates_for(pid)]
            except Exception:  # noqa: BLE001
                items = []
        elif own:
            try:
                items = list(plugin.project_templates())
            except Exception:  # noqa: BLE001
                items = []
        else:
            items = [(tid, title, desc, TEMPLATE_ICONS.get(tid, "SP_FileIcon"))
                     for tid, title, desc in self._template_list]
        self.templates.blockSignals(True)
        self.templates.clear()
        for tid, title, desc, icon in items:
            from .icons import template_badge
            it = QListWidgetItem(template_badge(tid) or template_icon(self.style(), icon or "SP_FileIcon"), title)
            it.setData(Qt.ItemDataRole.UserRole, tid)
            it.setToolTip(desc)
            self.templates.addItem(it)
        self.templates.setCurrentRow(0)
        self.templates.blockSignals(False)
        import re as _re
        cur = self.name.text()
        if web and _re.fullmatch(r"[A-Za-z]*(Application|Entry|Library)\d*|WebSite\d*", cur or "WebSite1"):
            self.name.setText(self._unique_name("WebSite"))
        elif own and _re.fullmatch(r"[A-Za-z]*(Application|Entry|Library)\d*|WebSite\d*|Game\d*|"
                                   r"FlutterApp\d*|KivyApp\d*|ExpoApp\d*", cur or "Game1"):
            self.name.setText(self._unique_name(getattr(plugin, "project_name_base", "Game")))
        elif not web and not own and was_web and _re.fullmatch(r"WebSite\d*|Game\d*|FlutterApp\d*|KivyApp\d*|ExpoApp\d*",
                                                                     cur):
            self.name.setText(self._unique_name("WindowsApplication"))

    def _unique_name(self, base: str) -> str:
        i = 1
        loc = Path(self.location.text())
        while (loc / f"{base}{i}").exists():
            i += 1
        return f"{base}{i}"

    def _lang_item(self, group, plugin):
        from PyQt6.QtWidgets import QTreeWidgetItem
        ok, note = language_installed(plugin)
        it = QTreeWidgetItem(group, [plugin.display_name.split(" (")[0] + (
            f"  ({plugin.display_name.split(' (', 1)[1]}" if " (" in plugin.display_name else "")])
        it.setIcon(0, badge_icon(plugin.id))
        it.setData(0, Qt.ItemDataRole.UserRole, plugin.id)
        it.setData(0, Qt.ItemDataRole.UserRole + 1, (ok, note))
        it.setToolTip(0, plugin.display_name + "  -  " +
                      (note if ok else f"not installed on this computer: {note}"))
        if not ok:
            it.setForeground(0, Qt.GlobalColor.gray)
        return it

    def _filter(self, text):
        q = text.strip().lower()
        for i in range(self.langs.topLevelItemCount()):
            g = self.langs.topLevelItem(i)
            any_visible = False
            for j in range(g.childCount()):
                c = g.child(j)
                pid = c.data(0, Qt.ItemDataRole.UserRole)
                hay = f"{c.text(0)} {pid} {g.text(0)} {self._plugins[pid].code_ext}".lower()
                show = not q or q in hay or any(q in t[1].lower() for t in self._template_list)
                c.setHidden(not show)
                any_visible |= show
            g.setHidden(not any_visible)
        for i in range(self.templates.count()):
            it = self.templates.item(i)
            it.setHidden(bool(q) and q not in it.text().lower() and not self._lang_matches(q))

    def _lang_matches(self, q):
        return any(q in f"{p.display_name} {p.id}".lower() for p in self._plugins.values())

    def _on_template(self):
        it = self.templates.currentItem()
        if it is not None and hasattr(self, "template_combo"):
            idx = self.template_combo.findData(it.data(Qt.ItemDataRole.UserRole))
            if idx >= 0:
                self.template_combo.setCurrentIndex(idx)
        self._update_desc()

    def _update_desc(self, *_):
        li = self.langs.currentItem()
        ti = self.templates.currentItem()
        pid = li.data(0, Qt.ItemDataRole.UserRole) if li is not None else None
        if pid is None:
            self.desc.setText("Choose a language on the left.")
            return
        p = self._plugins[pid]
        ok, note = li.data(0, Qt.ItemDataRole.UserRole + 1)
        tdesc = ti.toolTip() if ti is not None else ""
        from . import theme
        good, bad = theme.color("success"), theme.color("error")
        state = (f"<span style='color:{good}'>&#10004; {note}</span>" if ok and note.startswith("built in") else
                 f"<span style='color:{good}'>&#10004; installed ({note})</span>" if ok else
                 f"<span style='color:{bad}'>&#10008; not installed: {note}</span>")
        pm = p.package_manager.name if getattr(p, "package_manager", None) else "-"
        dbg = "yes" if p.supports_debug else "no"
        self.desc.setText(f"<b>{p.display_name}</b><br>{state}<br><br>"
                          f"<b>{ti.text() if ti else ''}</b><br>{tdesc}<br><br>"
                          f"Files: <code>*{p.code_ext}</code><br>Packages: {pm}<br>Debugger: {dbg}")

    # ------------------------------------------------------------ solution
    def _sync_solution_name(self, *_):
        if self._sln_name_auto:
            self.solution_name.setText(self.name.text())

    def _on_solution_mode(self):
        adding = self.adding_to_solution()
        self.solution_name.setEnabled(not adding)
        self.same_dir.setEnabled(not adding)
        self.location.setEnabled(not adding)
        if adding:
            self.location.setText(str(self._current_solution.folder))

    def adding_to_solution(self) -> bool:
        return self.solution_mode.currentData() == "add"

    def set_adding_to_solution(self, on: bool) -> None:
        idx = self.solution_mode.findData("add" if on else "new")
        if idx >= 0:
            self.solution_mode.setCurrentIndex(idx)

    def solution_folder(self) -> Path:
        """Folder of the .radsln (new solution) or of the current solution."""
        if self.adding_to_solution():
            return Path(self._current_solution.folder)
        if self.same_dir.isChecked():
            return Path(self.location.text()) / self.name.text()
        return Path(self.location.text()) / (self.solution_name.text().strip() or self.name.text())

    def solution_title(self) -> str:
        if self.adding_to_solution():
            return self._current_solution.name
        return self.solution_name.text().strip() or self.name.text()

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Project Location", self.location.text())
        if d:
            self.location.setText(d)

    def _accept(self):
        li = self.langs.currentItem()
        if li is None or li.data(0, Qt.ItemDataRole.UserRole) is None:
            QMessageBox.warning(self, "New Project", "Choose a language on the left.")
            return
        if not valid_identifier(self.name.text()):
            QMessageBox.warning(self, "New Project", "Project name must be a valid identifier.")
            return
        if not self.adding_to_solution() and not valid_identifier(self.solution_title()):
            QMessageBox.warning(self, "New Project", "Solution name must be a valid identifier.")
            return
        if self.adding_to_solution() and any(p.name.lower() == self.name.text().lower()
                                             for p in self._current_solution.projects):
            QMessageBox.warning(self, "New Project", f"The solution already has a project named "
                                                     f"'{self.name.text()}'.")
            return
        if self.folder().exists() and any(self.folder().iterdir()):
            QMessageBox.warning(self, "New Project", f"Folder already exists and is not empty:\n{self.folder()}")
            return
        if not self.adding_to_solution() and \
                (self.solution_folder() / f"{self.solution_title()}.radsln").exists():
            QMessageBox.warning(self, "New Project", f"A solution already exists there:\n{self.solution_folder()}")
            return
        self.accept()

    def folder(self) -> Path:
        """Folder of the new project."""
        if not self.adding_to_solution() and self.same_dir.isChecked():
            return Path(self.location.text()) / self.name.text()
        return self.solution_folder() / self.name.text()

    def language(self) -> str:
        li = self.langs.currentItem()
        pid = li.data(0, Qt.ItemDataRole.UserRole) if li is not None else None
        return pid or "python-tk"

    def template_id_value(self) -> str:
        ti = self.templates.currentItem()
        return ti.data(Qt.ItemDataRole.UserRole) if ti is not None else "windows"


class AddItemDialog(QDialog):
    """Add Windows Form / Add Module: a name and the language of the new file
    (default = the project language). One project can mix several languages."""

    def __init__(self, parent, title: str, default_name: str, default_language: str, forms: bool = True):
        super().__init__(parent)
        from PyQt6.QtWidgets import QComboBox
        self.setWindowTitle(title)
        self.resize(420, 150)
        self.name_edit = QLineEdit(default_name)
        self.name_edit.selectAll()
        self.lang = QComboBox()
        plugins = all_plugins()
        if not forms:              # one entry per file type (python-tk / python-qt share .py)
            seen, uniq = set(), []
            for p in sorted(plugins, key=lambda p: p.id != default_language):
                if p.code_ext not in seen:
                    seen.add(p.code_ext)
                    uniq.append(p)
            plugins = sorted(uniq, key=lambda p: p.display_name.lower())
        for p in plugins:
            self.lang.addItem(f"{p.display_name}   ({p.code_ext})" + ("   - project default"
                                                                      if p.id == default_language else ""), p.id)
        idx = self.lang.findData(default_language)
        if idx < 0 and not forms:
            ext = next((p.code_ext for p in all_plugins() if p.id == default_language), "")
            idx = next((i for i, p in enumerate(plugins) if p.code_ext == ext), 0)
        self.lang.setCurrentIndex(max(idx, 0))
        self.hint = QLabel("Code in other languages is called with radcall(\"Module.function\", ...).")
        self.hint.setProperty("radRole", "muted")
        self.hint.setWordWrap(True)
        form = QFormLayout()
        form.addRow("Name:", self.name_edit)
        form.addRow("Language:", self.lang)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(self.hint)
        lay.addWidget(buttons)

    def name(self) -> str:
        return self.name_edit.text().strip()

    def language(self) -> str:
        return self.lang.currentData()
