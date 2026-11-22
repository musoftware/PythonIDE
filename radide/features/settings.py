"""Tools > Options: editor font / size / tab width, Light or Dark theme,
designer grid size and snap, interpreter path per language, auto-save interval.
Everything is stored in the IDE's QSettings and applied live."""
from __future__ import annotations

import json

from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPalette
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                             QFontComboBox, QFormLayout, QGridLayout, QLabel, QLineEdit,
                             QPushButton, QScrollArea, QSpinBox, QTabWidget, QVBoxLayout, QWidget)

DEFAULTS = {"theme": "Light", "editor_font": "Consolas", "editor_font_size": 10, "tab_width": 4,
            "grid_size": 8, "snap": True, "autosave_seconds": 60, "ui_font_size": 9,
            "show_start_page": True, "reopen_last": False, "confirm_unsaved": True}
LAYOUTS = [("vs", "Visual Studio"), ("vscode", "VS Code"), ("agent", "Agent")]
KEY = "options/"
# extra Options pages added by other features: hook(dialog) -> (widget, title, apply_fn) or None
PAGE_HOOKS: list = []

LIGHT_CODE = {"keyword": "#0000FF", "builtin": "#2B91AF", "comment": "#008000", "string": "#A31515",
              "number": "#098658", "decorator": "#795E26", "defname": "#795E26", "operator": "#000000"}
DARK_CODE = {"keyword": "#569CD6", "builtin": "#4EC9B0", "comment": "#6A9955", "string": "#CE9178",
             "number": "#B5CEA8", "decorator": "#DCDCAA", "defname": "#DCDCAA", "operator": "#D4D4D4"}
LIGHT_CHROME = {"margin": "#F3F3F3", "margin_bp": "#E6E6E6", "line_number": "#2B91AF",
                "breakpoint_line": "#F7D9D6", "current_stmt": "#FFF3A0", "caret_line": "#EEF4FF"}
DARK_CHROME = {"margin": "#1E1E1E", "margin_bp": "#252526", "line_number": "#858585",
               "breakpoint_line": "#5A1D1D", "current_stmt": "#4B4B18", "caret_line": "#2A2D2E"}
CALLTIP = {"Light": "background:#FFFFE1; color:#000000; border:1px solid #888; padding:3px;",
           "Dark": "background:#252526; color:#D4D4D4; border:1px solid #555; padding:3px;"}
DESIGNER_BACK = {"Light": "#FFFFFF", "Dark": "#252526"}

DARK_STYLE = """
QMainWindow, QDockWidget { background: #2D2D30; }
QDockWidget::title { background: #3F3F46; color: #F1F1F1; padding: 4px; border: 1px solid #2D2D30;
                     font-weight: bold; }
QTabBar::tab { background: #2D2D30; color: #D0D0D0; padding: 4px 10px; border: 1px solid #3F3F46; }
QTabBar::tab:selected { background: #1E1E1E; color: #FFFFFF; border-bottom-color: #007ACC; }
QTabBar::tab:hover { background: #3E3E42; }
QToolBar { background: #333337; border-bottom: 1px solid #3F3F46; spacing: 2px; }
QStatusBar { background: #007ACC; color: #FFFFFF; }
QStatusBar QLabel { color: #FFFFFF; }
QMenuBar { background: #2D2D30; color: #F1F1F1; }
QMenuBar::item:selected { background: #3E3E40; }
QMenu { background: #1B1B1C; color: #F1F1F1; border: 1px solid #333337; }
QMenu::item:selected { background: #3E3E40; }
QMenu::separator { height: 1px; background: #3F3F46; margin: 3px 6px; }
QHeaderView::section { background: #333337; color: #D0D0D0; border: 0; border-right: 1px solid #3F3F46;
                       padding: 3px; }
QToolTip { background: #252526; color: #F1F1F1; border: 1px solid #555; }
"""


def get(win, name: str):
    v = win.settings.value(KEY + name, DEFAULTS[name])
    d = DEFAULTS[name]
    if isinstance(d, bool):
        return v if isinstance(v, bool) else str(v).lower() in ("1", "true", "yes")
    if isinstance(d, int):
        try:
            return int(v)
        except (TypeError, ValueError):
            return d
    return str(v) if v is not None else d


def dark_palette() -> QPalette:
    p = QPalette()
    R = QPalette.ColorRole
    G = QPalette.ColorGroup
    for role, c in ((R.Window, "#2D2D30"), (R.WindowText, "#F1F1F1"), (R.Base, "#1E1E1E"),
                    (R.AlternateBase, "#252526"), (R.ToolTipBase, "#252526"), (R.ToolTipText, "#F1F1F1"),
                    (R.Text, "#D4D4D4"), (R.Button, "#3C3C3C"), (R.ButtonText, "#F1F1F1"),
                    (R.BrightText, "#FF5555"), (R.Highlight, "#264F78"), (R.HighlightedText, "#FFFFFF"),
                    (R.Link, "#3794FF"), (R.LinkVisited, "#C586C0"), (R.PlaceholderText, "#8A8A8A"),
                    (R.Light, "#505050"), (R.Midlight, "#3F3F46"), (R.Mid, "#333337"), (R.Dark, "#1B1B1C"),
                    (R.Shadow, "#000000")):
        p.setColor(role, QColor(c))
    for role in (R.WindowText, R.Text, R.ButtonText):
        p.setColor(G.Disabled, role, QColor("#6D6D6D"))
    p.setColor(G.Disabled, R.Base, QColor("#252526"))
    return p


def light_palette() -> QPalette:
    """An explicit light palette (Qt's standard palette follows Windows' dark mode)."""
    from .. import theme
    return theme.light_form_palette()


# ===================================================================== apply
def _editors(win, widgets=None):
    """Code editors (CodeEditor, MonacoEditor) of the window; *widgets*: win.findChildren(QWidget) when the caller
    already has it (PyQt's typed findChildren is slower than one untyped search + isinstance)."""
    from .. import editor as E
    widgets = win.findChildren(QWidget) if widgets is None else widgets
    out = [w for w in widgets if isinstance(w, E.CodeEditor)]
    for w in widgets:
        if type(w).__name__ == "MonacoEditor" and hasattr(w, "_js"):
            out.append(w)
    return out


def apply_editor(win, ed=None):
    from .. import editor as E
    family, size, tab = get(win, "editor_font"), get(win, "editor_font_size"), get(win, "tab_width")
    from .. import theme as T
    t = T.current()
    E.FONT.setFamily(family)
    E.FONT.setPointSize(size)
    E.INDENT = " " * max(1, tab)
    code, chrome = t["code"], t["chrome"]
    E.COLORS.update(code)
    if hasattr(E, "EDITOR_THEME"):
        E.EDITOR_THEME.update(chrome)
    for e in ([ed] if ed is not None else _editors(win)):
        try:
            if hasattr(e, "_js") and not isinstance(e, E.CodeEditor):
                e._js(f"radSetFont({json.dumps(family)}, {int(size) + 3});"
                      f"radSetTheme({json.dumps(t['monaco'])});"
                      f"radEditor.updateOptions({{tabSize: {int(tab)}}});")
                continue
            f = QFont(E.FONT)
            e.setFont(f)
            e.setTabStopDistance(QFontMetrics(f).horizontalAdvance(" ") * max(1, tab))
            hl = getattr(e, "highlighter", None)
            if hl is not None and hasattr(hl, "fmt"):
                for name, fmt in hl.fmt.items():
                    if name in E.COLORS:
                        fmt.setForeground(QColor(E.COLORS[name]))
                hl.rehighlight()
            if hasattr(e, "calltip_label"):
                e.calltip_label.setStyleSheet("")
                T.role(e.calltip_label, "calltip")
            if hasattr(e, "detail"):
                e.detail.setStyleSheet("")
                T.role(e.detail, "calltip")
            if hasattr(e, "_update_margin_width"):
                e._update_margin_width()
            if hasattr(e, "margin"):
                e.margin.update()
            if hasattr(e, "_highlight_current"):
                e._highlight_current()
            e._rad_options = _generation(win)
        except Exception as ex:  # noqa: BLE001 - options must never break an editor
            win.log(f"[options] editor: {ex}")


def apply_designer(win, view=None):
    from .. import designer as D
    grid = max(2, min(64, get(win, "grid_size")))
    D.GRID = grid
    if not hasattr(D, "_rad_orig_snap"):
        D._rad_orig_snap = D.snap
    D.snap = D._rad_orig_snap if get(win, "snap") else (lambda v: int(round(v)))
    from .. import theme as T
    t = T.current()
    views = [view] if view is not None else list(win.findChildren(D.DesignerView))
    for v in views:
        try:
            content = getattr(v, "content", None)
            if content is not None:
                content.setObjectName("radDesignerContent")
                content.setStyleSheet(f"QWidget#radDesignerContent {{ background: {t['designer_back']}; }}")
            # the form itself always looks like the real (light) program
            for part in ("frame", "tray"):
                w = getattr(v, part, None)
                if w is not None:
                    w.setPalette(light_palette())
            if hasattr(v, "surface"):
                v.surface.update()
            v._rad_options = _generation(win)
        except Exception as ex:  # noqa: BLE001
            win.log(f"[options] designer: {ex}")


def apply_theme(win):
    """Palette + application style sheet + every themed part of the main window."""
    from .. import theme as T
    T.apply(get(win, "theme"))
    t = T.current()
    win.setStyleSheet("")                  # the app-wide sheet (theme.APP_STYLE) does the chrome
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    size = max(7, min(16, get(win, "ui_font_size")))
    if app is not None and app.font().pointSize() != size:
        f = app.font()
        f.setPointSize(size)
        app.setFont(f)
    mono = f"QPlainTextEdit {{ background: {t['base']}; color: {t['text']}; }}"
    for name in ("output", "immediate"):
        w = getattr(win, name, None)
        if w is not None and hasattr(w, "setStyleSheet"):
            w.setStyleSheet(mono)
    try:                                   # Properties window: category rows + description box
        from .. import properties as P
        if hasattr(P, "CATEGORY_BACK"):
            P.CATEGORY_BACK = t["category_back"]
        props = getattr(win, "properties", None)
        help_box = getattr(props, "help", None)
        if help_box is not None:
            help_box.setStyleSheet("")
            T.role(help_box, "help")
        if props is not None and hasattr(props, "refresh"):
            props.refresh()
    except Exception as ex:  # noqa: BLE001
        win.log(f"[options] properties: {ex}")
    win._rad_theme = T.current_name()


def _follow_system(win):
    """Windows switched light/dark while the 'System' theme is chosen: re-theme editors etc."""
    from .. import theme as T
    if getattr(win, "_rad_following", False):      # apply_all() itself emits theme.changed: no recursion
        return
    if get(win, "theme") == "System" and getattr(win, "_rad_theme", None) != T.current_name():
        win._rad_following = True
        try:
            apply_all(win)
        finally:
            win._rad_following = False


def apply_autosave(win):
    t = getattr(win, "_autosave", None)
    if t is None:
        return
    sec = get(win, "autosave_seconds")
    if sec <= 0:
        t.stop()
    else:
        t.setInterval(sec * 1000)
        t.start()


def _generation(win) -> int:
    return getattr(win, "_rad_options_gen", 0)


def apply_all(win):
    win._rad_options_gen = _generation(win) + 1
    for fn in (apply_theme, apply_editor, apply_designer, apply_autosave):
        try:
            fn(win)
        except Exception as ex:  # noqa: BLE001
            win.log(f"[options] {fn.__name__}: {ex}")


def _on_tab_changed(win, *_):
    """New editors / designers opened after the options were applied get them too."""
    from .. import designer as D
    from .. import editor as E
    gen = _generation(win)
    if gen == 0:
        return
    widgets = win.findChildren(QWidget)     # one search per tab switch (it was three, ~0.1-0.4 s together)
    for e in _editors(win, widgets):
        if getattr(e, "_rad_options", -1) != gen:
            if isinstance(e, E.CodeEditor) or hasattr(e, "_js"):
                apply_editor(win, e)
    for v in [w for w in widgets if isinstance(w, D.DesignerView)]:
        if getattr(v, "_rad_options", -1) != gen:
            apply_designer(win, v)


# ===================================================================== dialog
def _section(title: str) -> QLabel:
    lbl = QLabel(title)
    lbl.setStyleSheet("font-weight: bold; padding-top: 8px;")
    return lbl


class OptionsDialog(QDialog):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("Options")
        self.resize(680, 520)
        tabs = QTabWidget()

        # Environment
        env = QWidget()
        f = QFormLayout(env)
        self.theme = QComboBox()
        from .. import theme as T
        self.theme.addItems(T.THEME_NAMES)
        self.theme.setCurrentText(get(win, "theme"))
        f.addRow("Color theme:", self.theme)
        self.layout_mode = QComboBox()
        for mode, title in LAYOUTS:
            self.layout_mode.addItem(title, mode)
        wb = getattr(win, "workbench", None)
        cur = getattr(wb, "mode", None) or str(win.settings.value("workbench/mode", "vs") or "vs")
        self.layout_mode.setCurrentIndex(max(0, self.layout_mode.findData(cur)))
        self.layout_mode.setToolTip("Visual Studio: menus, tool bars and docked windows. VS Code: Activity Bar, "
                                    "Side Bar and Panel. Agent: the AI Agent Manager is the main surface.")
        f.addRow("Workbench layout:", self.layout_mode)
        self.ui_font = QSpinBox()
        self.ui_font.setRange(7, 16)
        self.ui_font.setSuffix(" pt")
        self.ui_font.setValue(get(win, "ui_font_size"))
        f.addRow("Menu and window font size:", self.ui_font)
        from .ui_language import language_combo           # English / Arabic (radide/i18n)
        self.ui_lang = language_combo(win)
        f.addRow("Language:", self.ui_lang)
        f.addRow(_section("Start-up and closing"))
        self.show_start = QCheckBox("Show the Start Page on startup")
        self.show_start.setChecked(get(win, "show_start_page"))
        f.addRow(self.show_start)
        self.reopen = QCheckBox("Reopen the last solution on startup")
        self.reopen.setChecked(get(win, "reopen_last"))
        f.addRow(self.reopen)
        self.confirm = QCheckBox("Ask before closing with unsaved changes (otherwise they are saved)")
        self.confirm.setChecked(get(win, "confirm_unsaved"))
        f.addRow(self.confirm)
        f.addRow(_section("Backups"))
        self.autosave = QSpinBox()
        self.autosave.setRange(0, 3600)
        self.autosave.setSuffix(" s")
        self.autosave.setSpecialValueText("Off")
        self.autosave.setValue(get(win, "autosave_seconds"))
        f.addRow("Auto-save backup every:", self.autosave)
        note = QLabel("Auto-save writes unsaved editor contents to the project's .radide_backup folder "
                      "(crash recovery); your files are only written by Save.")
        note.setWordWrap(True)
        T.role(note, "muted")
        f.addRow(note)
        self._env_applies = []
        try:                       # Windows integration (radide/features/shell_integration_ui.py)
            from .shell_integration_ui import windows_group
            grp = windows_group(self)
            if grp is not None:
                f.addRow(grp[0])
                self._env_applies.append(grp[1])
        except Exception as ex:  # noqa: BLE001 - never break Options
            win.log(f"[options] Windows integration: {ex}")
        tabs.addTab(env, "Environment")

        # Editor
        ed = QWidget()
        f = QFormLayout(ed)
        self.font = QFontComboBox()
        self.font.setFontFilters(QFontComboBox.FontFilter.MonospacedFonts)
        self.font.setCurrentFont(QFont(get(win, "editor_font")))
        f.addRow("Font:", self.font)
        self.size = QSpinBox()
        self.size.setRange(6, 48)
        self.size.setValue(get(win, "editor_font_size"))
        f.addRow("Size:", self.size)
        self.tab = QSpinBox()
        self.tab.setRange(1, 16)
        self.tab.setValue(get(win, "tab_width"))
        f.addRow("Tab / indent width:", self.tab)
        self.sample = QLabel("def Form1_Load(self):\n    return 42  # sample")
        from .. import theme as T
        T.role(self.sample, "sample")
        f.addRow("Preview:", self.sample)
        self.font.currentFontChanged.connect(lambda _f: self._preview())
        self.size.valueChanged.connect(lambda _v: self._preview())
        self._preview()
        tabs.addTab(ed, "Text Editor")

        # Designer
        de = QWidget()
        f = QFormLayout(de)
        self.grid = QSpinBox()
        self.grid.setRange(2, 64)
        self.grid.setSuffix(" px")
        self.grid.setValue(get(win, "grid_size"))
        f.addRow("Grid size:", self.grid)
        self.snap = QCheckBox("Snap controls to the grid")
        self.snap.setChecked(get(win, "snap"))
        f.addRow(self.snap)
        tabs.addTab(de, "Windows Forms Designer")

        # Languages
        from ..languages import all_plugins
        lw = QWidget()
        grid = QGridLayout(lw)
        grid.addWidget(QLabel("<b>Interpreter / compiler used to run each language</b> "
                              "(empty = detect automatically)"), 0, 0, 1, 3)
        self.interp: dict[str, QLineEdit] = {}
        for row, p in enumerate(sorted(all_plugins(), key=lambda p: p.display_name), 1):
            edit = QLineEdit(win.settings.value(f"interpreter/{p.id}", "") or "")
            try:
                auto = p.find_interpreter("")
            except Exception:  # noqa: BLE001
                auto = ""
            edit.setPlaceholderText(auto or "(not found)")
            b = QPushButton("...")
            b.setFixedWidth(30)
            b.clicked.connect(lambda _=False, e=edit, n=p.display_name: self._browse(e, n))
            grid.addWidget(QLabel(p.display_name), row, 0)
            grid.addWidget(edit, row, 1)
            grid.addWidget(b, row, 2)
            self.interp[p.id] = edit
        grid.setRowStretch(len(self.interp) + 1, 1)
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setWidget(lw)
        tabs.addTab(sa, "Languages")

        self._page_applies = list(getattr(self, "_env_applies", []))
        for hook in PAGE_HOOKS:
            try:
                page = hook(self)
            except Exception as ex:  # noqa: BLE001 - a broken page must not break Options
                win.log(f"[options] page failed: {ex}")
                continue
            if page:
                tabs.addTab(page[0], page[1])
                self._page_applies.append(page[2])

        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel |
                               QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.RestoreDefaults)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply)
        box.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(self.restore_defaults)
        lay = QVBoxLayout(self)
        lay.addWidget(tabs, 1)
        lay.addWidget(box)

    def _preview(self):
        f = QFont(self.font.currentFont().family(), self.size.value())
        self.sample.setFont(f)

    def _browse(self, edit, name):
        f, _ = QFileDialog.getOpenFileName(self, f"Locate {name} interpreter", edit.text(),
                                           "Programs (*.exe *.cmd *.bat);;All files (*)")
        if f:
            edit.setText(f)

    def restore_defaults(self):
        self.theme.setCurrentText(DEFAULTS["theme"])
        self.layout_mode.setCurrentIndex(0)
        self.ui_font.setValue(DEFAULTS["ui_font_size"])
        self.show_start.setChecked(DEFAULTS["show_start_page"])
        self.reopen.setChecked(DEFAULTS["reopen_last"])
        self.confirm.setChecked(DEFAULTS["confirm_unsaved"])
        self.autosave.setValue(DEFAULTS["autosave_seconds"])
        self.font.setCurrentFont(QFont(DEFAULTS["editor_font"]))
        self.size.setValue(DEFAULTS["editor_font_size"])
        self.tab.setValue(DEFAULTS["tab_width"])
        self.grid.setValue(DEFAULTS["grid_size"])
        self.snap.setChecked(DEFAULTS["snap"])

    def apply(self):
        s = self.win.settings
        s.setValue(KEY + "theme", self.theme.currentText())
        s.setValue(KEY + "ui_font_size", self.ui_font.value())
        s.setValue(KEY + "show_start_page", self.show_start.isChecked())
        s.setValue(KEY + "reopen_last", self.reopen.isChecked())
        s.setValue(KEY + "confirm_unsaved", self.confirm.isChecked())
        s.setValue(KEY + "autosave_seconds", self.autosave.value())
        s.setValue(KEY + "editor_font", self.font.currentFont().family())
        s.setValue(KEY + "editor_font_size", self.size.value())
        s.setValue(KEY + "tab_width", self.tab.value())
        s.setValue(KEY + "grid_size", self.grid.value())
        s.setValue(KEY + "snap", self.snap.isChecked())
        for pid, edit in self.interp.items():
            path = edit.text().strip().strip('"')
            if path:
                s.setValue(f"interpreter/{pid}", path)
            else:
                s.remove(f"interpreter/{pid}")
        s.sync()
        for fn in getattr(self, "_page_applies", []):
            try:
                fn()
            except Exception as ex:  # noqa: BLE001
                self.win.log(f"[options] page apply failed: {ex}")
        apply_all(self.win)
        self._apply_layout()
        from .ui_language import apply_language
        apply_language(self.win, self.ui_lang.currentData())

    def _apply_layout(self):
        mode = self.layout_mode.currentData()
        wb = getattr(self.win, "workbench", None)
        if wb is not None and hasattr(wb, "set_mode"):
            if getattr(wb, "mode", None) != mode:
                wb.set_mode(mode)
        else:
            self.win.settings.setValue("workbench/mode", mode)

    def accept(self):
        self.apply()
        super().accept()


def show_options(win):
    dlg = OptionsDialog(win)
    win._options_dialog = dlg
    dlg.exec()


def install(win) -> None:
    tools = next((a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == "Tools"), None)
    if tools is not None:
        tools.addSeparator()
        a = tools.addAction("&Options...", lambda: show_options(win))
        a.setMenuRole(a.MenuRole.PreferencesRole)
        win.a_options = a
    win.tabs.currentChanged.connect(lambda *_: _on_tab_changed(win))
    # always apply at start-up: the theme must be explicit (never Qt's palette that follows Windows)
    apply_all(win)
    from .. import theme as T
    from PyQt6 import sip           # a closed (deleted) window must not be re-themed
    T.changed.connect(lambda _n: None if sip.isdeleted(win) else _follow_system(win))


__all__ = ["OptionsDialog", "show_options", "apply_all", "get", "dark_palette", "DEFAULTS"]
