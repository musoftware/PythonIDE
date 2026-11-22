"""Visual Studio "Auto Hide" (minimize) of the tool windows - radide/features/dock_autohide.py.

Offscreen; QSettings "RADIDE-TEST-AUTOHIDE" (its own org: other GUI tests run at the same time) is cleared before and after; only widget.grab() pictures.
"""
import os
import sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")     # QtWebEngine views crash offscreen without it
os.environ["RADIDE_NO_BROWSER"] = "1"
os.environ["QT_FORCE_STDERR_LOGGING"] = "1"
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --disable-gpu-compositing")
ORG = "RADIDE-TEST-AUTOHIDE"        # radide.app.ide_settings() honours any "RADIDE-TEST*" organization
import re  # noqa: E402
import tempfile  # noqa: E402
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, ROOT)
__import__("PyQt6.QtWebEngineWidgets")       # must be imported before QApplication
from PyQt6.QtCore import QCoreApplication, QSettings, Qt, QTimer  # noqa: E402
from PyQt6.QtGui import QAction  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import QAbstractButton, QApplication, QDockWidget  # noqa: E402
QCoreApplication.setOrganizationName(ORG)
QCoreApplication.setApplicationName(ORG)
app = QApplication(sys.argv[:1])
QSettings().clear()
QSettings().sync()
from radide.app import MainWindow, _show_tool_window  # noqa: E402
from radide import i18n, theme  # noqa: E402
from radide.features import dock_autohide as AH  # noqa: E402
from radide.features.ui_language import apply_language  # noqa: E402

AH.ANIM_MS = 0
AR = re.compile(r"[\u0600-\u06FF]")
OUT = os.environ.get("AUTOHIDE_OUT") or tempfile.mkdtemp(prefix="radide_autohide_")
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (("  - " + str(detail)) if detail and not ok else ""), flush=True)


def pump(n=15):
    for _ in range(n):
        app.processEvents()
        QTest.qWait(5)


def close_boxes():
    m = QApplication.activeModalWidget()
    if m is not None:
        m.close()


killer = QTimer()
killer.timeout.connect(close_boxes)
killer.start(300)


def native(d, name):
    return d.findChild(QAbstractButton, name)


def docked_visible(win):
    return [d for d in win.findChildren(QDockWidget, options=Qt.FindChildOption.FindDirectChildrenOnly)
            if not d.isHidden() and not d.isFloating() and d.titleBarWidget() is None
            and win.dockWidgetArea(d) in AH.EDGE_OF]


try:
    win = MainWindow()
    win.resize(1280, 820)
    win.show()
    pump(40)
    mgr = win.autohide
    check("manager installed", isinstance(mgr, AH.AutoHide))
    wb = getattr(win, "workbench", None)
    check("Visual Studio layout", wb is None or wb.mode == "vs", getattr(wb, "mode", None))

    # ------------------------------------------------------------ title bar button
    tb = win.dock_toolbox
    b = mgr._buttons.get(tb)
    fl = native(tb, "qt_dockwidget_floatbutton")
    cl = native(tb, "qt_dockwidget_closebutton")
    check("pin button on the Toolbox title", b is not None and b.isVisible())
    check("pin left of Float / Close", b is not None and fl is not None and b.geometry().right() < fl.x()
          and b.geometry().right() < cl.x(), (b.geometry() if b else None, fl.geometry() if fl else None))
    check("pin inside the title bar row", b is not None and abs(b.y() - fl.y()) <= 1 and b.height() == fl.height())
    check("pin tooltip Auto Hide", b is not None and b.toolTip() == "Auto Hide")
    vis = docked_visible(win)
    # (windows behind another tab are not visible themselves: their pin only has to be shown in them)
    missing = [d.windowTitle() for d in vis if not (mgr._buttons.get(d) and not mgr._buttons[d].isHidden())]
    check("every docked tool window has the pin", vis and not missing, missing)
    check("native Float/Close kept", fl is not None and fl.isVisible() and cl is not None and cl.isVisible())
    tb.grab().save(os.path.join(OUT, "toolbox_title.png"))

    # ------------------------------------------------------------ auto hide one window
    central_before = win.centralWidget().geometry()
    toolbox_widget = win.toolbox
    left_grp = set(win.tabifiedDockWidgets(tb)) | {tb}
    left_grp = {d for d in left_grp if not d.isHidden()}
    b.click()
    pump()
    check("Toolbox hidden", tb.isHidden() and mgr.is_auto_hidden(tb))
    left = mgr.strips["left"]
    tabs = [t for t in left.tabs if isinstance(t, AH.StripTab)]
    check("left strip: a tab per window of the Toolbox group", left.isVisible() and len(tabs) == len(left_grp)
          and {t.dock for t in tabs} == left_grp, [t.dock.windowTitle() for t in tabs])
    tabs = [mgr.tab_for(tb)]
    check("left strip is vertical, tab taller than wide",
          left.orientation() == Qt.Orientation.Vertical and tabs and tabs[0].height() > tabs[0].width(),
          tabs[0].size() if tabs else None)
    check("Toolbox content moved to the slide panel", mgr.panel.isAncestorOf(toolbox_widget) and tb.widget() is None)
    left.grab().save(os.path.join(OUT, "left_strip.png"))

    # ------------------------------------------------------------ tab group
    grp_before = set(win.tabifiedDockWidgets(win.dock_output)) | {win.dock_output}
    mgr.auto_hide(win.dock_output)
    pump()
    group = mgr.group_of(win.dock_output)
    check("tabified group hidden together", set(group) == grp_before and all(d.isHidden() for d in group),
          [d.windowTitle() for d in group])
    bottom = mgr.strips["bottom"]
    btabs = [t for t in bottom.tabs if isinstance(t, AH.StripTab)]
    check("bottom strip: one tab per window", bottom.isVisible() and len(btabs) == len(grp_before), len(btabs))
    check("bottom strip horizontal", bottom.orientation() == Qt.Orientation.Horizontal)
    check("group order = tab order (Output first)", group and group[0] is win.dock_output,
          [d.windowTitle() for d in group])

    # ------------------------------------------------------------ slide out
    central_mid = win.centralWidget().geometry()
    mgr.slide_out(win.dock_output, focus=True)
    pump()
    p = mgr.panel
    pg = p.geometry()
    check("panel visible over the editor", p.isVisible() and p.parent() is win and mgr.shown_dock() is win.dock_output)
    check("panel sits right above the bottom strip", abs(pg.bottom() + 1 - bottom.geometry().top()) <= 1,
          (pg, bottom.geometry()))
    check("panel overlaps the central area", pg.intersects(win.centralWidget().geometry()))
    check("layout does not reflow while slid out", win.centralWidget().geometry() == central_mid)
    check("Output content shown in the panel", win.output.isVisible() and p.isAncestorOf(win.output))
    check("focus inside the panel", p.isAncestorOf(QApplication.focusWidget() or p) or QApplication.focusWidget() is p,
          type(QApplication.focusWidget()).__name__)
    p.grab().save(os.path.join(OUT, "panel_output.png"))
    win.grab().save(os.path.join(OUT, "window_slid_out.png"))
    QTest.keyClick(QApplication.focusWidget() or p, Qt.Key.Key_Escape)
    pump()
    check("Escape hides the slid-out window", not p.isVisible() and mgr.shown_dock() is None)
    check("still auto-hidden after Escape", mgr.is_auto_hidden(win.dock_output) and win.dock_output.isHidden())

    # click a tab, then focus elsewhere
    tabs = [mgr.tab_for(tb)]          # the strips are rebuilt on every change
    QTest.mouseClick(tabs[0], Qt.MouseButton.LeftButton)
    pump()
    check("click on the tab slides the window out", p.isVisible() and mgr.shown_dock() is tb)
    check("slid-out Toolbox on the left edge", abs(p.geometry().left() - (left.geometry().right() + 1)) <= 1,
          (p.geometry(), left.geometry()))
    win.solution.setFocus()
    pump()
    check("focus leaving hides it", not p.isVisible())
    QTest.mouseClick(tabs[0], Qt.MouseButton.LeftButton)
    pump()
    QTest.mouseClick(win.solution.viewport(), Qt.MouseButton.LeftButton)
    pump()
    check("click outside hides it", not p.isVisible())

    # hover
    btabs = [t for t in bottom.tabs if isinstance(t, AH.StripTab)]
    AH.HOVER_MS = 10
    mgr._hover_dock = btabs[1].dock
    mgr._hover_timer.setInterval(10)
    btabs[1].underMouse = lambda: True          # offscreen: no real pointer
    mgr._hover_start(btabs[1].dock)
    QTest.qWait(60)
    pump()
    check("hover slides out without focusing", p.isVisible() and mgr.shown_dock() is btabs[1].dock and mgr._hover)
    mgr.hide_panel()
    pump()

    # View menu entry / external show
    _show_tool_window(tb)
    pump()
    check("View > Toolbox slides it out", p.isVisible() and mgr.shown_dock() is tb and tb.isHidden())
    mgr.hide_panel()
    win.dock_locals.show()                       # what a feature does (e.g. the debugger)
    pump()
    check("dock.show() of an auto-hidden window slides it out",
          win.dock_locals.isHidden() and mgr.shown_dock() is win.dock_locals and p.isVisible(),
          (win.dock_locals.isHidden(), mgr.shown_dock()))
    mgr.hide_panel()
    pump()

    # ------------------------------------------------------------ dock back (pin)
    mgr.slide_out(win.dock_locals)
    pump()
    p.header.pin.click()
    pump(25)
    check("pin docks the group back", all(not d.isHidden() for d in grp_before) and not bottom.isVisible())
    check("back in the bottom area", win.dockWidgetArea(win.dock_output) == Qt.DockWidgetArea.BottomDockWidgetArea)
    check("back in its tab group", set(win.tabifiedDockWidgets(win.dock_output)) | {win.dock_output} == grp_before)
    check("content back in the docks", win.dock_output.widget() is win.output and win.dock_locals.widget() is win.locals)
    check("the pinned window is in front", win.dock_locals.visibleRegion().isEmpty() is False)
    check("panel hidden after docking", not p.isVisible())
    check("pins shown again", mgr._buttons[win.dock_output].isVisible() or mgr._buttons[win.dock_locals].isVisible())
    mgr.restore(tb)
    pump(25)
    check("Toolbox docked back on the left", not tb.isHidden() and tb.widget() is toolbox_widget
          and win.dockWidgetArea(tb) == Qt.DockWidgetArea.LeftDockWidgetArea)
    check("no strips left", not any(s.isVisible() for s in mgr.strips.values()))
    check("nothing saved when nothing is hidden", not QSettings(ORG, ORG).contains(AH.KEY))

    # ------------------------------------------------------------ close from the panel
    mgr.auto_hide(win.dock_props)
    pump()
    sol_hidden = win.dock_solution.isHidden()
    mgr.slide_out(win.dock_props)
    pump()
    p.header.close_btn.click()
    pump()
    check("Close in the panel closes the window", win.dock_props.isHidden() and not mgr.is_auto_hidden(win.dock_props)
          and win.dock_props.widget() is win.properties)
    check("Solution Explorer untouched (split, not tabbed)", win.dock_solution.isHidden() == sol_hidden)
    _show_tool_window(win.dock_props)
    pump()
    check("View shows the closed window docked", not win.dock_props.isHidden())

    # ------------------------------------------------------------ late docks of features
    from PyQt6.QtWidgets import QTextEdit
    late = QDockWidget("Late Tool", win)
    late.setObjectName("Late Tool")
    late.setWidget(QTextEdit())
    win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, late)
    pump()
    check("late dock gets the pin", mgr._buttons.get(late) is not None and not mgr._buttons[late].isHidden())
    check("late dock auto-hides to the right", mgr.auto_hide(late) and mgr.edge_of(late) == "right"
          and mgr.strips["right"].isVisible())
    pump()
    mgr.slide_out(late)
    pump()
    check("right panel opens to the left of its strip",
          abs(p.geometry().right() + 1 - mgr.strips["right"].geometry().left()) <= 1)
    mgr.restore(late)
    pump()

    # ------------------------------------------------------------ Window menu
    wm = next(a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == "Window")
    a_all = win.findChild(QAction, "autohide_all")
    a_tog = win.findChild(QAction, "autohide_toggle")
    check("Window > Auto Hide / Auto Hide All", a_all is not None and a_tog is not None
          and a_all in wm.actions() and a_tog in wm.actions())
    win.solution.setFocus()
    pump()
    wm.aboutToShow.emit()
    check("Auto Hide enabled for the active tool window", a_tog.isEnabled() and mgr.active_dock() is win.dock_solution)
    a_tog.trigger()
    pump()
    check("Window > Auto Hide hides the active window", mgr.is_auto_hidden(win.dock_solution))
    mgr.restore(win.dock_solution)
    pump()
    before = docked_visible(win)
    a_all.trigger()
    pump()
    check("Auto Hide All hides every docked tool window", not docked_visible(win) and len(mgr.auto_hidden()) >= len(before),
          [d.windowTitle() for d in docked_visible(win)])
    win.grab().save(os.path.join(OUT, "window_auto_hide_all.png"))
    hidden_names = sorted(d.objectName() for d in mgr.auto_hidden())
    check("Auto Hide All includes the late feature dock", "Late Tool" in hidden_names)
    hidden_names.remove("Late Tool")         # not created again after the restart (stays pending)
    saved = QSettings(ORG, ORG).value(AH.KEY)
    check("list saved in QSettings", saved and all(n in saved for n in hidden_names))

    # ------------------------------------------------------------ workbench layouts
    if wb is not None:
        wb.set_mode("vscode")
        pump(30)
        check("VS Code layout: windows put back", not mgr.auto_hidden() and win.dock_toolbox.widget() is toolbox_widget
              and not any(s.isVisible() for s in mgr.strips.values()))
        wb.set_mode("vs")
        pump(30)
        check("VS layout again: auto-hidden again",
              sorted(d.objectName() for d in mgr.auto_hidden() if d is not late) == hidden_names,
              sorted(d.objectName() for d in mgr.auto_hidden()))
        check("VS layout again: docks still hidden", all(d.isHidden() for d in mgr.auto_hidden()))

    # ------------------------------------------------------------ theme
    theme.apply("Dark")
    pump()
    dark = theme.current()["window"]
    check("strips / panel follow the theme", dark in mgr.panel.styleSheet() and dark in mgr.strips["left"].styleSheet())
    mgr.strips["bottom"].grab().save(os.path.join(OUT, "bottom_strip_dark.png"))
    theme.apply("Light")
    pump()

    # ------------------------------------------------------------ restart
    win.close()
    pump(20)
    win2 = MainWindow()
    win2.resize(1280, 820)
    win2.show()
    pump(40)
    m2 = win2.autohide
    names2 = sorted(d.objectName() for d in m2.auto_hidden())
    check("auto-hidden windows survive a restart", names2 == hidden_names, (names2, hidden_names))
    check("restored windows are hidden, strips shown",
          all(d.isHidden() for d in m2.auto_hidden()) and m2.strips["bottom"].isVisible() and m2.strips["left"].isVisible())
    check("restart keeps the tab group", set(m2.group_of(win2.dock_output)) >=
          {win2.dock_output, win2.dock_locals, win2.dock_stack, win2.dock_immediate})
    m2.slide_out(win2.dock_toolbox)
    pump()
    check("slide out after restart", m2.panel.isVisible() and win2.toolbox.isVisible())

    # ------------------------------------------------------------ Arabic / RTL
    m2.restore(win2.dock_toolbox, focus=False)
    pump(10)
    apply_language(win2, "ar", notify=False)
    pump(30)
    toolbox_x_rtl = win2.dock_toolbox.geometry().center().x()
    m2.auto_hide(win2.dock_toolbox)
    pump(10)
    m2.hide_panel()
    pump()
    a2 = win2.findChild(QAction, "autohide_all")
    check("Arabic: Auto Hide All translated", AR.search(i18n.shown(a2)) and a2.text() == "Auto Hide &All",
          i18n.shown(a2))
    tab = m2.tab_for(win2.dock_toolbox)
    check("Arabic: strip tab text translated", tab is not None and AR.search(tab.label()), tab.label() if tab else None)
    m2.slide_out(win2.dock_toolbox)
    pump()
    lst = m2.strips["left"]
    pg2, sg2 = m2.panel.geometry(), lst.geometry()
    # (QMainWindow does not mirror its dock areas in RTL: the strip is where the Toolbox was docked)
    check("RTL: strip on the edge the Toolbox was docked to", (sg2.center().x() < win2.width() // 2) ==
          (toolbox_x_rtl < win2.width() // 2), (sg2, toolbox_x_rtl))
    check("RTL: panel opens toward the editor", abs(pg2.left() - (sg2.right() + 1)) <= 1 if sg2.center().x() <
          win2.width() // 2 else abs(pg2.right() + 1 - sg2.left()) <= 1, (pg2, sg2))
    m2.panel.grab().save(os.path.join(OUT, "panel_rtl.png"))
    m2.restore_all()
    pump(25)
    d = win2.dock_solution
    b2, f2 = m2._buttons.get(d), native(d, "qt_dockwidget_floatbutton")
    check("RTL: pin right of Float / Close", b2 is not None and b2.isVisible() and f2 is not None and b2.x() > f2.geometry().right(),
          (b2.geometry() if b2 else None, f2.geometry() if f2 else None))
    d.grab().save(os.path.join(OUT, "solution_title_rtl.png"))
    apply_language(win2, "en", notify=False)
    pump(20)
    check("English again", not AR.search(i18n.shown(a2)), i18n.shown(a2))
    left_saved = QSettings(ORG, ORG).value(AH.KEY) or ""
    check("everything docked, only the missing late dock stays saved", not m2.auto_hidden()
          and "Late Tool" in left_saved and "Toolbox" not in left_saved, left_saved)
    win2.close()
    pump(10)
finally:
    QSettings().clear()
    QSettings().sync()

failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} passed   (pictures: {OUT})")
sys.exit(1 if failed else 0)
