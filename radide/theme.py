"""IDE colour themes (Tools > Options > Environment > Color theme).

One place that decides every colour of the IDE chrome:
  * a complete QPalette (never Qt's standard palette, which follows Windows' dark mode and
    produced the half-dark / half-light look),
  * one application style sheet (docks, tabs, menus, tool bars, status bar, headers, tool tips),
  * semantic roles for small widgets:  theme.role(label, "muted")  instead of hard-coded "#555",
  * the matching Monaco theme and code colours,
  * a `changed` signal so web views (Monaco, Design View, SuperPreview ...) follow live.

Themes: System (follows Windows light/dark, live), Light (Visual Studio 2005), Blue (VS 2010),
Dark (VS dark), High Contrast.  The forms being designed always keep the light look of a real
Windows program - see FORM_STYLE.
"""
from __future__ import annotations

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication, QWidget

THEME_NAMES = ["System", "Light", "Blue", "Dark", "High Contrast"]

_CODE_LIGHT = {"keyword": "#0000FF", "builtin": "#2B91AF", "comment": "#008000", "string": "#A31515",
               "number": "#098658", "decorator": "#795E26", "defname": "#795E26", "operator": "#000000"}
_CODE_DARK = {"keyword": "#569CD6", "builtin": "#4EC9B0", "comment": "#6A9955", "string": "#CE9178",
              "number": "#B5CEA8", "decorator": "#DCDCAA", "defname": "#DCDCAA", "operator": "#D4D4D4"}
_CODE_HC = {"keyword": "#569CD6", "builtin": "#4EC9B0", "comment": "#7CA668", "string": "#CE9178",
            "number": "#B5CEA8", "decorator": "#FFFF00", "defname": "#FFFF00", "operator": "#FFFFFF"}

_CHROME_LIGHT = {"margin": "#F3F3F3", "margin_bp": "#E6E6E6", "line_number": "#2B91AF",
                 "breakpoint_line": "#F7D9D6", "current_stmt": "#FFF3A0", "caret_line": "#EEF4FF"}
_CHROME_DARK = {"margin": "#1E1E1E", "margin_bp": "#252526", "line_number": "#858585",
                "breakpoint_line": "#5A1D1D", "current_stmt": "#4B4B18", "caret_line": "#2A2D2E"}
_CHROME_HC = {"margin": "#000000", "margin_bp": "#000000", "line_number": "#FFFFFF",
              "breakpoint_line": "#6F0000", "current_stmt": "#5C5C00", "caret_line": "#1A1A1A"}

# token -> colour.  Every theme defines every token (checked by _complete()).
THEMES: dict[str, dict] = {
    "Light": dict(
        dark=False, monaco="vs", code=_CODE_LIGHT, chrome=_CHROME_LIGHT,
        window="#F0F0EA", base="#FFFFFF", alt_base="#F5F5F0", text="#000000", muted="#5A5A5A",
        button="#ECECE6", button_text="#000000", border="#A0AFC3", light="#FFFFFF", mid="#B8B8B0",
        dark_c="#808080", shadow="#404040",
        highlight="#316AC5", highlight_text="#FFFFFF", link="#0645AD", link_visited="#5A3696",
        accent="#316AC5", accent_text="#FFFFFF",
        title1="#F6F7F9", title2="#D8DFEA", title_text="#000000",
        toolbar1="#FAFAFA", toolbar2="#E3E3DC", toolbar_border="#C0C0B8", bar_text="#000000",
        menu="#FAFAF7", menu_text="#000000", menu_sel="#C1D2EE", menu_sel_text="#000000", menu_border="#8A8A8A",
        tab="#E4E4DE", tab_text="#333333", tab_sel="#FFFFFF", tab_sel_text="#000000", tab_hover="#F4F4F0",
        status="#E8E8E2", status_text="#000000",
        header="#EBEBE5", header_text="#000000",
        tooltip="#FFFFE1", tooltip_text="#000000",
        calltip="#FFFFE1", calltip_text="#000000",
        note="#806000", banner="#FFF4CE", banner_text="#5C4400", banner_border="#E0C080",
        success="#087F23", error="#C42B1C", info_back="#F7F8FA",
        designer_back="#FFFFFF", category_back="#E4E8EE", stage="#3A3D44", heading="#1F3D7A",
        disabled="#8A8A8A", placeholder="#8A8A8A",
    ),
    "Blue": dict(
        dark=False, monaco="vs", code=_CODE_LIGHT, chrome=_CHROME_LIGHT,
        window="#293955", base="#FFFFFF", alt_base="#F3F6FB", text="#000000", muted="#4A5568",
        button="#E9EEF6", button_text="#000000", border="#8E9BBC", light="#FFFFFF", mid="#B4C0D8",
        dark_c="#6D7A99", shadow="#1B2738",
        highlight="#3399FF", highlight_text="#FFFFFF", link="#0E5AA7", link_visited="#5A3696",
        accent="#FFE8A6", accent_text="#000000",
        title1="#4D6082", title2="#3B4F71", title_text="#FFFFFF",
        toolbar1="#BCC7D8", toolbar2="#9FAEC7", toolbar_border="#8E9BBC", bar_text="#000000",
        menu="#EAF0F8", menu_text="#000000", menu_sel="#FFE8A6", menu_sel_text="#000000", menu_border="#9BA7B7",
        tab="#4D6082", tab_text="#FFFFFF", tab_sel="#FFE8A6", tab_sel_text="#000000", tab_hover="#5B7199",
        status="#007ACC", status_text="#FFFFFF",
        header="#DDE4EE", header_text="#000000",
        tooltip="#FFFFE1", tooltip_text="#000000",
        calltip="#FFFFE1", calltip_text="#000000",
        note="#806000", banner="#FFF4CE", banner_text="#5C4400", banner_border="#E0C080",
        success="#087F23", error="#C42B1C", info_back="#F3F6FB",
        designer_back="#FFFFFF", category_back="#DDE4EE", stage="#3A3D44", heading="#1F3D7A",
        disabled="#8A8A8A", placeholder="#8A8A8A",
    ),
    "Dark": dict(
        dark=True, monaco="vs-dark", code=_CODE_DARK, chrome=_CHROME_DARK,
        window="#2D2D30", base="#1E1E1E", alt_base="#252526", text="#D4D4D4", muted="#A0A0A0",
        button="#3C3C3C", button_text="#F1F1F1", border="#3F3F46", light="#505050", mid="#333337",
        dark_c="#1B1B1C", shadow="#000000",
        highlight="#264F78", highlight_text="#FFFFFF", link="#3794FF", link_visited="#C586C0",
        accent="#007ACC", accent_text="#FFFFFF",
        title1="#3F3F46", title2="#3F3F46", title_text="#F1F1F1",
        toolbar1="#333337", toolbar2="#333337", toolbar_border="#3F3F46", bar_text="#F1F1F1",
        menu="#1B1B1C", menu_text="#F1F1F1", menu_sel="#3E3E40", menu_sel_text="#FFFFFF", menu_border="#333337",
        tab="#2D2D30", tab_text="#D0D0D0", tab_sel="#1E1E1E", tab_sel_text="#FFFFFF", tab_hover="#3E3E42",
        status="#007ACC", status_text="#FFFFFF",
        header="#333337", header_text="#D0D0D0",
        tooltip="#252526", tooltip_text="#F1F1F1",
        calltip="#252526", calltip_text="#D4D4D4",
        note="#E0B050", banner="#4B3E12", banner_text="#F5E3A8", banner_border="#7A6420",
        success="#6CCB5F", error="#F48771", info_back="#252526",
        designer_back="#252526", category_back="#3F3F46", stage="#1B1B1C", heading="#9CDCFE",
        disabled="#6D6D6D", placeholder="#8A8A8A",
    ),
    "High Contrast": dict(
        dark=True, monaco="hc-black", code=_CODE_HC, chrome=_CHROME_HC,
        window="#000000", base="#000000", alt_base="#0A0A0A", text="#FFFFFF", muted="#FFFFFF",
        button="#000000", button_text="#FFFFFF", border="#FFFFFF", light="#FFFFFF", mid="#7F7F7F",
        dark_c="#FFFFFF", shadow="#FFFFFF",
        highlight="#1AEBFF", highlight_text="#000000", link="#FFFF00", link_visited="#FF80FF",
        accent="#1AEBFF", accent_text="#000000",
        title1="#000000", title2="#000000", title_text="#FFFFFF",
        toolbar1="#000000", toolbar2="#000000", toolbar_border="#FFFFFF", bar_text="#FFFFFF",
        menu="#000000", menu_text="#FFFFFF", menu_sel="#1AEBFF", menu_sel_text="#000000", menu_border="#FFFFFF",
        tab="#000000", tab_text="#FFFFFF", tab_sel="#1AEBFF", tab_sel_text="#000000", tab_hover="#333333",
        status="#000000", status_text="#FFFFFF",
        header="#000000", header_text="#FFFFFF",
        tooltip="#000000", tooltip_text="#FFFFFF",
        calltip="#000000", calltip_text="#FFFFFF",
        note="#FFFF00", banner="#000000", banner_text="#FFFF00", banner_border="#FFFF00",
        success="#3FF23F", error="#FF6B6B", info_back="#000000",
        designer_back="#000000", category_back="#333333", stage="#000000", heading="#FFFF00",
        disabled="#A0A0A0", placeholder="#C0C0C0",
    ),
}

# semantic roles for small widgets: theme.role(w, "muted")
ROLE_QSS = {
    "muted": "color: {muted};",
    "note": "color: {note};",
    "success": "color: {success};",
    "error": "color: {error};",
    "link": "color: {link}; text-align: left;",
    "heading": "color: {heading};",
    "banner": "background: {banner}; color: {banner_text}; padding: 4px 8px; border-bottom: 1px solid {banner_border};",
    "info": "padding: 8px; background: {info_back}; color: {text}; border: 1px solid {border};",
    "help": "padding: 4px; background: {alt_base}; color: {text}; border-top: 1px solid {border};",
    "calltip": "background: {calltip}; color: {calltip_text}; border: 1px solid {border}; padding: 3px;",
    "stage": "background: {stage};",
    "sample": "border: 1px solid {border}; padding: 6px;",
}

APP_STYLE = """
QMainWindow, QDockWidget {{ background: {window}; }}
QMainWindow::separator {{ background: {window}; width: 4px; height: 4px; }}
QDockWidget {{ color: {title_text}; }}
QDockWidget::title {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {title1}, stop:1 {title2});
                      color: {title_text}; padding: 4px; border: 1px solid {border}; font-weight: bold; }}
QTabBar::tab {{ background: {tab}; color: {tab_text}; padding: 4px 10px; border: 1px solid {border}; }}
QTabBar::tab:selected {{ background: {tab_sel}; color: {tab_sel_text}; }}
QTabBar::tab:hover:!selected {{ background: {tab_hover}; }}
QTabWidget::pane {{ border: 1px solid {border}; }}
QToolBar {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {toolbar1}, stop:1 {toolbar2});
            border-bottom: 1px solid {toolbar_border}; spacing: 2px; }}
QToolBar QToolButton {{ color: {bar_text}; }}
QToolBar QToolButton:disabled {{ color: {disabled}; }}
QMenuBar {{ background: {toolbar1}; color: {bar_text}; }}
QMenuBar::item {{ background: transparent; padding: 3px 8px; }}
QMenuBar::item:selected {{ background: {menu_sel}; color: {menu_sel_text}; }}
QMenu {{ background: {menu}; color: {menu_text}; border: 1px solid {menu_border}; }}
QMenu::item {{ padding: 4px 24px 4px 24px; }}
QMenu::item:selected {{ background: {menu_sel}; color: {menu_sel_text}; }}
QMenu::item:disabled {{ color: {disabled}; }}
QMenu::separator {{ height: 1px; background: {border}; margin: 3px 6px; }}
QStatusBar {{ background: {status}; color: {status_text}; }}
QStatusBar QLabel {{ color: {status_text}; }}
QStatusBar::item {{ border: none; }}
QStatusBar QToolButton {{ color: {status_text}; padding: 0px 6px; }}
QStatusBar QToolButton::menu-indicator {{ image: none; width: 0px; }}
QHeaderView::section {{ background: {header}; color: {header_text}; border: 0;
                        border-right: 1px solid {border}; border-bottom: 1px solid {border}; padding: 3px; }}
QToolTip {{ background: {tooltip}; color: {tooltip_text}; border: 1px solid {border}; }}
"""

# The form being designed (and its component tray) must look like the real light Windows program,
# whatever the IDE theme: these rules override APP_STYLE inside the designer surface.
FORM_STYLE = """
QTabBar::tab { background: #F0F0F0; color: #000000; padding: 3px 8px; border: 1px solid #ADADAD; }
QTabBar::tab:selected { background: #FFFFFF; color: #000000; }
QTabWidget::pane { border: 1px solid #ADADAD; }
QHeaderView::section { background: #F0F0F0; color: #000000; border: 0; border-right: 1px solid #D0D0D0;
                       border-bottom: 1px solid #D0D0D0; padding: 2px; }
QToolBar { background: #F0F0F0; border-bottom: 1px solid #D0D0D0; }
QStatusBar { background: #F0F0F0; color: #000000; }
QMenuBar { background: #FFFFFF; color: #000000; }
"""


def _complete() -> None:
    keys = set(THEMES["Light"])
    for name, t in THEMES.items():
        missing = keys - set(t)
        if missing:
            raise KeyError(f"theme {name!r} misses {sorted(missing)}")


_complete()

BUILTIN_THEMES = ("System", "Light", "Blue", "Dark", "High Contrast")


def add_theme(name: str, t: dict, base: str | None = None) -> str:
    """Add (or replace) a colour theme at run time (VS Code colour themes: radide/vsx/contrib_themes.py).
    Tokens missing from *t* come from *base* (default: Dark for dark themes, else Light); the name then
    appears in Tools > Options > Color theme. Built-in names cannot be replaced."""
    if name in BUILTIN_THEMES:
        raise ValueError(f"'{name}' is a built-in theme name")
    import copy
    base = base if base in THEMES else ("Dark" if t.get("dark") else "Light")
    full = copy.deepcopy(THEMES[base])
    for part in ("code", "chrome"):
        if isinstance(t.get(part), dict):
            full[part] = dict(full[part], **t[part])
    full.update({k: v for k, v in t.items() if k not in ("code", "chrome")})
    THEMES[name] = full
    if name not in THEME_NAMES:
        THEME_NAMES.append(name)
    return name


def remove_theme(name: str) -> None:
    """Remove a theme added with add_theme (the IDE falls back to Light when it was in use)."""
    if name in BUILTIN_THEMES or name not in THEMES:
        return
    was_current = _manager.name == name
    THEMES.pop(name, None)
    if name in THEME_NAMES:
        THEME_NAMES.remove(name)
    if was_current:
        _manager.apply("Light")


def system_is_dark() -> bool:
    app = QApplication.instance()
    try:
        return app is not None and app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:
        return False


def resolve(name: str) -> str:
    """'System' -> 'Dark' or 'Light'; unknown names -> 'Light'."""
    if name == "System":
        return "Dark" if _manager.system_dark else "Light"
    return name if name in THEMES else "Light"


def palette_for(t: dict) -> QPalette:
    p = QPalette()
    R, G = QPalette.ColorRole, QPalette.ColorGroup
    pairs = ((R.Window, "window"), (R.WindowText, "text"), (R.Base, "base"), (R.AlternateBase, "alt_base"),
             (R.ToolTipBase, "tooltip"), (R.ToolTipText, "tooltip_text"), (R.Text, "text"),
             (R.Button, "button"), (R.ButtonText, "button_text"), (R.BrightText, "error"),
             (R.Highlight, "highlight"), (R.HighlightedText, "highlight_text"), (R.Link, "link"),
             (R.LinkVisited, "link_visited"), (R.PlaceholderText, "placeholder"), (R.Light, "light"),
             (R.Midlight, "mid"), (R.Mid, "mid"), (R.Dark, "dark_c"), (R.Shadow, "shadow"),
             (R.Accent, "highlight"))
    for role, key in pairs:
        p.setColor(role, QColor(t[key]))
    # the Window colour of the "Blue" theme is the dark-blue frame; the text on plain dialog
    # surfaces (which also use Window) must stay readable, so Blue dialogs use a light window.
    if t is THEMES["Blue"]:
        p.setColor(R.Window, QColor("#E9EEF6"))
        p.setColor(R.WindowText, QColor("#000000"))
    for role in (R.WindowText, R.Text, R.ButtonText):
        p.setColor(G.Disabled, role, QColor(t["disabled"]))
    p.setColor(G.Disabled, R.Base, QColor(t["alt_base"]))
    return p


_LIGHT_FORM_PALETTE: list = [None, None]      # (theme values, palette): every designer preview asks for it


def light_form_palette() -> QPalette:
    """The palette of a real (light) Windows program - for the form designer surface."""
    t = THEMES["Light"]
    key = tuple(sorted((k, str(v)) for k, v in t.items()))
    if _LIGHT_FORM_PALETTE[0] != key:
        _LIGHT_FORM_PALETTE[:] = [key, palette_for(t)]
    return QPalette(_LIGHT_FORM_PALETTE[1])        # a copy: callers may change theirs


class _Manager(QObject):
    changed = pyqtSignal(str)          # resolved theme name

    def __init__(self):
        super().__init__()
        self.setting = "Light"
        self.name = "Light"
        self.system_dark = False
        self._hooked = False

    # ---------------------------------------------------------------- public
    @property
    def t(self) -> dict:
        return THEMES[self.name]

    def apply(self, setting: str) -> str:
        app = QApplication.instance()
        self.setting = setting if setting in THEME_NAMES else "Light"
        if app is not None and not self._hooked:
            self._hooked = True
            try:
                # read the real Windows scheme once, before we pin the scheme ourselves
                self.system_dark = system_is_dark()
                app.styleHints().colorSchemeChanged.connect(self._on_system_scheme)
            except AttributeError:
                pass
        self.name = resolve(self.setting)
        t = self.t
        if app is not None:
            st = app.style()
            base = st.name().lower()
            if not base and st.metaObject().className() == "QStyleSheetStyle":
                # with the application style sheet set, app.style() is Qt's style-sheet proxy (name ""):
                # its base is the style checked here last time - setting Fusion again re-polished every
                # widget (~1.7 s at start-up and on each theme change)
                base = str(app.property("radBaseStyle") or "")
            if base != "fusion":
                app.setStyle("Fusion")        # the only style that honours the whole palette
            app.setProperty("radBaseStyle", "fusion")
            try:      # tells Qt widgets and web pages (prefers-color-scheme) the same thing
                self._pinning = True
                app.styleHints().setColorScheme(Qt.ColorScheme.Dark if t["dark"] else Qt.ColorScheme.Light)
            except AttributeError:
                pass
            finally:
                self._pinning = False
            app.setPalette(palette_for(t))
            sheet = stylesheet(t)
            if app.styleSheet() != sheet:     # the same sheet again re-polishes every widget (~2 s at start-up)
                app.setStyleSheet(sheet)
        self.changed.emit(self.name)
        return self.name

    # ---------------------------------------------------------------- system follow
    _pinning = False

    def _on_system_scheme(self, scheme):
        if self._pinning:
            return
        self.system_dark = scheme == Qt.ColorScheme.Dark
        if self.setting == "System" and resolve("System") != self.name:
            self.apply("System")


_manager = _Manager()
changed = _manager.changed


def manager() -> _Manager:
    return _manager


def apply(setting: str) -> str:
    return _manager.apply(setting)


def current() -> dict:
    return _manager.t


def current_name() -> str:
    return _manager.name


def is_dark() -> bool:
    return bool(_manager.t["dark"])


def color(token: str) -> str:
    return _manager.t[token]


def monaco_theme() -> str:
    return _manager.t["monaco"]


def stylesheet(t: dict | None = None) -> str:
    t = t or _manager.t
    out = APP_STYLE.format(**t)
    # the designed form keeps the light Windows look: the same rules scoped to the designer frame
    import re
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", FORM_STYLE):
        scoped = ", ".join(f"FormFrame {s.strip()}" for s in sel.split(","))
        out += f"\n{scoped} {{{' '.join(body.split())}}}"
    for role, rule in ROLE_QSS.items():
        out += f'\n*[radRole="{role}"] {{ {rule.format(**t)} }}'
    return out


def role(widget: QWidget, name: str) -> QWidget:
    """Give a small widget a semantic colour role (muted, note, success, error, link, heading,
    banner, info, help, calltip, stage, sample).  It follows theme changes automatically."""
    if name not in ROLE_QSS:
        raise KeyError(name)
    widget.setProperty("radRole", name)
    st = widget.style()
    if st is not None:
        st.unpolish(widget)
        st.polish(widget)
    return widget


def css_vars(t: dict | None = None) -> str:
    """CSS custom properties for HTML pages hosted in the IDE (help, reports, design view chrome)."""
    t = t or _manager.t
    keys = ("window", "base", "alt_base", "text", "muted", "border", "accent", "accent_text", "link",
            "highlight", "highlight_text", "error", "success", "note", "header", "header_text")
    body = "; ".join(f"--rad-{k.replace('_', '-')}: {t[k]}" for k in keys)
    return f":root {{ {body}; color-scheme: {'dark' if t['dark'] else 'light'}; }}"


__all__ = ["THEME_NAMES", "THEMES", "FORM_STYLE", "apply", "current", "current_name", "is_dark", "color",
           "monaco_theme", "stylesheet", "role", "css_vars", "changed", "manager", "light_form_palette",
           "palette_for", "resolve", "system_is_dark", "add_theme", "remove_theme", "BUILTIN_THEMES"]
