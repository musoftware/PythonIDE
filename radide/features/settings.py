"""Tools > Options: editor font / size / tab width, Light or Dark theme,
designer grid size and snap, interpreter path per language, auto-save interval.
Everything is stored in the IDE's QSettings and applied live."""
from __future__ import annotations

import json

from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPalette
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                             QFontComboBox, QFormLayout, QGridLayout, QLabel, QLineEdit,
                             QPushButton, QScrollArea, QSpinBox, QTabWidget, QVBoxLayout, QWidget)

DEFAULTS = {"theme": "Light", "editor_font": "Consolas", "editor_font_size": 10, "tab_width": 4,
            "grid_size": 8, "snap": True, "autosave_seconds": 60}
KEY = "options/"

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
    app = QApplication.instance()
    return app.style().standardPalette()


# ===================================================================== apply
def _editors(win):
    from .. import editor as E
    out = list(win.findChildren(E.CodeEditor))
    for w in win.findChildren(QWidget):
        if type(w).__name__ == "MonacoEditor" and hasattr(w, "_js"):
            out.append(w)
    return out


def apply_editor(win, ed=None):
    from .. import editor as E
    family, size, tab = get(win, "editor_font"), get(win, "editor_font_size"), get(win, "tab_width")
    theme = get(win, "theme")
    E.FONT.setFamily(family)
    E.FONT.setPointSize(size)
    E.INDENT = " " * max(1, tab)
    code, chrome = (DARK_CODE, DARK_CHROME) if theme == "Dark" else (LIGHT_CODE, LIGHT_CHROME)
    E.COLORS.update(code)
    if hasattr(E, "EDITOR_THEME"):
        E.EDITOR_THEME.update(chrome)
    for e in ([ed] if ed is not None else _editors(win)):
        try:
            if hasattr(e, "_js") and not isinstance(e, E.CodeEditor):
                e._js(f"radSetFont({json.dumps(family)}, {int(size) + 3});"
                      f"radSetTheme({'true' if theme == 'Dark' else 'false'});"
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
                e.calltip_label.setStyleSheet(CALLTIP.get(theme, CALLTIP["Light"]))
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
    theme = get(win, "theme")
    views = [view] if view is not None else list(win.findChildren(D.DesignerView))
    for v in views:
        try:
            content = getattr(v, "content", None)
            if content is not None:
                if theme == "Dark":
                    content.setObjectName("radDesignerContent")
                    content.setStyleSheet(f"QWidget#radDesignerContent {{ background: {DESIGNER_BACK['Dark']}; }}")
                elif content.objectName() == "radDesignerContent":
                    content.setStyleSheet("background:#ffffff;")     # the designer's own default
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
    from .. import app as A
    app = QApplication.instance()
    theme = get(win, "theme")
    if theme == "Dark":
        app.setPalette(dark_palette())
        win.setStyleSheet(DARK_STYLE)
        out_style = "QPlainTextEdit { background: #1E1E1E; color: #D4D4D4; }"
    else:
        app.setPalette(light_palette())
        win.setStyleSheet(getattr(A, "STYLE", ""))
        out_style = ""
    for name in ("output", "immediate"):
        w = getattr(win, name, None)
        if w is not None and hasattr(w, "setStyleSheet"):
            w.setStyleSheet(out_style)
    try:                                   # Properties window: category rows + description box
        from .. import properties as P
        if hasattr(P, "CATEGORY_BACK"):
            P.CATEGORY_BACK = "#3F3F46" if theme == "Dark" else "#E4E8EE"
        props = getattr(win, "properties", None)
        help_box = getattr(props, "help", None)
        if help_box is not None:
            help_box.setStyleSheet("padding:4px; background:#252526; color:#D4D4D4; border-top:1px solid #3F3F46;"
                                   if theme == "Dark" else
                                   "padding:4px; background:#f4f4f4; border-top:1px solid #ccc;")
        if props is not None and hasattr(props, "refresh"):
            props.refresh()
    except Exception as ex:  # noqa: BLE001
        win.log(f"[options] properties: {ex}")
    win._rad_theme = theme


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
    for e in _editors(win):
        if getattr(e, "_rad_options", -1) != gen:
            if isinstance(e, E.CodeEditor) or hasattr(e, "_js"):
                apply_editor(win, e)
    for v in win.findChildren(D.DesignerView):
        if getattr(v, "_rad_options", -1) != gen:
            apply_designer(win, v)


# ===================================================================== dialog
class OptionsDialog(QDialog):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("Options")
        self.resize(620, 460)
        tabs = QTabWidget()

        # Environment
        env = QWidget()
        f = QFormLayout(env)
        self.theme = QComboBox()
        self.theme.addItems(["Light", "Dark"])
        self.theme.setCurrentText(get(win, "theme"))
        f.addRow("Color theme:", self.theme)
        self.autosave = QSpinBox()
        self.autosave.setRange(0, 3600)
        self.autosave.setSuffix(" s")
        self.autosave.setSpecialValueText("Off")
        self.autosave.setValue(get(win, "autosave_seconds"))
        f.addRow("Auto-save backup every:", self.autosave)
        f.addRow(QLabel("<small>Auto-save writes unsaved editor contents to the project's .radide_backup folder "
                        "(crash recovery); your files are only written by Save.</small>"))
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
        self.sample.setStyleSheet("border:1px solid #999; padding:6px;")
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
        self.autosave.setValue(DEFAULTS["autosave_seconds"])
        self.font.setCurrentFont(QFont(DEFAULTS["editor_font"]))
        self.size.setValue(DEFAULTS["editor_font_size"])
        self.tab.setValue(DEFAULTS["tab_width"])
        self.grid.setValue(DEFAULTS["grid_size"])
        self.snap.setChecked(DEFAULTS["snap"])

    def apply(self):
        s = self.win.settings
        s.setValue(KEY + "theme", self.theme.currentText())
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
        apply_all(self.win)

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
    # apply saved options at start-up (only when something differs from the defaults)
    if any(win.settings.contains(KEY + k) for k in DEFAULTS):
        apply_all(win)


__all__ = ["OptionsDialog", "show_options", "apply_all", "get", "dark_palette", "DEFAULTS"]
