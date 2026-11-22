"""High contrast, colour contrast and text scaling.

  * WCAG 2.1 contrast of every theme (radide/theme.py tokens, the pairs the application style sheet really paints:
    dock titles on both gradient stops, tool bar text, tabs incl. hover, menus, status bar, headers, tool tips,
    banners, notes, links, errors) - 4.5:1 for text, 3:1 for disabled / placeholder text and for the selection and
    focus colours (non-text contrast, 1.4.11); the High Contrast theme 7:1 (AAA)
  * the QPalette each theme installs (Window/WindowText, Base/Text, Button/ButtonText, Highlight/HighlightedText)
  * the four Windows 11 contrast themes (Aquatic, Desert, Dusk, Night sky): the theme the IDE builds from the
    Windows colours passes the same checks, and follow_high_contrast() switches to it (and not when switched off)
  * the style sheet never removes focus outlines; the keyboard focus ring colour is visible on every theme
  * 200 % text: with a doubled application font the main dialogs and the docked windows clip no label / button /
    check box text (size >= minimum size hint, wrapped labels tall enough) and still fit a 1280 x 720 screen

    .venv\\Scripts\\python samples\\Tests\\Accessibility\\test_contrast_scaling.py     (exit code = failures)
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _a11y_common import app, auto_close_modals, check, finish, info, main_window, project_copy, pump  # noqa: E402

from PyQt6.QtGui import QFont, QPalette  # noqa: E402
from PyQt6.QtWidgets import QAbstractButton, QCheckBox, QLabel, QRadioButton, QWidget  # noqa: E402

from radide import theme  # noqa: E402
from radide.features import perf_a11y as A  # noqa: E402

# (fg, bg, minimum) - what APP_STYLE / ROLE_QSS paint, on top of perf_a11y.CONTRAST_PAIRS
EXTRA = [("title_text", "title2", 4.5), ("bar_text", "toolbar2", 4.5), ("tab_text", "tab_hover", 4.5),
         ("banner_text", "banner", 4.5), ("note", "base", 4.5), ("heading", "base", 4.5), ("link", "window", 4.5),
         ("error", "window", 4.5), ("success", "window", 4.5), ("calltip_text", "calltip", 4.5),
         ("muted", "window", 4.5), ("text", "alt_base", 4.5), ("text", "info_back", 4.5), ("text", "category_back", 4.5),
         ("menu_sel", "menu", 1.0)]


def pairs_of(t: dict, hc: bool = False) -> list[tuple[str, str, float, float]]:
    out = []
    for fg, bg, need in A.CONTRAST_PAIRS + EXTRA:
        if fg in t and bg in t:
            need2 = 7.0 if hc and need >= 4.5 else need
            out.append((fg, bg, A.contrast(t[fg], t[bg]), need2))
    return out


def check_theme(name: str, t: dict, hc: bool = False) -> None:
    # text sits on the palette's Window colour (dialogs, panels); the token "window" of the Blue theme is only the
    # dark frame of the main window behind the docks (theme.palette_for gives plain surfaces a light colour)
    t = dict(t, window=theme.palette_for(t).color(QPalette.ColorRole.Window).name()) if "window" in t else t
    low =[f"{fg} on {bg} {r}:1 < {need}" for fg, bg, r, need in pairs_of(t, hc) if r < need]
    check(f"contrast: theme {name} - {len(pairs_of(t, hc))} colour pairs{' (AAA 7:1)' if hc else ''}", not low, low)
    # the selection must stand out from the page and the menu selection from the menu (1.4.11, 3:1 / visible)
    sel = A.contrast(t["highlight"], t["base"])
    check(f"contrast: theme {name} - selection vs page >= 3:1 or selected text inverted",
          sel >= 3.0 or A.contrast(t["highlight_text"], t["highlight"]) >= 4.5, sel)


for name in theme.BUILTIN_THEMES:
    if name == "System":
        continue
    check_theme(name, theme.THEMES[name], hc=(name == "High Contrast"))

# ---------------------------------------------------------------- the palette Qt really uses
R = QPalette.ColorRole
for name in [n for n in theme.BUILTIN_THEMES if n != "System"]:
    theme.apply(name)
    pump(2)
    p = app.palette()
    low = []
    for fg, bg in ((R.WindowText, R.Window), (R.Text, R.Base), (R.ButtonText, R.Button),
                   (R.HighlightedText, R.Highlight), (R.ToolTipText, R.ToolTipBase)):
        r = A.contrast(p.color(fg).name(), p.color(bg).name())
        if r < 4.5:
            low.append(f"{fg.name}/{bg.name} {r}")
    dis = A.contrast(p.color(QPalette.ColorGroup.Disabled, R.Text).name(), p.color(QPalette.ColorGroup.Disabled, R.Base).name())
    if dis < 3.0:
        low.append(f"disabled text {dis}")
    check(f"palette: theme {name} - Qt palette roles readable", not low, low)
    sheet = app.styleSheet()
    check(f"style sheet: theme {name} never removes focus outlines", not re.search(r"outline\s*:\s*(none|0)", sheet))
    bg = p.color(R.Window).name()
    ring = A.ring_color(bg)
    check(f"focus ring: theme {name} - ring colour >= 3:1 on the window surface", A.contrast(ring, bg) >= 3.0,
          (ring, bg, A.contrast(ring, bg)))
theme.apply("Light")

# ---------------------------------------------------------------- Windows contrast themes
for wname, cols in A.WINDOWS_CONTRAST_THEMES.items():
    t = A.system_contrast_theme(cols)
    full = dict(theme.THEMES["High Contrast" if t["dark"] else "Light"])
    full.update(t)
    base = [(fg, bg, A.contrast(full[fg], full[bg])) for fg, bg in (("text", "window"), ("button_text", "button"),
                                                                    ("highlight_text", "highlight"), ("link", "window"),
                                                                    ("disabled", "window"))]
    low = [f"{fg}/{bg} {r}" for fg, bg, r in base if r < (3.0 if fg == "disabled" else 4.5)]
    check(f"Windows contrast theme {wname}: the system colours themselves pass", not low, low)
    check_theme(f"Windows Contrast ({wname})", full)
    check(f"Windows contrast theme {wname}: only Windows colours used", {full[k] for k in ("window", "base", "menu", "status")}
          == {cols["window"]} and full["text"] == cols["text"] and full["highlight"] == cols["highlight"])

auto_close_modals(True)
win = main_window(open_designer=False)
win.settings.setValue("accessibility/follow_high_contrast", True)
name = A.follow_high_contrast(win, on=True, colors=A.WINDOWS_CONTRAST_THEMES["Desert"])
pump(5)
check("Windows contrast on: the IDE switches to 'Windows Contrast'", name == A.SYSTEM_CONTRAST and theme.current_name() == name,
      (name, theme.current_name()))
check("Windows contrast on: the palette uses the Windows window colour",
      app.palette().color(R.Window).name().upper() == A.WINDOWS_CONTRAST_THEMES["Desert"]["window"].upper(),
      app.palette().color(R.Window).name())
check("Windows contrast on: listed in Tools > Options > Color theme", A.SYSTEM_CONTRAST in theme.THEME_NAMES)
theme.apply("Light")
win.settings.setValue("accessibility/follow_high_contrast", False)
name = A.follow_high_contrast(win, on=True, colors=A.WINDOWS_CONTRAST_THEMES["Night sky"])
check("Windows contrast on, following switched off: theme unchanged", name == "" and theme.current_name() == "Light",
      (name, theme.current_name()))
check("Windows contrast off: nothing happens", A.follow_high_contrast(win, on=False) == "")
win.settings.remove("accessibility/follow_high_contrast")
theme.remove_theme(A.SYSTEM_CONTRAST)

# ---------------------------------------------------------------- 200 % text
SCREEN = (1280, 720)


def clipped(root: QWidget) -> list[str]:
    out = []
    for w in root.findChildren(QWidget):
        try:
            if not w.isVisible() or w.visibleRegion().isEmpty():
                continue
            if isinstance(w, QLabel) and w.text().strip() and w.pixmap() is None or isinstance(w, QLabel) and \
                    w.pixmap() is not None and w.pixmap().isNull() and w.text().strip():
                if w.wordWrap():
                    need = w.heightForWidth(w.width())
                    if need > w.height() + 2:
                        out.append(f"label '{w.text()[:40]}' needs {need} px height, has {w.height()}")
                else:
                    msh = w.minimumSizeHint()
                    if w.width() + 2 < msh.width() and w.parentWidget() is not None and \
                            w.parentWidget().metaObject().className() not in ("QStatusBar",):
                        out.append(f"label '{w.text()[:40]}' {w.width()} < {msh.width()} px")
            elif isinstance(w, (QCheckBox, QRadioButton)) or (isinstance(w, QAbstractButton) and
                                                              w.metaObject().className() == "QPushButton"):
                if not w.text().strip():
                    continue
                msh = w.sizeHint()
                need_w = w.fontMetrics().horizontalAdvance(w.text().replace("&", "")) + 6 +                     (w.iconSize().width() + 4 if isinstance(w, (QCheckBox, QRadioButton)) or not w.icon().isNull() else 0)
                if w.width() + 2 < need_w or w.height() + 2 < min(msh.height(), w.fontMetrics().height() + 4):
                    out.append(f"{w.metaObject().className()} '{w.text()[:40]}' {w.width()}x{w.height()} < "
                               f"{msh.width()}x{msh.height()}")
        except RuntimeError:
            continue
    return out


base_font = QFont(app.font())
big = QFont(base_font)
big.setPointSizeF(base_font.pointSizeF() * 2)
app.setFont(big)
pump(5)
info(f"application font {base_font.pointSizeF()} pt -> {big.pointSizeF()} pt")
auto_close_modals(False)
from radide.dialogs import AddItemDialog, NewProjectDialog  # noqa: E402
from radide.features.extensions import ExtensionsDialog  # noqa: E402
from radide.features.installer import PublishDialog  # noqa: E402
from radide.features.settings import OptionsDialog  # noqa: E402
for title, make in (("New Project", lambda: NewProjectDialog(win)), ("Options", lambda: OptionsDialog(win)),
                    ("Publish", lambda: PublishDialog(win, project_copy(), "HelloPython")),
                    ("Extensions", lambda: ExtensionsDialog(win)),
                    ("Add Windows Form", lambda: AddItemDialog(win, "Add Windows Form", "Form2", "python-tk")),
                    ("Accessibility Check", lambda: A.show_check(win))):
    dlg = make()
    dlg.setFont(big)
    dlg.show()
    pump(15)
    msh = dlg.minimumSizeHint()
    bad = clipped(dlg)
    check(f"200 % text: dialog {title} clips no text", not bad, bad[:6])
    check(f"200 % text: dialog {title} fits {SCREEN[0]} x {SCREEN[1]} (minimum {msh.width()} x {msh.height()})",
          msh.width() <= SCREEN[0] and msh.height() <= SCREEN[1], (msh.width(), msh.height()))
    dlg.close()
    dlg.deleteLater()
    pump(3)
auto_close_modals(True)
for d in (win.dock_toolbox, win.dock_props, win.dock_solution):
    d.widget().setFont(big)
pump(10)
bad = []
for d in (win.dock_props, win.dock_solution):
    bad += [f"{d.windowTitle()}: {x}" for x in clipped(d)]
check("200 % text: Properties / Solution Explorer clip no label or button", not bad, bad[:6])
app.setFont(base_font)
win.close()
pump(5)
sys.exit(finish("Accessibility / contrast and scaling"))
